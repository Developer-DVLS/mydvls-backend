from datetime import datetime
import hashlib
import hmac
from fastapi import APIRouter, Depends, Request, HTTPException

from app.core.config import settings
from app.core.database import get_db
from app.models.orders import OrderStatus
from app.models.refunds import RefundStatus
from app.services.orderservice import OrderService
from app.services.refundservice import RefundService
from app.services.smsservice import send_message

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

AUTHORIZE_SIGNATURE_KEY = settings.AUTHORIZE_SIGNATURE_KEY

def verify_signature(raw_body: bytes, signature_header: str) -> bool:
    if not signature_header or not signature_header.startswith("sha512="):
        return False
    expected_sig = signature_header.split("sha512=", 1)[1]
    computed = hmac.new(
        AUTHORIZE_SIGNATURE_KEY.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(computed.lower(), expected_sig.lower())


@router.post("/webhooks/authorize-net")
async def handle_authorize_net_webhook(request: Request, db=Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("X-ANET-Signature", "")

    if not verify_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event_type = payload.get("eventType")
    payload_data = payload.get("payload", {})
    trans_id = payload_data.get("id")  # the transId of the held transaction

    if not trans_id:
        return {"received": True}  # nothing actionable

    refund_service = RefundService(db)
    refund = await refund_service.get_refund_by_gateway_transaction_id(trans_id)
    if refund:
        sms_message = None
        # Handle refund webhook
        if event_type == "net.authorize.payment.fraud.approved":
            refund.status = RefundStatus.SUCCEEDED.value
            refund.completed_at = datetime.utcnow()
            refund.gateway_error = None
            
            sms_message = (
                f"Your refund for order #{refund.order.order_number} "
                "has been successfully processed."
            )
        elif event_type == "net.authorize.payment.fraud.declined":
            refund.status = RefundStatus.FAILED.value
            refund.gateway_error = "Declined after fraud review"
            
            sms_message = (
                f"Your refund for order #{refund.order.order_number} "
                "was declined."
            )
        else:
            return {"received": True}

        await db.commit()
        
        if sms_message:
            try:
                await send_message(sms_message, refund.order.receiver_phone)
            except Exception as exc:
                # Log SMS failure, but don't fail the webhook
                logger.exception("Failed to send refund SMS: %s", exc)
                
        return {"received": True}
    
    order_service = OrderService(db)
    order = await order_service.get_order_by_trans_id(trans_id)
    if order:
        sms_message = None
        
        if event_type == "net.authorize.payment.fraud.approved":
            order.payment_status = "paid" 
            
            sms_message = (
                f"Payment for order #{order.order_number} "
                "has been approved."
            )

        elif event_type == "net.authorize.payment.fraud.declined":
            order.status = OrderStatus.CANCELLED.value
            order.payment_status = "failed"
            
            #update inventory
            for ordered_item in order.items:
                product_variant = ordered_item.product_variant
                #update
                product_variant.stock_quantity += ordered_item.quantity

            sms_message = (
                f"Payment for order #{order.order_number} "
                "was declined. Your order has been cancelled."
            )
            
        await db.commit()
        if sms_message:
            try:
                await send_message(sms_message, order.receiver_phone)
            except Exception as exc:
                logger.exception("Failed to send payment SMS: %s", exc)

    return {"received": True}
    
    