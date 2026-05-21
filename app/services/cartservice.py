import json
import uuid
from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.carts import CartProductResponse, CartResponse, ProductResponse
from app.models.carts import Cart, CartProduct, CartStatus
from app.models.offers import DiscountType
from app.models.products import Product, ProductVariant
from app.services.offerservice import build_offer_indexes, get_all_active_offers, resolve_offer
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
            .options(selectinload(ProductVariant.product))
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
            max_age=self.GUEST_CART_EXPIRY
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
            .options(selectinload(Cart.cart_products))
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
            .options(selectinload(ProductVariant.product))
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
        
        # load 
        # result = await db.execute(
        #     select(Cart)
        #     .options(
        #         selectinload(Cart.cart_products)
        #         .selectinload(CartProduct.product_variant)
        #         .selectinload(ProductVariant.product),

        #         selectinload(Cart.cart_products)
        #         .selectinload(CartProduct.product_variant)
        #         .selectinload(ProductVariant.images),
        #     )
        #     .where(Cart.id == cart.id)
        # )

        # cart = result.scalars().first()

        return cart

    
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

        return cart
    
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
    
    async def enrich_cart(self, db, cart):
        # normalize
        cart = CartResponse(**cart) if isinstance(cart, dict) else cart

        # attach product-variant and product data 
        #along with subtotal calculation, (discount amount and discounted_amount initialization)
        cart = await self._attach_products(db, cart)
        
        # check if offer (item, category, store) exists
        # first get all active offers
        offers = await get_all_active_offers(db)
        if offers:
            item_map, category_map, store_offer, bogo_map = build_offer_indexes(offers)

            # apply offers
            for cart_product in cart.cart_products:
                if not cart_product.product_variant:
                    continue
                product = (
                    ProductResponse(**cart_product.product_variant["product"])
                    if isinstance(cart_product.product_variant, dict)
                    else cart_product.product_variant.product
                )
                
                cart_product_response = await self._attach_offer(
                    db,
                    cart_product,
                    product,
                    item_map,
                    category_map,
                    store_offer,
                    bogo_map
                )
            
                # calculate discount amount
                discount_amount = self.calculate_product_discount_amount(
                    cart_product_response.offer, 
                    cart_product.product_variant.price,
                    cart_product.quantity
                    )
                cart_product_response.discount_amount = discount_amount
                
                #calculate discounted amount
                discounted_amount = self.calculate_product_discounted_amount(
                    cart_product.subtotal,
                    discount_amount
                )
                cart_product_response.discounted_amount = discounted_amount
        
        # total cart totals
        cart = self.calculate_cart_total(cart)
        return cart
    
        cart.discount_amount = discount_amount
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
        total = subtotal - discount_amount
        
        cart.total_amount = total
        
        return cart
        
    async def _attach_products(self, db, cart):
        variant_ids = [i.product_variant_id for i in cart.cart_products]

        result = await db.execute(
            select(ProductVariant)
            .options(
                selectinload(ProductVariant.product),
                selectinload(ProductVariant.images)
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
            
            # ALWAYS use DB price (source of truth)
            price = float(variant.price)
            qty = cart_product.quantity

            subtotal = price * qty

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
        product,
        item_map,
        category_map,
        store_offer,
        bogo_map
    ):        
        best_offer = resolve_offer(
            product,
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