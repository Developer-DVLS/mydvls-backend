from datetime import datetime
from enum import Enum
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orders import DeliveryStatus, Order, OrderItem, OrderStatus
from app.models.products import Product, ProductVariant
from app.models.user import User
from app.auth.permissions import staff_only
from app.core.database import get_db
from app.services.reportservice import DateFilter, ReportService

report_router = APIRouter(prefix="/dashboard/report", tags=['Reports'])
    
@report_router.get("/overview/")
async def overview(
    filter_type: DateFilter = Query(DateFilter.THIS_MONTH),
    start_date: datetime | None = Query(
        None,
        description="Start date for custom filter."
    ),
    end_date: datetime | None = Query(
        None,
        description="End date for custom filter."
    ),
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    #--------------------------
    #date filtering
    #--------------------------
    report_service = ReportService
    start, end = report_service.get_date_range(
        filter_type,
        start_date,
        end_date,
    )
    
    #--------------------------
    #sales summary
    #--------------------------
    sales_query =(
        select(
            func.coalesce(func.sum(Order.subtotal), 0).label("gross_sales"),
            func.coalesce(
                func.sum(
                    Order.subtotal - Order.discount_amount
                ),
                0,
            ).label("net_sales"),
            func.coalesce(func.sum(Order.total), 0).label("total_sales"),
            func.coalesce(func.sum(Order.tax_amount), 0).label("tax_amount"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("discount_amount"),
            func.coalesce(func.sum(Order.delivery_charge), 0).label("delivery_charge"),
        )
        .where(
            Order.status == OrderStatus.COMPLETED,
            Order.payment_status == "paid",
            Order.delivery_status == DeliveryStatus.DELIVERED
            )
    )
    if start and end:
        sales_query = sales_query.where(
            Order.created_at >= start,
            Order.created_at < end,
        )
    sales_result = await db.execute(sales_query)
    sales = sales_result.one()
    
    #--------------------------
    #orders summary
    #--------------------------
    order_query = (
        select(
                func.count(case((Order.status == OrderStatus.COMPLETED, 0))).label("completed_orders"),
                func.count(case((Order.status == OrderStatus.PENDING, 0))).label("pending_orders"),
                func.count(case((Order.status == OrderStatus.CANCELLED, 0))).label("cancelled_orders"),
                func.count(case((Order.status == OrderStatus.REFUNDED, 0))).label("refunded_orders"),
            )
    )
    if start and end:
        order_query = order_query.where(
            Order.created_at >= start,
            Order.created_at < end,
        )
    order_result = await db.execute(order_query)
    orders = order_result.one()

    #--------------------------
    #products summary
    #--------------------------
    product_query = (
        select(
            func.count(Product.id).label("total_products"),
            func.count(case((Product.is_active == True, 0))).label("active_products"),
            func.count(case((Product.is_active == False, 0))).label("inactive_products"),
        )
    )
    if start and end:
        product_query = product_query.where(
            Product.created_at >= start,
            Product.created_at < end,
        )
    product_result = await db.execute(product_query)
    products = product_result.one()
    
    variant_query = (
        select(
            func.count(ProductVariant.id).label("total_variants"),
            func.count(
                case((ProductVariant.stock_quantity == 0, 0))
            ).label("out_of_stock_products"),
            func.count(
                case(
                    (
                        and_(
                            ProductVariant.stock_quantity >= 1,
                            ProductVariant.stock_quantity <= 5,
                        ),
                        1,
                    )
                )
            ).label("low_stock_products"),
        )
    )
    if start and end:
        variant_query = variant_query.where(
            ProductVariant.created_at >= start,
            ProductVariant.created_at < end,
        )
    variant_result = await db.execute(variant_query) 
    variants = variant_result.one()
    
    #--------------------------
    #users summary
    #--------------------------
    user_query = (
        select(
            func.count(User.id).label("total_users"),
            func.count(case((User.is_active == True, 0))).label("active_users"),
            func.count(case((User.is_active == False, 0))).label("inactive_users"),
            func.count(case((User.is_guest == True, 0))).label("guest_users")
        )
    )
    if start and end:
        user_query = user_query.where(
            User.created_at >= start,
            User.created_at < end,
        )
    user_result = await db.execute(user_query)
    users = user_result.one()
    
    return {
        "sales_summary": {
            "gross_sales": sales.gross_sales,
            "net_sales": sales.net_sales,
            "total_sales": sales.total_sales,
            "discount_amount": sales.discount_amount,
            "shipping_charge": sales.delivery_charge,
            "tax_amount": sales.tax_amount
        },
        "order_summary": {
            "completed_orders": orders.completed_orders,
            "pending_orders": orders.pending_orders,
            "cancelled_orders": orders.cancelled_orders,
            "refunded_orders": orders.refunded_orders,
        },
        "product_summary": {
            "total_products": products.total_products,
            "active_products": products.active_products,
            "inactive_products": products.inactive_products,
            "out_of_stock_products": variants.out_of_stock_products,
            "low_stock_products": variants.low_stock_products,
            "total_variants": variants.total_variants,
        },
        "user_summary": {
            "total_users": users.total_users,
            "active_users": users.active_users,
            "inactive_users": users.inactive_users,
            "guest_users": users.guest_users,
        }
    }
    

@report_router.get("/sales-report/")
async def sales_report(
    filter_type: DateFilter = Query(DateFilter.THIS_MONTH),
    start_date: datetime | None = Query(
        None,
        description="Start date for custom filter."
    ),
    end_date: datetime | None = Query(
        None,
        description="End date for custom filter."
    ),
    search: str | None = Query(
        None,
        description="Search orders by order number, receiver's name, email, or phone number.",
        ),
    order_status: Optional[OrderStatus] = None,
    delivery_status: Optional[DeliveryStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    #--------------------------
    #date filtering
    #--------------------------
    report_service = ReportService
    start, end = report_service.get_date_range(
        filter_type,
        start_date,
        end_date,
    )
    
    #--------------------------
    #sales summary
    #--------------------------
    summary_query = (
        select(
            func.coalesce(func.sum(Order.subtotal), 0).label("gross_sales"),
            func.coalesce(
                func.sum(Order.subtotal - Order.discount_amount),
                0,
            ).label("net_sales"),
            func.coalesce(func.sum(Order.total), 0).label("total_sales"),
            func.coalesce(func.sum(Order.tax_amount), 0).label("tax_amount"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("discount_amount"),
            func.coalesce(func.sum(Order.delivery_charge), 0).label("delivery_charge"),
            func.count(Order.id).label("total_orders"),
        )
        .where(
            Order.status == OrderStatus.COMPLETED,
            Order.payment_status == "paid",
            Order.delivery_status == DeliveryStatus.DELIVERED,
        )
    )

    if start and end:
        summary_query = summary_query.where(
            Order.created_at >= start,
            Order.created_at < end,
        )

    summary = (await db.execute(summary_query)).one()
    
    #--------------------------
    #orders
    #--------------------------
    
    orders_query = (
        select(Order)
        .options(
            selectinload(Order.user)
        )
        .where(
            Order.status == OrderStatus.COMPLETED,
            Order.payment_status == "paid",
            Order.delivery_status == DeliveryStatus.DELIVERED,
        )
        .order_by(Order.created_at.desc())
    )

    if start and end:
        orders_query = orders_query.where(
            Order.created_at >= start,
            Order.created_at < end,
        )
    
    if search:
        search = search.strip()

        orders_query = orders_query.where(
            or_(
                Order.receiver_first_name.ilike(f"%{search}%"),
                Order.receiver_last_name.ilike(f"%{search}%"),
                Order.receiver_email.ilike(f"%{search}%"),
                Order.receiver_phone.ilike(f"%{search}%"),
                Order.order_number == search
            )
        )
    
    if order_status:
        orders_query = orders_query.where(
            Order.status == order_status
        )
    if delivery_status:
        orders_query = orders_query.where(
            Order.delivery_status == delivery_status
        )

    orders_query = orders_query.offset(skip).limit(limit)

    orders = (await db.execute(orders_query)).scalars().all()
    
    return {
        "summary": {
            "gross_sales": summary.gross_sales,
            "net_sales": summary.net_sales,
            "discount_amount": summary.discount_amount,
            "tax_amount": summary.tax_amount,
            "shipping_charge": summary.delivery_charge,
            "total_sales": summary.total_sales,
            "total_orders": summary.total_orders,
        },
        "orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "customer": order.user.email if order.user else None,
                "date": order.created_at.strftime("%Y %b %-d"),
                "subtotal": order.subtotal,
                "discount": order.discount_amount,
                "tax": order.tax_amount,
                "shipping": order.delivery_charge,
                "total": order.total,
                "payment_method": order.payment_method,
            }
            for order in orders
        ]
    }
    
@report_router.get("/sales-by-item/")
async def sales_by_item(
    filter_type: DateFilter = Query(
        DateFilter.THIS_MONTH,
        description="Date filter for the report."
    ),
    start_date: datetime | None = Query(
        None,
        description="Start date for custom filter."
    ),
    end_date: datetime | None = Query(
        None,
        description="End date for custom filter."
    ),
    search: str | None = Query(
        None,
        description="Search by product or variant name."
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    #--------------------------
    #date filtering
    #--------------------------
    report_service = ReportService()
    start, end = report_service.get_date_range(
        filter_type,
        start_date,
        end_date,
    )
    
    query = (
        select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            ProductVariant.id.label("variant_id"),
            ProductVariant.sku.label("variant_sku"),
            func.sum(OrderItem.quantity).label("quantity_sold"),
            func.sum(OrderItem.unit_price).label("gross_sales"),
            func.sum(OrderItem.total_price).label("total_sales"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(ProductVariant, ProductVariant.id == OrderItem.product_variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(
            Order.status == OrderStatus.COMPLETED,
            Order.payment_status == "paid",
            Order.delivery_status == DeliveryStatus.DELIVERED,
        )
    )
    
    if start and end:
        query = query.where(
            Order.created_at >= start,
            Order.created_at < end,
        )
        
    if search:
        query = query.where(
            or_(
                Product.name.ilike(f"%{search}%"),
                ProductVariant.sku.ilike(f"%{search}%"),
            )
        )
        
    #grouping
    query = (
        query
        .group_by(
            Product.id,
            Product.name,
            ProductVariant.id,
            ProductVariant.sku,
        )
        .order_by(func.sum(OrderItem.total_price).desc())
        .offset(skip)
        .limit(limit)
    )

    results = (await db.execute(query)).all()
    
    return [
        {
            "product_id": row.product_id,
            "product_name": row.product_name,
            "variant_id": row.variant_id,
            "variant_name": row.variant_name,
            "quantity_sold": row.quantity_sold,
            "gross_sales": row.gross_sales,
            "discount_amount": row.discount_amount,
            "tax_amount": row.tax_amount,
            "total_sales": row.total_sales,
        }
        for row in results
    ]