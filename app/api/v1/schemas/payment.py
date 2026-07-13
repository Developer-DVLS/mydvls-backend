from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class ChargeRequest(BaseModel):
    opaqueDataDescriptor: str   # "COMMON.ACCEPT.INAPP.PAYMENT"
    opaqueDataValue: str        # nonce from Accept.js
    amount: Decimal
    order_number: str
    receiver_email: str