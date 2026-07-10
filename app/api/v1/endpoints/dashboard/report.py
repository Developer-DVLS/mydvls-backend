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
from app.models.visits import Visit
from app.services.reportservice import DateFilter, ReportService

report_router = APIRouter(prefix="/dashboard/report", tags=['Reports'])
    
def get_period(column, period_type: str):
    if period_type == "daily":
        return func.date(column)
    elif period_type == "weekly":
        return func.date_trunc("week", column)
    elif period_type == "monthly":
        return func.date_trunc("month", column)
    else:
        return func.date_trunc("hour", column)
        
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
    report_service = ReportService()
    start, end = report_service.get_date_range(
        filter_type,
        start_date,
        end_date,
    )
        
    #--------------------------
    #group filters
    #--------------------------
    period_type = None
    if filter_type in {
        DateFilter.TODAY,
        DateFilter.YESTERDAY,
        DateFilter.THIS_WEEK,
        DateFilter.LAST_WEEK,
        DateFilter.LAST_7_DAYS,
        DateFilter.THIS_MONTH,
        DateFilter.LAST_MONTH,
        DateFilter.LAST_30_DAYS,
        DateFilter.DAILY,
    }:
        period_type = "daily"
    elif filter_type == DateFilter.WEEKLY:
        period_type = "weekly"
    elif filter_type in {
        DateFilter.THIS_YEAR,
        DateFilter.LAST_YEAR,
        DateFilter.LAST_3_MONTHS,
        DateFilter.LAST_6_MONTHS,
        DateFilter.MONTHLY
        }:
        period_type = "monthly"
    else:
        # Custom
        if start and end and (end - start).days <= 31:
            period = func.date(Order.created_at)
            period_type = "daily"
        else:
            period = func.date_trunc("month", Order.created_at)
            period_type = "monthly"
    
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
            func.date(Order.created_at) >= start.date(),
            func.date(Order.created_at) < end.date(),
        )
    sales_result = await db.execute(sales_query)
    sales = sales_result.one()
    
    #--------------------------
    #sales trend
    #--------------------------
    sales_trend = []
    if period_type is not None:
        sales_period = get_period(Order.created_at, period_type)
        sales_trend_query = (
            select(
                sales_period.label("period"),
                func.coalesce(func.sum(Order.subtotal), 0).label("gross_sales"),
                func.coalesce(
                    func.sum(Order.subtotal - Order.discount_amount),
                    0,
                ).label("net_sales"),
                func.coalesce(func.sum(Order.total), 0).label("total_sales"),
                func.coalesce(func.sum(Order.discount_amount), 0).label("discount_amount"),
                func.coalesce(func.sum(Order.tax_amount), 0).label("tax_amount"),
                func.coalesce(func.sum(Order.delivery_charge), 0).label("shipping_charge"),
            )
            .where(
                Order.status == OrderStatus.COMPLETED,
                Order.payment_status == "paid",
                Order.delivery_status == DeliveryStatus.DELIVERED,
            )
        )

        if start and end:
            sales_trend_query = sales_trend_query.where(
                func.date(Order.created_at) >= start.date(),
                func.date(Order.created_at) < end.date(),
            )

        sales_trend_query = (
            sales_trend_query
            .group_by(sales_period)
            .order_by(sales_period)
        )

        result = await db.execute(sales_trend_query)

        for row in result.all():
            if period_type == "daily":
                label = row.period.strftime("%Y %b %-d")
            elif period_type == "weekly":
                label = f"Week of {row.period.strftime('%Y %b %-d')}"
            else:
                label = row.period.strftime("%Y %b")

            sales_trend.append({
                "label": label,
                "gross_sales": float(row.gross_sales),
                "net_sales": float(row.net_sales),
                "discount_amount": float(row.discount_amount),
                "tax_amount": float(row.tax_amount),
                "shipping_charge": float(row.shipping_charge),
                "total_sales": float(row.total_sales),
            })
    
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
            func.date(Order.created_at) >= start.date(),
            func.date(Order.created_at) < end.date(),
        )
    order_result = await db.execute(order_query)
    orders = order_result.one()
    
    #--------------------------
    #orders trend
    #--------------------------
    order_trend = []

    if period_type is not None:
        order_period = get_period(Order.created_at, period_type)

        order_trend_query = (
            select(
                order_period.label("period"),
                func.count(case((Order.status == OrderStatus.COMPLETED, 1))).label("completed_orders"),
                func.count(case((Order.status == OrderStatus.PENDING, 1))).label("pending_orders"),
                func.count(case((Order.status == OrderStatus.CANCELLED, 1))).label("cancelled_orders"),
                func.count(case((Order.status == OrderStatus.REFUNDED, 1))).label("refunded_orders"),
            )
        )

        if start and end:
            order_trend_query = order_trend_query.where(
            func.date(Order.created_at) >= start.date(),
            func.date(Order.created_at) < end.date(),
            )

        order_trend_query = (
            order_trend_query
            .group_by(order_period)
            .order_by(order_period)
        )

        result = await db.execute(order_trend_query)

        for row in result.all():
            if period_type == "daily":
                label = row.period.strftime("%Y %b %-d")
            elif period_type == "weekly":
                label = f"Week of {row.period.strftime('%Y %b %-d')}"
            else:
                label = row.period.strftime("%Y %b")

            order_trend.append({
                
                "label": label,
                "completed_orders": row.completed_orders,
                "pending_orders": row.pending_orders,
                "cancelled_orders": row.cancelled_orders,
                "refunded_orders": row.refunded_orders,
            })

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
            func.date(Product.created_at) >= start.date(),
            func.date(Product.created_at) < end.date(),
        )
    product_result = await db.execute(product_query)
    products = product_result.one()
    
    #--------------------------
    #products trend
    #--------------------------
    print("period_type!!!!", period_type)
    product_trend = []
    
    if period_type is not None:
        product_period = get_period(Product.created_at, period_type)
        print("product_period!!!", product_period)
        product_trend_query = (
            select(
                product_period.label("period"),
                func.count(Product.id).label("total_products"),
                func.count(case((Product.is_active == True, 1))).label("active_products"),
                func.count(case((Product.is_active == False, 1))).label("inactive_products"),
            )
        )
        print("start, end!!!!", start, end)
        if start and end:
            product_trend_query = product_trend_query.where(
                func.date(Product.created_at) >= start.date(),
                func.date(Product.created_at) < end.date(),
            )

        product_trend_query = (
            product_trend_query
            .group_by(product_period)
            .order_by(product_period)
        )

        result = await db.execute(product_trend_query)

        for row in result.all():
            if period_type == "daily":
                label = row.period.strftime("%Y %b %-d")
            elif period_type == "weekly":
                label = f"Week of {row.period.strftime('%Y %b %-d')}"
            else:
                label = row.period.strftime("%Y %b")

            product_trend.append({
                
                "label": label,
                "total_products": row.total_products,
                "active_products": row.active_products,
                "inactive_products": row.inactive_products,
            })
            
    #--------------------------
    #products variant summary
    #--------------------------
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
            func.date(ProductVariant.created_at) >= start.date(),
            func.date(ProductVariant.created_at) < end.date(),
        )
    variant_result = await db.execute(variant_query) 
    variants = variant_result.one()
    
    #--------------------------
    #products variant trend
    #--------------------------
    variant_trend = []
    
    if period_type is not None:
        variant_period = get_period(ProductVariant.created_at, period_type)

        variant_trend_query = (
            select(
                variant_period.label("period"),
                func.count(ProductVariant.id).label("total_variants"),
                func.count(
                    case((ProductVariant.stock_quantity == 0, 1))
                ).label("out_of_stock_products"),
                func.count(
                    case((
                        and_(
                            ProductVariant.stock_quantity >= 1,
                            ProductVariant.stock_quantity <= 5,
                        ),
                        1,
                    ))
                ).label("low_stock_products"),
            )
        )

        if start and end:
            variant_trend_query = variant_trend_query.where(
                func.date(ProductVariant.created_at) >= start.date(),
                func.date(ProductVariant.created_at) < end.date(),
            )

        variant_trend_query = (
            variant_trend_query
            .group_by(variant_period)
            .order_by(variant_period)
        )

        result = await db.execute(variant_trend_query)

        for row in result.all():
            if period_type == "daily":
                label = row.period.strftime("%Y %b %-d")
            elif period_type == "weekly":
                label = f"Week of {row.period.strftime('%Y %b %-d')}"
            else:
                label = row.period.strftime("%Y %b")

            variant_trend.append({
                "label": label,
                "total_variants": row.total_variants,
                "out_of_stock_products": row.out_of_stock_products,
                "low_stock_products": row.low_stock_products,
            })
    
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
            func.date(User.created_at) >= start.date(),
            func.date(User.created_at) < end.date(),
        )
    user_result = await db.execute(user_query)
    users = user_result.one()
    
    #--------------------------
    #users trend
    #--------------------------
    user_trend = []
    if period_type is not None:
        user_period = get_period(User.created_at, period_type)
        
        user_trend_query = (
            select(
                user_period.label("period"),
                func.count(User.id).label("total_users"),
                func.count(case((User.is_active == True, 1))).label("active_users"),
                func.count(case((User.is_active == False, 1))).label("inactive_users"),
                func.count(case((User.is_guest == True, 1))).label("guest_users"),
            )
        )

        if start and end:
            user_trend_query = user_trend_query.where(
                func.date(User.created_at) >= start.date(),
                func.date(User.created_at) < end.date(),
            )

        user_trend_query = (
            user_trend_query
            .group_by(user_period)
            .order_by(user_period)
        )

        result = await db.execute(user_trend_query)

        for row in result.all():
            if period_type == "daily":
                label = row.period.strftime("%Y %b %-d")
            elif period_type == "weekly":
                label = f"Week of {row.period.strftime('%Y %b %-d')}"
            else:
                label = row.period.strftime("%Y %b")

            user_trend.append({
                "label": label,
                "total_users": row.total_users,
                "active_users": row.active_users,
                "inactive_users": row.inactive_users,
                "guest_users": row.guest_users,
            })
        
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
        },
        "sales_trend": sales_trend,
        "order_trend": order_trend,
        "product_trend": product_trend,
        "user_trend": user_trend
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
    report_service = ReportService()
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
            func.date(Order.created_at) >= start.date(),
            func.date(Order.created_at) < end.date(),
        )

    summary = (await db.execute(summary_query)).one()
    
    #--------------------------
    #orders
    #--------------------------
    
    #--------------------------
    #grouping filter response
    #--------------------------
    if filter_type in {
        DateFilter.TODAY,
        DateFilter.YESTERDAY
    }:
        # Group by hour
        period = func.date_trunc("hour", Order.created_at)
        period_type = "hourly"

    elif filter_type in {
        DateFilter.DAILY,
        DateFilter.THIS_WEEK,
        DateFilter.LAST_WEEK,
        DateFilter.LAST_7_DAYS,
        DateFilter.THIS_MONTH,
        DateFilter.LAST_MONTH,
        DateFilter.LAST_30_DAYS,
    }:
        # Group by day
        period = func.date(Order.created_at)
        period_type = "daily"
        
    elif filter_type in {
        DateFilter.WEEKLY,
    }:
        # Weekly
        period = func.date_trunc("week", Order.created_at)
        period_type = "weekly"

    elif filter_type in {
        DateFilter.THIS_YEAR,
        DateFilter.LAST_YEAR,
        DateFilter.LAST_3_MONTHS,
        DateFilter.LAST_6_MONTHS,
        DateFilter.MONTHLY,
    }:
        # Group by month
        period = func.date_trunc("month", Order.created_at)
        period_type = "monthly"

    else:
        # Custom
        if start and end and (end - start).days <= 31:
            period = func.date(Order.created_at)
            period_type = "daily"
        else:
            period = func.date_trunc("month", Order.created_at)
            period_type = "monthly"
    
    orders_query = (
        select(
            period.label("period"),
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
        orders_query = orders_query.where(
            func.date(Order.created_at) >= start.date(),
            func.date(Order.created_at) < end.date(),
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

    orders_query = (
        orders_query
        .group_by(period)
        .order_by(period)
        .offset(skip)
        .limit(limit)
    )

    order_result = await db.execute(orders_query)
    orders = order_result.all()
    
    order_response = []

    for row in orders:
        if period_type == "hourly":
            label = row.period.strftime("%I:%M %p")      # e.g. 09:00 AM
        elif period_type == "daily":
            label = row.period.strftime("%Y %b %-d")     # e.g. 2026 Jul 10
        elif period_type == "weekly":
            label = f"Week of {row.period.strftime('%Y %b %-d')}"
        else:
            label = row.period.strftime("%Y %b")         # e.g. 2026 Jul

        order_response.append({
            "label": label,
            "gross_sales": row.gross_sales,
            "net_sales": row.net_sales,
            "discount_amount": row.discount_amount,
            "tax_amount": row.tax_amount,
            "shipping_charge": row.delivery_charge,
            "total_sales": row.total_sales,
            "total_orders": row.total_orders,
        })
    
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
        "orders": order_response
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
            func.date(Order.created_at) >= start.date(),
            func.date(Order.created_at) < end.date(),
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
            "variant_name": row.variant_sku,
            "quantity_sold": row.quantity_sold,
            "gross_sales": row.gross_sales,
            "total_sales": row.total_sales,
        }
        for row in results
    ]
    
    
@report_router.get("/visit-report/")
async def visit_report(
    filter_type: DateFilter = Query(
        DateFilter.THIS_MONTH,
        description="Date range for the report."
    ),
    start_date: datetime | None = Query(
        None,
        description="Required when filter_type=CUSTOM."
    ),
    end_date: datetime | None = Query(
        None,
        description="Required when filter_type=CUSTOM."
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    report_service = ReportService()
    start, end = report_service.get_date_range(
        filter_type,
        start_date,
        end_date,
    )
    
    #--------------------------
    #grouping filter response
    #--------------------------
    if filter_type in {
        DateFilter.TODAY,
        DateFilter.YESTERDAY
    }:
        # Group by hour
        period = func.date_trunc("hour", Visit.created_at)
        period_type = "hourly"

    elif filter_type in {
        DateFilter.DAILY,
        DateFilter.THIS_WEEK,
        DateFilter.LAST_WEEK,
        DateFilter.LAST_7_DAYS,
        DateFilter.THIS_MONTH,
        DateFilter.LAST_MONTH,
        DateFilter.LAST_30_DAYS,
    }:
        # Group by day
        period = func.date(Visit.created_at)
        period_type = "daily"
        
    elif filter_type in {
        DateFilter.WEEKLY,
    }:
        # Weekly
        period = func.date_trunc("week", Visit.created_at)
        period_type = "weekly"

    elif filter_type in {
        DateFilter.THIS_YEAR,
        DateFilter.LAST_YEAR,
        DateFilter.LAST_3_MONTHS,
        DateFilter.LAST_6_MONTHS,
        DateFilter.MONTHLY,
    }:
        # Group by month
        period = func.date_trunc("month", Visit.created_at)
        period_type = "monthly"

    else:
        # Custom
        if start and end and (end - start).days <= 31:
            period = func.date(Visit.created_at)
            period_type = "daily"
        else:
            period = func.date_trunc("month", Visit.created_at)
            period_type = "monthly"
    
    #--------------------------
    #visit report
    #--------------------------
    
    filters = [
        func.date(Visit.created_at) >= start.date(),
        func.date(Visit.created_at) <= end.date(),
    ]

    total_visits = await db.scalar(
        select(func.count())
        .select_from(Visit)
        .where(*filters)
    )

    source_result = await db.execute(
        select(
            period.label("period"),
            Visit.source,
            func.count().label("count"),
        )
        .where(*filters)
        .group_by(
            period,
            Visit.source
        )
        .order_by(period)
    )

    medium_result = await db.execute(
        select(
            period.label("period"),
            Visit.medium,
            func.count().label("count"),
        )
        .where(*filters)
        .group_by(
            period,
            Visit.medium
        )
        .order_by(period)
    )
    
    campaign_result = await db.execute(
        select(
            period.label("period"),
            Visit.campaign,
            func.count().label("count"),
        )
        .where(
            *filters,
            Visit.campaign.is_not(None),
            func.trim(Visit.campaign) != "",
        )
        .group_by(
            period,
            Visit.campaign
        )
        .order_by(period)
    )
    
    def format_period(value, period_type):
        if period_type == "hourly":
            return value.strftime("%Y %b %d %H:00")

        if period_type == "daily":
            return value.strftime("%Y %b %d")

        if period_type in ["weekly", "monthly"]:
            return value.strftime("%Y %b")

        return value

    return {
        "total_visits": total_visits,
        "sources": [
            {
                "period": format_period(row.period, period_type),
                "source": row.source,
                "count": row.count,
            }
            for row in source_result
        ],

        "mediums": [
            {
                "period": format_period(row.period, period_type),
                "medium": row.medium,
                "count": row.count,
            }
            for row in medium_result
        ],

        "campaigns": [
            {
                "period": format_period(row.period, period_type),
                "campaign": row.campaign,
                "count": row.count,
            }
            for row in campaign_result
        ],
    }