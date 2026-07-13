# Replace with your actual credentials 
from fastapi import HTTPException
import httpx

from app.api.v1.schemas.payment import ChargeRequest
from app.core.config import settings


API_LOGIN_ID = settings.API_LOGIN_ID
TRANSACTION_KEY = settings.TRANSACTION_KEY
ENDPOINT_URL = settings.ENDPOINT_URL

class PaymentService:
    async def charge_card(
        self, 
        payment: ChargeRequest
    ) -> dict:
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
                        "invoiceNumber": payment["order_number"]
                    },
                    "customer": {
                        "email": payment["receiver_email"]
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