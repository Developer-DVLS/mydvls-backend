from typing import Optional
import uuid
from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, raiseload

from app.api.v1.endpoints.cart import get_cart
from app.api.v1.schemas.carts import CartResponse
from app.api.v1.schemas.orders import OrderBillingAddressBase, OrderCreate, OrderShippingAddressBase
from app.models.address import Address
from app.models.carts import CartProduct
from app.models.offers import Offer, OfferType
from app.models.orders import AppliedCombo, Order, OrderItem
from app.models.products import Product, ProductVariant
from app.models.user import User, UserRole
from app.services.cartservice import CartService
from app.services.userservice import UserService

class OrderService:

    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_order_address(self, user_id, address_id):
        result = await self.db.execute(
            select(Address).where(
                Address.id == address_id,
                Address.user_id == user_id,
            )
        )

        address = result.scalar_one_or_none()

        if not address:
            raise HTTPException(
                status_code=404,
                detail="Address not found",
            )

        return address
        
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
        is_guest = False if user else True
        
        # Get cart
        cart = await cart_service.get_cart(
            request,
            self.db, 
            user.id if user else None
            )
        
        # normalize
        cart = cart_service.normalize_cart(cart)
            
        if not cart.cart_products:
            raise HTTPException(status_code=400, detail="Cart is empty")

        # inventory check
        for cart_product in cart.cart_products:
            try:
                await cart_service.check_stock(
                    self.db, 
                    cart_product.product_variant_id, 
                    cart_product.quantity
                    )
            except HTTPException as e:
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail["message"]
                )
        
        coupon_code = None
        coupon = None
        if user and cart.coupon_id:
            coupon_result = await self.db.execute(
                select(Offer).where(Offer.id == cart.coupon_id)
            )
            coupon = coupon_result.scalars().first()
            coupon_code = coupon.code if coupon else None

        enriched_cart = await cart_service.enrich_cart(
            request=request,
            response=response,
            db=self.db,
            user_id=user.id if user else None,
            cart=cart,
            coupon_code=coupon_code,
            remove_coupon=coupon_code is None,
        )
        
        # if any bogo-offer exists: create a cart-product for free item
        if user and enriched_cart.bogo_offer_exists:       
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
            
            
        # validate user auth
        if not user:
            # create guest user
            user = await user_service.create_guest_user(
                data.receiver_first_name,
                data.receiver_last_name,
                data.receiver_email,
                data.receiver_phone
            )
        
        if data.billing_address_id:
            order_billing_address = await self.get_order_address(
                user.id, 
                data.billing_address_id
                )
            data.billing_address = OrderBillingAddressBase(
                address_line1=order_billing_address.address_line1,
                address_line2=order_billing_address.address_line2,
                city=order_billing_address.city,
                state=order_billing_address.state,
                postal_code=order_billing_address.postal_code,
                country=order_billing_address.country,
                latitude=order_billing_address.latitude,
                longitude=order_billing_address.longitude,
            )
        
        if data.shipping_address_id:
            order_shipping_address = await self.get_order_address(
                user.id, 
                data.shipping_address_id
                )   
            data.shipping_address = OrderShippingAddressBase(
                address_line1=order_shipping_address.address_line1,
                address_line2=order_shipping_address.address_line2,
                city=order_shipping_address.city,
                state=order_shipping_address.state,
                postal_code=order_shipping_address.postal_code,
                country=order_shipping_address.country,
                latitude=order_shipping_address.latitude,
                longitude=order_shipping_address.longitude,
            )
        # Create order
        order = Order(
            user_id = user.id,
            cart_id = None if is_guest else cart.id ,
            coupon_id = cart.coupon_id or None,
            order_number = str(uuid.uuid4()),
            subtotal = enriched_cart.subtotal,
            tax_amount = enriched_cart.tax_amount,
            discount_amount = enriched_cart.total_discount_amount,
            delivery_charge = enriched_cart.shipping_charge,
            total = enriched_cart.total_amount,
            currency = data.currency or "USD",
            notes = data.notes,
            
            receiver_first_name = data.receiver_first_name, 
            receiver_last_name = data.receiver_last_name,
            receiver_email = data.receiver_email,
            receiver_phone = data.receiver_phone, 
            address_line1 = data.billing_address.address_line1,
            address_line2 = data.billing_address.address_line2 or None,
            city = data.billing_address.city,
            state = data.billing_address.state,
            postal_code = data.billing_address.postal_code,
            country = data.billing_address.country,
            latitude = data.billing_address.latitude,
            longitude = data.billing_address.longitude,
            
            shipping_full_name = data.shipping_full_name,
            shipping_company = data.shipping_company,
            shipping_phone = data.shipping_phone,
            shipping_address_line_1 = data.shipping_address.address_line1,
            shipping_address_line_2 = data.shipping_address.address_line2 or None,
            shipping_city = data.shipping_address.city,
            shipping_state =  data.shipping_address.state,
            shipping_postal_code = data.shipping_address.postal_code,
            shipping_country = data.shipping_address.country,
            shipping_latitude = data.shipping_address.latitude,
            shipping_longitude = data.shipping_address.longitude,
            
            delivery_distance = None,
            payment_status="pending"
        )

        self.db.add(order)
        await self.db.flush()  # Generates order.id
        

        if not is_guest:
            # Get cart items
            items_result = await self.db.execute( 
                                                select(CartProduct) 
                                                .where(CartProduct.cart_id == cart.id) ) 
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
        else:
            # redis_cart = await cart_service.get_redis_cart(request)
            redis_items = enriched_cart.cart_products

            if not redis_items:
                raise HTTPException(status_code=400, detail="Cart is empty")
            
            variant_ids = [item.product_variant_id for item in redis_items]

            # Single batched query instead of one query per item
            result = await self.db.execute(
                select(ProductVariant)
                .join(ProductVariant.product)
                .options(selectinload(ProductVariant.product).selectinload(Product.category))
                .where(
                    ProductVariant.id.in_(variant_ids),
                    ProductVariant.is_active == True,
                    ProductVariant.deleted_at.is_(None),
                    Product.is_active == True,
                    Product.deleted_at.is_(None),
                )
            )
            variants_by_id = {v.id: v for v in result.scalars().all()}

            for item in redis_items:
                variant = variants_by_id.get(item.product_variant_id)
                if not variant:
                    raise HTTPException(status_code=400, detail="Invalid product_variant_id.")

                self.db.add(OrderItem(
                    order_id=order.id,
                    product_variant_id=variant.id,
                    quantity=item.quantity,
                    unit_price=variant.price,
                    total_price=variant.price * item.quantity,
                ))
                print("exists!!!!", enriched_cart.bogo_offer_exists)
                ## add bogo free item 
                if (
                    enriched_cart.bogo_offer_exists
                    and item.offer
                    and item.offer.type == OfferType.BOGO
                    and item.bogo_free_item
                ):
                    self.db.add(OrderItem(
                        order_id=order.id,
                        product_variant_id=item.bogo_free_item.product_variant_id,
                        quantity=item.bogo_free_item.quantity,
                        unit_price=0,
                        total_price=0,
                    ))
        
        # Assign combo-offer to order if any applied
        if enriched_cart.combo_offers:
            for combo_offer in enriched_cart.combo_offers:
                applied_combo = AppliedCombo(
                    order_id = order.id,
                    combo_offer_id = combo_offer["id"],
                    quantity_used = combo_offer["applied_count"],
                    discount_amount = combo_offer["discount"]
                )
                self.db.add(applied_combo)
        
        await self.db.commit()
        await self.db.refresh(order)
        
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.cart),
                selectinload(Order.items)
                .selectinload(OrderItem.product_variant)
                .selectinload(ProductVariant.product)
            )
            .where(Order.id == order.id)
        )
        order = result.scalars().first()

        return order
    
    async def get_order_by_trans_id(self, trans_id):
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items)
                .selectinload(OrderItem.product_variant)
                )
            .where(Order.payment_intent_id == trans_id)
        )
        return result.scalar_one_or_none()