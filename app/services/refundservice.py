from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.models.refunds import Refund, RefundStatus
from app.core.config import settings

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
            select(Refund).where(Refund.refund_transaction_id == trans_id)
        )
        return result.scalar_one_or_none()