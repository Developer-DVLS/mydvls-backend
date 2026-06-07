import select
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.carts import CartResponse
from app.core.database import get_db
from app.models.offers import ComboOffer
from app.services.cartservice import CartService
from app.services.offerservice import validate_combo_offer
from app.services.security import get_current_user_optional

cart_router = APIRouter(prefix="/cart", tags=["Cart"])

cart_service = CartService()

@cart_router.get("/", response_model=CartResponse | dict )
async def get_cart(
    request: Request,
    cart_count: Optional[bool] = False,
    coupon_code: Optional[str] = None,
    remove_coupon: Optional[bool] = True,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None
    
    # to get cart count
    if cart_count:
        return {"cart_count" : await cart_service.cart_count(request=request, db=db, user_id=user_id)}
        
    # get cart from session / db
    cart = await cart_service.get_cart(
        request=request,
        db=db,
        user_id=user_id
    )
    
    # calculate totals    
    enriched_cart = await cart_service.enrich_cart(
        request=request,
        db=db,
        user_id=user_id,
        cart=cart,
        coupon_code=coupon_code,
        remove_coupon=remove_coupon
    )

    return enriched_cart
    

@cart_router.post("/add-to-cart/")
async def add_to_cart(
    request: Request,
    response: Response,
    product_variant_id: int,
    quantity: int = 1,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None

    await cart_service.add(
        request=request,
        response=response,
        db=db,
        product_variant_id=product_variant_id,
        quantity=quantity,
        user_id=user_id
    )
    
    return {
        "status": True,
        "message": "Item added successfully"
    }

@cart_router.patch("/update-cart-product/{cart_product_id}/")
async def update_cart_product(
    request: Request,
    cart_product_id: int,
    quantity: int = 1,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None

    await cart_service.update(
        request=request,
        db=db,  
        quantity=quantity, 
        cart_product_id=cart_product_id, 
        user_id=user_id
    )
    
    return {
        "status": True,
        "message": "Item updated successfully"
    }


@cart_router.delete("/delete-cart-product/{cart_product_id}/")
async def delete_cart_product(
    request: Request,
    cart_product_id: int,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None

    await cart_service.remove(
        request=request,
        db=db,  
        cart_product_id=cart_product_id, 
        user_id=user_id
    )
    
    return {
        "status": True,
        "message": "Item deleted successfully"
    }

@cart_router.delete("/clear-cart/")
async def clear_cart(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None

    await cart_service.clear(
        request=request,
        db=db,  
        user_id=user_id
    )
    
    return {
        "status": True,
        "message": "Cart cleared."
    }


## add combo offer product_variant in cart
@cart_router.post("/add-combo-to-cart/")
async def add_combo_to_cart(
    request: Request,
    response: Response,
    combo_offer_id: int,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None
    
    # get combo offer 
    combo_offer = await validate_combo_offer(db, combo_offer_id)
    
    if combo_offer:
        for item in combo_offer.items:            
            await cart_service.add(
                request=request,
                response=response,
                db=db,
                product_variant_id=item.product_variant_id,
                quantity=item.quantity,
                user_id=user_id
            )
        
        return {
            "status": True,
            "message": "Items added successfully"
        }
    
    raise HTTPException(
        status_code=400,
        detail="Invalid combo offer."
    )
    
## remove combo offer product_variant in cart
@cart_router.delete("/remove-combo-from-cart/")
async def remove_combo_from_cart(
    request: Request,
    response: Response,
    combo_offer_id: int,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None
    
    # get combo offer 
    combo_offer = await validate_combo_offer(db, combo_offer_id)
    
    if combo_offer:
        for item in combo_offer.items:   
            print("!!!", item.quantity)         
            await cart_service.remove_combo_item(
                request=request,
                db=db,  
                quantity=item.quantity, 
                product_variation_id=item.product_variant_id, 
                user_id=user_id
            )
        
        return {
            "status": True,
            "message": "Items removed successfully"
        }
    
    raise HTTPException(
        status_code=400,
        detail="Invalid combo offer."
    )