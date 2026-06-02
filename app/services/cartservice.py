from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import json
import uuid
from fastapi import HTTPException, Request, Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.carts import CartBOGOFreeItem, CartBOGOMeta, CartGetItem, CartGetItemProduct, CartOfferResponse, CartResponse, ProductVariantResponse
from app.models.carts import Cart, CartProduct, CartStatus
from app.models.offers import ComboDiscountType, ComboOffer, DiscountType, Offer, OfferType
from app.models.products import Product, ProductCategory, ProductVariant
from app.services.offerservice import build_offer_indexes, get_all_active_offers, resolve_offer, valid_combo_offers
from app.utils.cache import delete_cache, get_cache, set_cache

class CartService:
    SESSION_COOKIE_KEY = "guest_cart"
    REDIS_PREFIX = "cart:guest:"
    GUEST_CART_EXPIRY = 60 * 60 * 24 * 7  #7days
    
    # GET CART (UNIFIED)
    async def get_cart(
        self, 
        request: Request,
        db: AsyncSession, 
        user_id=None
        ):
        if user_id:
            return await self.get_db_cart(db, user_id)

        return await self.get_redis_cart(request)
    
    # ADD ITEM
    async def add(
        self, 
        request: Request,
        response: Response,
        db: AsyncSession, 
        product_variant_id: int, 
        quantity: int = 1, 
        user_id=None
    ):
        if user_id:
            return  await self.add_to_db_cart(db, user_id, product_variant_id, quantity)

        return await self.add_to_redis_cart(request, response, product_variant_id, quantity, db)
    
    # UPDATE ITEM
    async def update(
        self, 
        request: Request,
        db: AsyncSession,  
        quantity: int, 
        cart_product_id: int = None, 
        user_id=None
    ):
        if user_id:
            return await self.update_db_cart_item(db, user_id, cart_product_id, quantity)

        return await self.update_redis_cart(request, cart_product_id, quantity)
    
    # REMOVE ITEM
    async def remove(
        self, 
        request: Request,
        db: AsyncSession, 
        cart_product_id: int = None,  
        user_id=None
    ):
        if user_id:
            return await self.remove_db_cart_item(db, user_id, cart_product_id)

        return await self.remove_redis_cart(request, cart_product_id)
    
    
    # ======================================================
    # REDIS CACHE CART (GUEST USER)
    # ======================================================
    
    #get redis cart
    async def get_redis_cart(
        self,
        request: Request
    ):
        # get redis cache key from cookie
        redis_cache_key = request.cookies.get(self.SESSION_COOKIE_KEY)
        
        if not redis_cache_key:
            return {
                "id": int(str(uuid.uuid4().int)[:4]),
                "status": "active",
                "user_id": None,
                "cart_products": [], 
                "subtotal": 0
                }

        data = await get_cache(redis_cache_key)

        if not data:
            return {
                "id": int(str(uuid.uuid4().int)[:4]),
                "status": "active",
                "user_id": None,
                "cart_products": [], 
                "subtotal": 0
                }

        return data
    
    # add item to redis cache
    async def add_to_redis_cart(
        self,
        request: Request,
        response: Response, 
        product_variant_id: int, 
        quantity: int,
        db: AsyncSession
    ):
        # check if variant id is valid
        result = await db.execute(
            select(ProductVariant)
            .join(ProductVariant.product)
            .options(selectinload(ProductVariant.product).selectinload(Product.category))
            .where(
                ProductVariant.id == product_variant_id,
                ProductVariant.is_active == True,
                Product.is_active == True
                )
        )
        variant = result.scalars().first()
        
        if not variant:
            raise HTTPException(
                status_code=400,
                detail="Invalid product_variant_id."
                )
        
        # get redis cache key from cookie
        redis_cache_key = request.cookies.get(self.SESSION_COOKIE_KEY)
        if redis_cache_key:
            cart = await get_cache(redis_cache_key)
        else:
            cart_uuid = str(uuid.uuid4())
            redis_cache_key = f"{self.REDIS_PREFIX}{cart_uuid}"
            
            cart = await get_cache(redis_cache_key)

        if not cart:
            cart = {
                "id": int(str(uuid.uuid4().int)[:4]),
                "status": "active",
                "user_id": None,
                "cart_products": [],
                "subtotal": 0
                }

        items = cart["cart_products"]
        found = False

        for item in items:
            if item["product_variant_id"] == product_variant_id:
                item["quantity"] += quantity
                found = True
                break

        if not found:
            items.append(
                {
                    "id": int(str(uuid.uuid4().int)[:4]),
                    "product_variant_id": product_variant_id,
                    "quantity": quantity,
                    "unit_price": str(variant.price)
                }
            )

        cart["cart_products"] = items
        
        await set_cache(redis_cache_key, cart, expire=self.GUEST_CART_EXPIRY)
        
        response.set_cookie(
            key=self.SESSION_COOKIE_KEY,
            value=redis_cache_key,
            httponly=True,
            max_age=self.GUEST_CART_EXPIRY,
            secure=True, 
            samesite="none"
        )
        return cart
    
    #update redis cart item
    async def update_redis_cart(
        self, 
        request: Request,
        cart_product_id: int, 
        quantity: int
    ):      
        # get redis cache key from cookie
        redis_cache_key = request.cookies.get(self.SESSION_COOKIE_KEY)
        
        cart = await self.get_redis_cart(request)
        items = cart.get("cart_products", [])

        for item in items:
            if item["id"] == cart_product_id:
                item["quantity"] = quantity

        cart["cart_products"] = items
        
        await set_cache(redis_cache_key, cart, self.GUEST_CART_EXPIRY)

        return cart
    
    # remove cache cart item
    async def remove_redis_cart(
        self, 
        request: Request,
        cart_product_id: int
    ):
        # get redis cache key from cookie
        redis_cache_key = request.cookies.get(self.SESSION_COOKIE_KEY)
        
        cart = await get_cache(redis_cache_key)
        items = cart.get("cart_products", {})

        # remove matching cart product
        items = [
            item for item in items
            if item["id"] != cart_product_id
        ]

        cart["cart_products"] = items
        await set_cache(redis_cache_key, cart, self.GUEST_CART_EXPIRY)

        return cart
    
    # ======================================================
    # DB CART (AUTH USER)
    # ======================================================

    async def get_or_create_db_cart(self, db: AsyncSession, user_id):
        result = await db.execute(
            select(Cart)
            .options(
                selectinload(Cart.cart_products)
                .selectinload(CartProduct.product_variant)
                .selectinload(ProductVariant.product)
                .selectinload(Product.category),
                selectinload(Cart.cart_products)
                .selectinload(CartProduct.product_variant)
                .selectinload(ProductVariant.images),
                )
            .where(
                Cart.user_id == user_id,
                Cart.status == CartStatus.ACTIVE
            )
        )

        cart = result.scalars().first()

        if not cart:
            cart = Cart(user_id=user_id, status="active")
            db.add(cart)
            await db.commit()
            await db.refresh(cart)
            
            # Re-fetch with full eager loading after create
            result = await db.execute(
                select(Cart)
                .options(
                    selectinload(Cart.cart_products)
                    .selectinload(CartProduct.product_variant)
                    .selectinload(ProductVariant.product)
                    .selectinload(Product.category),
                    selectinload(Cart.cart_products)
                    .selectinload(CartProduct.product_variant)
                    .selectinload(ProductVariant.images),
                )
                .where(Cart.id == cart.id)
            )
            cart = result.scalars().first()

        return cart 

    async def get_db_cart(self, db: AsyncSession, user_id):
        cart = await self.get_or_create_db_cart(db, user_id)
        return cart
    
    async def add_to_db_cart(self, db: AsyncSession, user_id, product_variant_id, quantity):
        # get users cart 
        cart = await self.get_or_create_db_cart(db, user_id)
        
        # check if variant id is valid
        result = await db.execute(
            select(ProductVariant)
            .join(ProductVariant.product)
            .options(selectinload(ProductVariant.product).selectinload(Product.category))
            .where(
                ProductVariant.id == product_variant_id,
                ProductVariant.is_active == True,
                Product.is_active == True
                )
        )
        variant = result.scalars().first()
        
        if not variant:
            raise HTTPException(
                status_code=400,
                detail="Invalid product_variant_id."
                )
            
        result = await db.execute(
            select(CartProduct)
            .options(selectinload(CartProduct.product_variant).selectinload(ProductVariant.product))
            .where(
                CartProduct.cart_id == cart.id,
                CartProduct.product_variant_id == product_variant_id
                )
            )
        item = result.scalars().first()
        if item:
            item.quantity += quantity
        else:
            item = CartProduct(
                cart_id=cart.id,
                product_variant_id=product_variant_id,
                quantity=quantity,
                unit_price=variant.price if variant else 0
            )
            db.add(item)

        await db.commit()
        await db.refresh(cart)
        
        result = await db.execute(
            select(Cart)
            .options(
                selectinload(Cart.cart_products)
                .selectinload(CartProduct.product_variant)
                .selectinload(ProductVariant.product)
                .selectinload(Product.category),
                selectinload(Cart.cart_products)
                .selectinload(CartProduct.product_variant)
                .selectinload(ProductVariant.images),
            )
            .where(Cart.id == cart.id)
        )
        return result.scalars().first()

    
    async def update_db_cart_item(self, db: AsyncSession, user_id, cart_product_id, quantity):
        cart = await self.get_or_create_db_cart(db, user_id)
        
        # check if cartproduct id is valid
        result = await db.execute(
            select(CartProduct).where(CartProduct.id == cart_product_id)
        )
        cart_product = result.scalars().first()

        if not cart_product:
            raise HTTPException(status_code=404, detail="CartProduct not found")
        

        result = await db.execute(
            select(CartProduct)
            .where(
                CartProduct.cart_id == cart.id,
                CartProduct.id == cart_product_id
                )
            )
        item = result.scalars().first()

        if item:
            item.quantity = quantity
            await db.commit()
            
        result = await db.execute(
        select(Cart)
            .options(
                selectinload(Cart.cart_products)
                .selectinload(CartProduct.product_variant)
                .selectinload(ProductVariant.product)
                .selectinload(Product.category),
                selectinload(Cart.cart_products)
                .selectinload(CartProduct.product_variant)
                .selectinload(ProductVariant.images),
            )
            .where(Cart.id == cart.id)
        )
        return result.scalars().first()
    
    async def remove_db_cart_item(self, db: AsyncSession, user_id, cart_product_id):
        cart = await self.get_or_create_db_cart(db, user_id)
        
        result = await db.execute(
            select(CartProduct).where(CartProduct.id == cart_product_id)
        )
        cart_product = result.scalars().first()

        if not cart_product:
            raise HTTPException(status_code=404, detail="CartProduct not found")

        await db.delete(cart_product)
        await db.commit()
        return cart
    
    
    # ======================================================
    # CART COUNT
    # ======================================================

    async def cart_count(self, request: Request, db: AsyncSession, user_id=None):
        if user_id:
            cart = await self.get_or_create_db_cart(db, user_id)
            return sum(i.quantity for i in cart.cart_products)
        
        cart = await self.get_redis_cart(request)
        return sum(i['quantity'] for i in cart.get("cart_products"))
    
    # ======================================================
    # SYNC ON LOGIN (REDIS → DB)
    # ======================================================

    async def cart_sync_on_login(
        self, 
        request: Request,
        response: Response,
        db: AsyncSession, 
        user_id: int
    ):
        # get redis cache key from cookie
        redis_cache_key = request.cookies.get(self.SESSION_COOKIE_KEY)
        
        redis_cart = await self.get_redis_cart(request)

        if not redis_cart.get("cart_products"):
            return

        for item in redis_cart["cart_products"]:
            await self.add_to_db_cart(
                db,
                user_id,
                item["product_variant_id"],
                item["quantity"]
            )

        # delete cart from redis cache
        await delete_cache(redis_cache_key)
        # delete cart cookie
        response.delete_cookie(key=self.SESSION_COOKIE_KEY)
        
    # ======================================================
    # Calculate offers and totals
    # ======================================================
    
    async def enrich_cart(self, request, db, user_id, cart, coupon_code, remove_coupon):
        # normalize
        # cart = CartResponse(**cart) if isinstance(cart, dict) else cart
        if not isinstance(cart, CartResponse):
            cart = CartResponse.model_validate(cart)

        # attach product-variant and product data 
        #along with subtotal calculation, (discount amount and discounted_amount initialization)
        cart = await self._attach_products(db, cart)
        
        # check for combo offer
        valid_combo_offers_result = await valid_combo_offers(db)
        if valid_combo_offers_result:
            combo_offers =  self.apply_combo_offers(
                cart_items=cart.cart_products,
                combo_offers=valid_combo_offers_result
            )
        cart.combo_offers = combo_offers
        
        # check if offer (item, category, store) exists
        # first get all active offers
        offers = await get_all_active_offers(db)
        if offers:
            bogo_map, item_map, category_map, store_offer = build_offer_indexes(offers)
            
            # apply offers
            for cart_product in cart.cart_products:
                if not cart_product.product_variant:
                    continue
                if cart_product.quantity_after_combo <= 0:
                    continue
                
                print("quantity_after_combo!!!!",cart_product.quantity, cart_product.quantity_after_combo)
                
                product_variant = (
                    ProductVariantResponse(**cart_product.product_variant)
                    if isinstance(cart_product.product_variant, dict)
                    else cart_product.product_variant
                )
                
                cart_product_response = await self._attach_offer(
                    db,
                    cart_product,
                    product_variant,
                    item_map,
                    category_map,
                    store_offer,
                    bogo_map
                )
                if cart_product_response.offer:
                    # if offer type in item,category or store then calculate for discount amount and discounted amount
                    if  cart_product_response.offer.type in (OfferType.ITEM, OfferType.CATEGORY, OfferType.STORE):
                        # calculate discount amount
                        discount_amount = self.calculate_product_discount_amount(
                            cart_product_response.offer, 
                            cart_product.product_variant.price,
                            cart_product.quantity_after_combo
                            # cart_product.quantity
                            )
                        cart_product_response.discount_amount = discount_amount
                        
                        #calculate discounted amount
                        discounted_amount = self.calculate_product_discounted_amount(
                            cart_product.subtotal,
                            discount_amount
                        )
                        cart_product_response.discounted_amount = discounted_amount
                    # handle bogo offer accordingly
                    elif cart_product_response.offer.type == OfferType.BOGO:
                        if cart_product_response.quantity != cart_product_response.offer.bogo_meta.buy_quantity:
                            cart_product_response.offer = None
                            continue
                        
                        if cart_product_response.offer.bogo_meta.apply_to_same_item:
                            response = self.calculate_same_item_bogo(
                                cart_product_response.offer,
                                cart_product_response
                                )
                            if response["free_items"] > 0:
                                cart_product_response.bogo_free_item = CartBOGOFreeItem(
                                    product_variant_id=response["get_item_id"],
                                    quantity=response["free_items"],
                                    unit_price=0 
                                )
                        else:
                            response = self.calculate_cross_item_bogo(
                                cart_product_response.offer,
                                cart_product_response
                            )
                            
                            if response["free_items"] > 0:
                                cart_product_response.bogo_free_item =  CartBOGOFreeItem(
                                    product_variant_id=response["get_item_id"],
                                    quantity=response["free_items"],
                                    unit_price=0 
                                )

                        # add bogo get item data
                        get_item_result = await db.execute(
                            select(ProductVariant)
                            .options(selectinload(ProductVariant.product).selectinload(Product.category),
                                    selectinload(ProductVariant.images)
                                    )
                            .where(ProductVariant.id == cart_product_response.offer.bogo_meta.get_item_id)
                        )
                        get_item = get_item_result.scalars().first()
                        cart_product_response.offer.bogo_meta.get_item = CartGetItem(
                            id=get_item.id,
                            sku=get_item.sku,
                            price=get_item.price,
                            image=get_item.images[0].image_url if get_item.images else None,
                            product = CartGetItemProduct(
                                id=get_item.product.id,
                                name=get_item.product.name,
                                description=get_item.product.description,
                            )
                        )
        
        # recalculate total cart totals
        cart = self.calculate_cart_total(cart)
        
        if combo_offers:
            total_bundle_price = 0
            total_final_price = 0
            for combo_offer in combo_offers:
                total_bundle_price += combo_offer['bundle_price']
                total_final_price += combo_offer['final_price']

            print("cart!!", cart.total_amount)
            cart.total_amount -= total_bundle_price
            cart.total_amount += total_final_price

        # coupon validation
        if remove_coupon:
            cart.coupon_applied = False
            cart.coupon_applicable = False
            cart.coupon_message = "No coupon applied."
            
            ## remove coupon from session/ db
            await self.remove_applied_coupon(request, db, user_id)
        else:
            cart = await self.coupon_validation(request, db, cart, coupon_code, user_id)

        return cart
    
    def calculate_cart_total(self, cart):
        subtotal = 0
        discount_amount = 0
        discounted_amount = 0
        total_amount = 0
        
        for cart_product in cart.cart_products:
            subtotal += cart_product.subtotal
            discount_amount += cart_product.discount_amount
            discounted_amount += cart_product.discounted_amount
            
        cart.subtotal = subtotal
        cart.discount_amount = discount_amount
        cart.discounted_amount = discounted_amount
        
        #calculate total
        total_amount = subtotal - discount_amount
        
        cart.total_amount = total_amount
        
        return cart
        
    async def _attach_products(self, db, cart):
        variant_ids = [i.product_variant_id for i in cart.cart_products]

        result = await db.execute(
            select(ProductVariant)
            .options(
                selectinload(ProductVariant.product).selectinload(Product.category),
                selectinload(ProductVariant.images),
            )
            .where(ProductVariant.id.in_(variant_ids))
        )

        variants = {v.id: v for v in result.scalars().all()}

        valid_cart_products = []
        for cart_product in cart.cart_products:
            variant = variants.get(cart_product.product_variant_id)
            if not variant:
                continue
            
            #assign variant
            cart_product.product_variant = variant
            
            cart_product.product_variant.image = (
                variant.images[0].image_url
                if variant.images
                else None
            )
            
            # ALWAYS use DB price (source of truth)
            price = float(variant.price)
            qty = cart_product.quantity

            subtotal = price * qty

            cart_product.quantity_after_combo = qty
            cart_product.subtotal = subtotal
            cart_product.discount_amount = 0
            cart_product.discounted_amount = subtotal
            
            valid_cart_products.append(cart_product)
            
        cart.cart_products = valid_cart_products
        return cart
    
    async def _attach_offer(
        self,
        db,
        cart_product,
        product_variant,
        item_map,
        category_map,
        store_offer,
        bogo_map
    ):        
        best_offer = resolve_offer(
            product_variant,
            item_map,
            category_map,
            store_offer,
            bogo_map
        )
                
        # attach object directly
        cart_product.offer = best_offer
        return cart_product
        
    def calculate_product_discount_amount(self, offer, product_price, quantity):
        product_total_price = float(product_price) * quantity
        discount_amount = 0
        if offer.discount_type == DiscountType.PERCENTAGE:
            discount_amount = (offer.discount_value / 100) * product_total_price
        elif offer.discount_type == DiscountType.FLAT:
            discount_amount = offer.discount_value
        
        return discount_amount
    
    def calculate_product_discounted_amount(self, subtotal, discount_amount):
        return subtotal - discount_amount
    
    # ======================================================
    # COUPON
    # ======================================================
    ## TODO: usage limit validations

    #calculate coupon discount
    def calculate_coupon_discount_amount(self, offer, subtotal):
        discount_amount = 0
        if offer.discount_type == DiscountType.PERCENTAGE:
            discount_amount = (offer.discount_value / 100) * subtotal
        elif offer.discount_type == DiscountType.FLAT:
            discount_amount = offer.discount_value
        
        return discount_amount
    
    #coupon validation
    async def coupon_validation(self, request, db, cart, coupon_code, user_id):
        now = datetime.utcnow()
        
        # get coupon with this coupon code when first applied
        if coupon_code:
            result = await db.execute(
                select(Offer)
                .where(
                    Offer.type == OfferType.COUPON,
                    Offer.code == coupon_code,
                    Offer.is_active == True,
                    Offer.start_date <= now,
                    Offer.end_date >= now,
                )

            )
            coupon_offer = result.scalars().first()
            
            if not coupon_offer:
                cart.coupon_applied = False
                cart.coupon_applicable = False
                cart.coupon_message = "Invalid coupon code."

                return cart
            
            ## add coupon in session/ db
            await self.add_applied_coupon(request, db, user_id, coupon_offer)
        else:
            #get coupon id from session/ db
            coupon_id = await self.get_applied_coupon(request, db, user_id)
            
            result = await db.execute(
                select(Offer)
                .where(
                    Offer.id == coupon_id,
                    Offer.type == OfferType.COUPON,
                    Offer.is_active == True,
                    Offer.start_date <= now,
                    Offer.end_date >= now,
                )

            )
            
            coupon_offer = result.scalars().first()
            
            if not coupon_offer:
                cart.coupon_applied = False
                cart.coupon_applicable = False
                cart.coupon_message = "Invalid coupon code."

                return cart
        
        # minimum spent amount validation
        if cart.subtotal < coupon_offer.min_spent_amount:
            cart.coupon_applied = False
            cart.coupon_applicable = False
            cart.coupon_message = f"Minimum spent amount must be above ${coupon_offer.min_spent_amount}"
            
            return cart
        
        #calculate coupon discount
        coupon_discount_amount = self.calculate_coupon_discount_amount(coupon_offer, cart.subtotal)
        
        # maximum discount amount validation
        if coupon_discount_amount > coupon_offer.max_discount_amount:
            coupon_discount_amount = coupon_offer.max_discount_amount
        
        cart.coupon_applied = True
        cart.coupon_applicable = True
        cart.coupon_message = "Coupon applied."
        cart.coupon_discount_amount = coupon_discount_amount
        
        cart.total_amount = cart.total_amount - coupon_discount_amount
            
        return cart
    
    # ======================================================
    # COUPON-CART RELATION
    # ======================================================
    
    # get coupon_id from session/ db
    async def get_applied_coupon(self, request, db, user_id):
        #if user is logged in coupon_id get from cart
        if user_id:
            result = await db.execute(
                select(Cart)
                .where(
                    Cart.user_id == user_id,
                    Cart.status == CartStatus.ACTIVE
                )
            )
            user_cart = result.scalars().first()
            
            if not user_cart:
                return None 
            
            return user_cart.coupon_id
        else:
            # get from session
            # get redis cache key from cookie
            redis_cache_key = request.cookies.get(self.SESSION_COOKIE_KEY)
            if not redis_cache_key:
                return None
            cart = await get_cache(redis_cache_key)
            if 'coupon_id' in cart and cart.get('coupon_id'):
                return cart['coupon_id']
    
    async def add_applied_coupon(self, request, db, user_id, coupon):
        # if user is logged in add coupon to cart
        if user_id:
            result = await db.execute(
                select(Cart)
                .where(
                    Cart.user_id == user_id,
                    Cart.status == CartStatus.ACTIVE
                )
            )
            user_cart = result.scalars().first()
            
            if not user_cart:
                return None 
            
            user_cart.coupon_id = coupon.id
            await db.commit()
            await db.refresh(user_cart)            
        else:
            # add coupon_id in session
            # get redis cache key from cookie
            redis_cache_key = request.cookies.get(self.SESSION_COOKIE_KEY)
            if not redis_cache_key:
                return None
            cart = await get_cache(redis_cache_key)
            cart["coupon_id"] = coupon.id
            
            await set_cache(redis_cache_key, cart, expire=self.GUEST_CART_EXPIRY)
    
    async def remove_applied_coupon(self, request, db, user_id):
        if user_id:
            result = await db.execute(
                select(Cart)
                .where(
                    Cart.user_id == user_id,
                    Cart.status == CartStatus.ACTIVE
                )
            )
            user_cart = result.scalars().first()
            
            if not user_cart:
                return None 
            
            user_cart.coupon_id = None
            await db.commit()
            await db.refresh(user_cart)
        else:
            # add coupon_id in session
            # get redis cache key from cookie
            redis_cache_key = request.cookies.get(self.SESSION_COOKIE_KEY)
            if not redis_cache_key:
                return None
            cart = await get_cache(redis_cache_key)
            if not cart:
                return None
            cart["coupon_id"] =  None
            
            await set_cache(redis_cache_key, cart, expire=self.GUEST_CART_EXPIRY)
    
    # ======================================================
    # BOGO OFFER
    # ======================================================
    def calculate_same_item_bogo(self, offer, cart_product_response):
    
        bogo = offer.bogo_meta

        # 1. Get cart item (same product for buy + get)
        item = cart_product_response.offer.bogo_meta.buy_item_id

        # 2. Safety check
        if not item:
            return {
                "free_items": 0,
                "discount": 0,
                "payable_quantity": 0,
                "buy_item_id": bogo.buy_item_id,
                "get_item_id": bogo.get_item_id
            }

        # 3. Total quantity in cart
        quantity = cart_product_response.quantity
        unit_price = float(cart_product_response.unit_price)

        # 4. Eligible sets
        eligible_sets = quantity // bogo.buy_quantity

        # 5. Free items
        free_items = eligible_sets * bogo.get_quantity

        # 6. Discount value
        discount = free_items * unit_price

        # 7. Payable quantity
        payable_quantity = quantity - free_items

        return {
            "free_items": free_items,
            "discount": discount,
            "payable_quantity": payable_quantity,
            "buy_item_id": bogo.buy_item_id,
            "get_item_id": bogo.get_item_id
        }
        
    def calculate_cross_item_bogo(self, offer, cart_product_response):
        bogo = offer.bogo_meta
        
        buy_item = cart_product_response.offer.bogo_meta.buy_item_id 
        get_item = cart_product_response.offer.bogo_meta.get_item_id
        
        if not buy_item or not get_item:
            return {
                "free_items": 0,
                "discount": 0,
                "buy_item_id": bogo.buy_item_id,
                "get_item_id": bogo.get_item_id
        } 

        # 3. Calculate eligible BOGO sets
        eligible_sets = buy_item.quantity // bogo.buy_quantity

        # 4. Total eligible free quantity from offer
        eligible_free_qty = eligible_sets * bogo.get_quantity

        # 5. Cap by actual cart quantity of get item
        free_qty = min(get_item.quantity, eligible_free_qty)

        # 6. Calculate discount value (important for totals)
        discount = float(get_item.unit_price) * free_qty

        return {
            "free_items": free_qty,
            "discount": discount,
            "buy_item_id": bogo.buy_item_id,
            "get_item_id": bogo.get_item_id
        }
        
    # ======================================================
    # COMBO OFFER
    # ======================================================
    def build_stock(self, cart_items):
        """
        Build a stock map from cart items.

        Returns:
            dict[product_variant_id, quantity]
            Example: {1: 5, 2: 3}
        """
        stock = defaultdict(int)

        for item in cart_items:
            stock[item.product_variant_id] += item.quantity
        
        return stock
    
    def get_max_applications(self, combo_offer, stock):
        """
        Calculate the maximum number of times a combo offer
        can be applied based on currently available stock.

        The limiting item in the combo determines the result.

        Returns:
            int: Number of valid combo applications.
        """
    
        max_count = None

        for item in combo_offer.items:

            available = stock[item.product_variant_id]
            possible = available // item.quantity

            if max_count is None:
                max_count = possible
            else:
                max_count = min(max_count, possible)

        return max_count or 0

    def consume_stock(self, combo_offer, stock, count, cart_items):
        """
        Deduct stock used by an applied combo offer.

        Args:
            combo_offer: Offer being applied.
            stock: Mutable stock map.
            count: Number of times the combo was applied.
        """
        for item in combo_offer.items:
            stock[item.product_variant_id] -= item.quantity * count
        
        # sync remaining quantities back to cart items
        for cart_item in cart_items:
            cart_item.quantity_after_combo = stock[cart_item.product_variant_id]
    
    def apply_combo_offers(self, cart_items, combo_offers):
        """
        Apply combo offers against cart inventory.

        Workflow:
        1. Build available stock from cart items.
        2. Determine how many times each offer can be applied.
        3. Calculate bundle value and discount.
        4. Record applied offers.
        5. Consume used stock to prevent overlapping discounts.

        Returns:
            list[dict]: Applied offer details including
            discount amount, final price, and application count.
        """
    
        stock = self.build_stock(cart_items)

        results = []
        for offer in combo_offers:
            max_count = self.get_max_applications(offer, stock)

            if max_count <= 0:
                continue

            bundle_price = 0

            for item in offer.items:
                price = item.product_variant.price  # or join loaded price
                bundle_price += price * item.quantity

            total_bundle = bundle_price * max_count
            

            # discount logic (example percentage)
            if offer.discount_type == ComboDiscountType.PERCENTAGE.value:
                discount = total_bundle * (offer.discount_value / 100)
            elif offer.discount_type == ComboDiscountType.FIXED.value:
                discount = offer.discount_value * max_count
            elif offer.discount_type == ComboDiscountType.COMBO_PRICE.value:
                discount = total_bundle - (offer.discount_value * max_count)

            # CRITICAL STEP
            self.consume_stock(offer, stock, max_count, cart_items)
            
            results.append({
                "id": offer.id,
                "name": offer.name,
                "discount_type": offer.discount_type.value,
                "applied_count": max_count,
                "bundle_price": float(total_bundle),
                "discount": discount,
                "final_price": float(total_bundle - discount),
                "priority": offer.priority,
                "stock": stock
            })
            
        return results