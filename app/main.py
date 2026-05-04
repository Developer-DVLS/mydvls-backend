from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import engine, Base
from app import models
from app.utils.create_superuser import create_superuser

from app.models.user import User    
from app.models.address import Address
from app.api.v1.endpoints.users import user_router
from app.api.v1.endpoints.media import media_router
from app.api.v1.endpoints.dashboard.users import admin_user_router
from app.api.v1.endpoints.dashboard.productcategories import product_category_router, admin_product_category_router
from app.api.v1.endpoints.dashboard.products import product_router, admin_product_router
from app.api.v1.endpoints.dashboard.productvariants import product_variant_router, admin_variant_router
from app.api.v1.endpoints.shop import shop_router

app = FastAPI(
    title="FastAPI App",
    description="A FastAPI backend with PostgreSQL",
    version="1.0.0",
)

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


# =========================
# CORS CONFIGURATION
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change in production
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


@app.on_event("startup")
async def startup_event():
    # run only once
    await create_superuser()