from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app import models
from app.utils.create_superuser import create_superuser
from app.core.redis import redis_client

from app.models.user import User    
from app.models.address import Address
from app.api.v1.endpoints.users import user_router
from app.api.v1.endpoints.media import media_router
from app.api.v1.endpoints.dashboard.users import admin_user_router
from app.api.v1.endpoints.dashboard.productcategories import product_category_router, admin_product_category_router
from app.api.v1.endpoints.dashboard.products import product_router, admin_product_router
from app.api.v1.endpoints.dashboard.productvariants import product_variant_router, admin_variant_router
from app.api.v1.endpoints.dashboard.offers import offer_router
from app.api.v1.endpoints.shop import shop_router
from app.api.v1.endpoints.cart import cart_router
from app.api.v1.endpoints.dashboard.delivery import delivery_router
from app.api.v1.endpoints.dashboard.taxes import tax_router
from app.api.v1.endpoints.orders import order_router
from app.api.v1.endpoints.dashboard.orders import admin_order_router
from app.api.v1.endpoints.dashboard.carts import admin_cart_router
from app.api.v1.endpoints.demorequest import demo_request_router
from app.api.v1.endpoints.dashboard.demorequest import admin_demo_request_router
from app.api.v1.endpoints.dashboard.subscriptionplan import admin_subscription_plan, subscription_plan

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    health_check()
    try:
        await redis_client.ping()
        print("Redis connected")
    except Exception as e:
        print("Redis connection failed:", e)

    await create_superuser()
    
    yield

    # shutdown
    await redis_client.close()
    print("Redis connection closed")


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(user_router)
app.include_router(media_router)
app.include_router(admin_user_router)
app.include_router(product_category_router)
app.include_router(admin_product_category_router)
app.include_router(product_router)
app.include_router(admin_product_router)
app.include_router(product_variant_router)
app.include_router(admin_variant_router)
app.include_router(shop_router)
app.include_router(offer_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(delivery_router)
app.include_router(tax_router)
app.include_router(admin_order_router)
app.include_router(admin_cart_router)
app.include_router(demo_request_router)
app.include_router(admin_demo_request_router)
app.include_router(admin_subscription_plan)
app.include_router(subscription_plan)

# =========================
# CORS CONFIGURATION
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ROOT ENDPOINT
# =========================
@app.get("/")
def read_root():
    return {
        "message": "FastAPI is running 🚀",
        "status": "success"
    }

# =========================
# HEALTH CHECK
# =========================
@app.get("/health")
def health_check():
    return {"status": "ok"}
