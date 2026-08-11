# Replace with your actual credentials 
from fastapi import Depends, HTTPException
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.payment import ChargeRequest
from app.core.config import settings
from app.models.orders import Order
from app.core.database import get_db


API_LOGIN_ID = settings.API_LOGIN_ID
TRANSACTION_KEY = settings.TRANSACTION_KEY
ENDPOINT_URL = settings.ENDPOINT_URL

class PaymentService:
    async def charge_card(
        self, 
        payment: ChargeRequest,
        db: AsyncSession = Depends(get_db),
    ) -> dict:
        # get order 
        order_result = await db.execute(
            select(Order).where(
                Order.order_number == payment["order_number"]
                )
        )
        order = order_result.scalars().first()
        if not order:
            raise HTTPException(
                    status_code=404, 
                    detail="Order not Found."
                    )
        
        shipping_name_parts = (order.shipping_full_name or "").strip().split(" ", 1)

        shipping_first_name = shipping_name_parts[0] if shipping_name_parts else ""
        shipping_last_name = (
            shipping_name_parts[1]
            if len(shipping_name_parts) > 1
            else ""
        )
        
        payload = {
            "createTransactionRequest": {
                "merchantAuthentication": {
                    "name": API_LOGIN_ID,
                    "transactionKey": TRANSACTION_KEY,
                },
                "transactionRequest": {
                    "transactionType": "authCaptureTransaction",
                    "amount":f"{payment['amount']:.2f}",
                    "payment": {
                        "opaqueData": {
                            "dataDescriptor": payment["opaqueDataDescriptor"],
                            "dataValue": payment["opaqueDataValue"],
                        }
                    },
                    "order": {
                        "invoiceNumber": str(payment["order_number"])[:20]
                    },
                    "customer": {
                        "email": payment["receiver_email"]
                    },
                    # Billing address
                    "billTo": {
                        "firstName": (order.receiver_first_name or "")[:50],
                        "lastName": (order.receiver_last_name or "")[:50],
                        "address": (order.address_line1 or "")[:60],
                        "city": (order.city or "")[:40],
                        "state": (order.state or "")[:40],
                        "zip": (order.postal_code or "")[:20],
                        "country": (order.country or "")[:60],
                    },
                    
                    # Shipping address
                    "shipTo": {
                        "firstName": shipping_first_name,
                        "lastName": shipping_last_name,
                        "company": (order.shipping_company or "")[:50],
                        "address": order.shipping_address_line_1[:60],
                        "city": (order.shipping_city or "")[:40],
                        "state": (order.shipping_state or "")[:40],
                        "zip": (order.shipping_postal_code or "")[:20],
                        "country": (order.shipping_country or "")[:60],
                    },
                },
            }
        }

        async with httpx.AsyncClient() as client:       
            response = await client.post(ENDPOINT_URL, json=payload)
            response.raise_for_status()                

        data = response.json()

        # Top-level API error (auth failure, malformed request, etc.)
        if data.get("messages", {}).get("resultCode") != "Ok":
            error_text = (
                data.get("messages", {})
                    .get("message", [{}])[0]
                    .get("text", "Request failed")
            )
            raise HTTPException(status_code=400, detail=error_text)

        tx = data.get("transactionResponse", {})

        if tx.get("responseCode") != "1":
            if tx.get("responseCode") == "4":
                raise HTTPException(
                    status_code=402, 
                    detail="Transaction is held for manual fraud review."
                    )
            
            error_text = (
                tx.get("errors", [{}])[0].get("errorText")
                or tx.get("messages", [{}])[0].get("description")
                or "Transaction declined"
            )
            raise HTTPException(status_code=402, detail=error_text)

        return {
            
            "status": "success",
            "transactionId": tx["transId"],
            "authCode": tx["authCode"],
        }