from typing import Optional
import uuid
from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.cart import get_cart
from app.api.v1.schemas.carts import CartResponse
from app.api.v1.schemas.orders import OrderCreate
from app.models.carts import CartProduct
from app.models.orders import Order, OrderItem
from app.models.user import User, UserRole
from app.services.cartservice import CartService
from app.services.userservice import UserService

class OrderService:

    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_order(
        self,
        request: Request,
        response: Response,
        data: OrderCreate,
        user: Optional[User] = None,
    ):
        """
        Create an order for either:
        - Logged-in user
        - Guest user
        """

        user_service = UserService(self.db)
        cart_service = CartService()
        cart = None
        
        # Get cart
        cart = await cart_service.get_cart(
            request,
            self.db, 
            user.id if user else None
            )
        # normalize
        if not isinstance(cart, CartResponse):
            cart = CartResponse.model_validate(cart)
        
        if not cart.cart_products:
            raise ValueError("Cart is Empty")
        
        # validate user auth
        if not user:
            # create guest user
            user = await user_service.create_guest_user(
                data.receiver_first_name,
                data.receiver_last_name,
                data.receiver_email,
                data.receiver_phone
            )
            
            # assign cart to guest-user
            # sync session cart
            cart = await cart_service.cart_sync_on_login(request, response, self.db, user.id) 
            if not cart:
                raise ValueError("Cart is Empty")

        # Create order
        order = Order(
            user_id = user.id,
            cart_id = cart.id,
            order_number = str(uuid.uuid4()),
            subtotal = data.subtotal,
            tax_amount = data.tax_amount,
            discount_amount = data.discount_amount,
            delivery_charge = data.delivery_charge,
            total = data.total,
            currency = data.currency or "USD",
            notes = data.notes,
            receiver_first_name = data.receiver_first_name, 
            receiver_last_name = data.receiver_last_name,
            receiver_email = data.receiver_email,
            receiver_phone = data.receiver_phone, 
            address_line1 = data.address_line1,
            address_line2 = data.address_line2 or None,
            city = data.city,
            state = data.state,
            postal_code = data.postal_code,
            country = data.country,
            latitude = data.longitude,
            longitude = data.longitude,
            delivery_distance = None,
            payment_status="pending"
        )

        self.db.add(order)
        await self.db.flush()  # Generates order.id

        # Get cart items
        items_result = await self.db.execute(
            select(CartProduct)
            .where(CartProduct.cart_id == cart.id)
        )
        cart_items = items_result.scalars().all()
        print("cart_items!!", cart_items)
        # Create order items
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_variant_id=item.product_variant_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.unit_price * item.quantity,
            )
            self.db.add(order_item)

        await self.db.commit()
        await self.db.refresh(order)
        
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.cart),
                selectinload(Order.items)
            )
            .where(Order.id == order.id)
        )
        order = result.scalars().first()

        return order