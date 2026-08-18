from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from sqlalchemy.orm import selectinload

from app.models.refunds import Refund, RefundStatus
from app.core.config import settings
from app.services.paymentservice import PaymentService
from app.services.smsservice import send_message

import logging

logger = logging.getLogger(__name__)

API_LOGIN_ID = settings.API_LOGIN_ID
TRANSACTION_KEY = settings.TRANSACTION_KEY
ENDPOINT_URL = settings.ENDPOINT_URL

class RefundService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def existing_pending_check(
        self,
        order_id,
        current_user
    ):
        existing_result = await self.db.execute(
            select(Refund)
            .where(
                Refund.order_id == order_id,
                Refund.user_id == current_user.id,
                Refund.status.in_([
                    RefundStatus.PENDING.value,
                    RefundStatus.PROCESSING.value,
                ]),
            )
        )

        existing_refund = existing_result.scalar_one_or_none()

        if existing_refund:
            raise HTTPException(
                status_code=400,
                detail="A refund request is already being processed for this order.",
            )
        
    async def get_previous_refunded_amount(
        self,
        order_id: int,
    ) -> Decimal:

        result = await self.db.execute(
            select(
                func.coalesce(
                    func.sum(Refund.amount),
                    0,
                )
            )
            .where(
                Refund.order_id == order_id,
                Refund.status == RefundStatus.SUCCEEDED.value,
            )
        )

        return Decimal(
            str(result.scalar() or 0)
        )
        
    async def get_transaction_details(
        self,
        transaction_id: str,
    ) -> dict:
        payload = {
            "getTransactionDetailsRequest": {
                "merchantAuthentication": {
                    "name": API_LOGIN_ID,
                    "transactionKey": TRANSACTION_KEY,
                },
                "transId": transaction_id,
            }
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(ENDPOINT_URL, json=payload)
            response.raise_for_status()

        data = response.json()

        if data.get("messages", {}).get("resultCode") != "Ok":
            error_text = (
                data.get("messages", {})
                    .get("message", [{}])[0]
                    .get("text", "Could not retrieve transaction details")
            )
            raise HTTPException(status_code=400, detail=error_text)

        return data.get("transaction", {})
    
    async def get_refund_card_info(
        self,
        transaction_id: str,
    ) -> dict:
        """
        Returns the masked card info + settlement status needed to decide
        between refundTransaction and voidTransaction, and to populate the
        refund payload.
        """
        transaction = await self.get_transaction_details(transaction_id)
        
        if transaction and transaction.get("transactionStatus") != "settledSuccessfully":
            raise HTTPException(status_code=400, detail="Refund cannot be processed yet. Payment for this order is still being processed.")

        credit_card = transaction.get("payment", {}).get("creditCard", {})
        card_number = credit_card.get("cardNumber")
        expiration_date = credit_card.get("expirationDate")

        if not card_number or not expiration_date:
            raise HTTPException(
                status_code=400,
                detail="Could not retrieve original card details for refund.",
            )

        return {
            "card_last4": card_number[-4:],
            "card_number_masked": card_number,   # e.g. "XXXX1111" — pass this straight into refundTransaction
            "expiration_date": expiration_date,  # e.g. "XXXX" — pass this straight into refundTransaction
            "transaction_status": transaction.get("transactionStatus"),  # e.g. "settledSuccessfully" | "capturedPendingSettlement"
            "settled": transaction.get("transactionStatus") == "settledSuccessfully",
        }
        
    async def get_refund_by_gateway_transaction_id(
        self,
        trans_id: str,
    ) -> Refund | None:
        result = await self.db.execute(
            select(Refund)
            .options(selectinload(Refund.order))
            .where(Refund.refund_transaction_id == trans_id)
        )
        return result.scalar_one_or_none()
    
    async def process_refund(
        self,
        refund,
        ):
        try:
            authorize_net = PaymentService()

            response = await authorize_net.refund(
                amount=refund.amount,
                original_transaction_id=(
                    refund.original_transaction_id
                ),
                card_last4=refund.card_last4,
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            # We genuinely don't know if Authorize.Net processed this.
            # Do NOT mark as FAILED — that invites a duplicate refund.
            refund.status = RefundStatus.PENDING_RECONCILIATION.value
            refund.gateway_error = f"No response from gateway: {exc}"
            await self.db.commit()
            raise HTTPException(
                status_code=502,
                detail="Refund status unknown, pending reconciliation.",
            )

        except Exception as exc:
            refund.status = RefundStatus.FAILED.value
            refund.gateway_error = str(exc)
            await self.db.commit()

            raise HTTPException(
                status_code=502,
                detail="Authorize.Net refund request failed.",
            )

        # ---------------------------------------------------------
        # Parse Authorize.Net response
        # ---------------------------------------------------------

        transaction_response = response.get("transactionResponse", {})
        response_code = transaction_response.get("responseCode")
        top_level_messages = response.get("messages", {})

        # ---------------------------------------------------------
        # Success / Failure
        # ---------------------------------------------------------

        if response_code == "1":
            refund.status = RefundStatus.SUCCEEDED.value
            refund.refund_transaction_id = (
                transaction_response.get("transId")
            )
            refund.gateway_response_code = (
                response_code
            )
            refund.completed_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(refund)
            
            #send sms 
            message = (f"Your refund for order #{refund.order.order_number} has been successfully processed. "
                        "Please allow some time for the amount to appear in your account.")
            await send_message(message, refund.order.receiver_phone)

            return refund
        elif response_code == "4":
            refund.status = RefundStatus.PENDING_REVIEW.value
            refund.gateway_response_code = response_code
            refund.gateway_error = str(
                transaction_response.get("errors")
                or transaction_response.get("messages")
                or "Held for review"
            )
            
            message = (
                f"Your refund for order #{refund.order.order_number} is currently under review. "
                "We will notify you once the refund is completed."
            )
            try:
                await send_message(message, refund.order.receiver_phone)
            except Exception as exc:
                    # Log SMS failure, but don't fail the webhook
                    logger.exception("Failed to send refund SMS: %s", exc)
            
        else:
            refund.status = RefundStatus.FAILED.value
            refund.gateway_response_code = response_code
            refund.gateway_error = str(
                transaction_response.get("errors")
                or transaction_response.get("messages")
                or top_level_messages.get("message")
                or "Unknown gateway error"
            )

        await self.db.commit()
        await self.db.refresh(refund)
        
        return refund