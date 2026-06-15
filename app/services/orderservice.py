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
from app.models.offers import Offer
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
        cart = cart_service.normalize_cart(cart)
            
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
            
            # # normalize
            # cart = cart_service.normalize_cart(cart)
                        
        if cart.coupon_id:
            coupon_result = await self.db.execute(
                select(Offer)
                .where(Offer.id == cart.coupon_id)
            )
            coupon = coupon_result.scalars().first()
            enriched_cart = await cart_service.enrich_cart(
                    request=request,
                    response=response,
                    db=self.db,
                    user_id=user.id,
                    cart=cart,
                    coupon_code=coupon.code,
                    remove_coupon=False
                )
        else:
            enriched_cart = await cart_service.enrich_cart(
                    request=request,
                    response=response,
                    db=self.db,
                    user_id=user.id,
                    cart=cart,
                    coupon_code=None,
                    remove_coupon=True
                )

        # if any bogo-offer exists: create a cart-product for free item
        if enriched_cart.bogo_offer_exists:
            for cart_product in enriched_cart.cart_products:
                if cart_product.bogo_free_item:
                    item = CartProduct(
                        cart_id=cart.id,
                        product_variant_id=cart_product.bogo_free_item.product_variant_id,
                        quantity=cart_product.bogo_free_item.quantity,
                        unit_price=0,
                        is_free_item=True,
                        trigger_cart_item_id=cart_product.id,
                        parent_offer_id=cart_product.offer.id
                    )
                    self.db.add(item)
            # await self.db.refresh(item)

        # Create order
        order = Order(
            user_id = user.id,
            cart_id = cart.id,
            order_number = str(uuid.uuid4()),
            subtotal = enriched_cart.subtotal,
            tax_amount = enriched_cart.tax_amount,
            discount_amount = enriched_cart.total_discount_amount,
            delivery_charge = 0, #TODO: need to calculate delivery charge
            total = enriched_cart.total_amount,
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