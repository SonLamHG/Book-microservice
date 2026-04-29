"""
Rule-based customer behavior analyzer.
Fetches data from order-service, comment-rate-service, product-service
and computes RFM segmentation + preferences.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from collections import Counter

import requests
from django.conf import settings
from django.utils import timezone

from .models import CustomerBehaviorSummary

logger = logging.getLogger(__name__)

ORDER_SERVICE_URL = getattr(settings, 'ORDER_SERVICE_URL', 'http://order-service:8000')
COMMENT_RATE_SERVICE_URL = getattr(settings, 'COMMENT_RATE_SERVICE_URL', 'http://comment-rate-service:8000')
PRODUCT_SERVICE_URL = getattr(settings, 'PRODUCT_SERVICE_URL', 'http://product-service:8000')
CATALOG_SERVICE_URL = getattr(settings, 'CATALOG_SERVICE_URL', 'http://catalog-service:8000')

REQUEST_TIMEOUT = 5


def _fetch_json(url, params=None):
    """Fetch JSON from a service URL, return list/dict or empty."""
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except requests.exceptions.RequestException as e:
        logger.warning("Failed to fetch %s: %s", url, e)
    return None


def _determine_segment(total_orders, last_order_date):
    """Determine customer segment based on RFM heuristics."""
    if total_orders == 0:
        return 'new'

    if last_order_date is None:
        return 'new'

    now = timezone.now()
    if timezone.is_naive(last_order_date):
        last_order_date = timezone.make_aware(last_order_date)

    days_since_last = (now - last_order_date).days

    if total_orders >= 5:
        return 'loyal'
    if days_since_last <= 30:
        return 'active'
    if days_since_last <= 60:
        return 'active'
    if days_since_last <= 120:
        return 'at_risk'
    return 'churned'


def analyze_customer_behavior(customer_id):
    """
    Analyze customer behavior by aggregating data from other services.
    Stores/updates results in CustomerBehaviorSummary.
    """
    summary, _ = CustomerBehaviorSummary.objects.get_or_create(customer_id=customer_id)

    # ── 1. Fetch orders ──
    orders_data = _fetch_json(f"{ORDER_SERVICE_URL}/orders/", params={'customer_id': customer_id})
    if orders_data is None:
        orders_data = []

    total_orders = len(orders_data)
    total_spent = Decimal('0')
    last_order_date = None
    order_dates = []
    book_ids_purchased = []

    for order in orders_data:
        amount = Decimal(str(order.get('total_amount', 0)))
        total_spent += amount

        created_at_str = order.get('created_at')
        if created_at_str:
            try:
                order_date = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                order_dates.append(order_date)
                if last_order_date is None or order_date > last_order_date:
                    last_order_date = order_date
            except (ValueError, TypeError):
                pass

        # Collect book_ids from order items
        for item in order.get('items', []):
            book_id = item.get('book_id')
            if book_id:
                book_ids_purchased.append(book_id)

    avg_order_value = total_spent / total_orders if total_orders > 0 else Decimal('0')

    # Purchase frequency
    purchase_frequency_days = None
    if len(order_dates) >= 2:
        order_dates.sort()
        diffs = [(order_dates[i+1] - order_dates[i]).days for i in range(len(order_dates)-1)]
        purchase_frequency_days = sum(diffs) / len(diffs) if diffs else None

    # ── 2. Fetch book details to extract categories/authors ──
    category_counter = Counter()
    author_counter = Counter()

    book_details_cache = {}
    for book_id in set(book_ids_purchased):
        book_data = _fetch_json(f"{PRODUCT_SERVICE_URL}/books/{book_id}/")
        if book_data:
            book_details_cache[book_id] = book_data
            author = book_data.get('author')
            cat_id = book_data.get('category_id')
            if author:
                author_counter[author] += 1
            if cat_id:
                category_counter[cat_id] += 1

    # Resolve category names
    favorite_categories = []
    for cat_id, count in category_counter.most_common(5):
        cat_data = _fetch_json(f"{CATALOG_SERVICE_URL}/categories/{cat_id}/")
        cat_name = cat_data.get('name', f'Category {cat_id}') if cat_data else f'Category {cat_id}'
        favorite_categories.append({'category_id': cat_id, 'name': cat_name, 'count': count})

    favorite_authors = [
        {'author': author, 'count': count}
        for author, count in author_counter.most_common(5)
    ]

    # ── 3. Fetch reviews/ratings ──
    avg_rating_given = None
    reviews_data = _fetch_json(f"{COMMENT_RATE_SERVICE_URL}/reviews/", params={'customer_id': customer_id})
    if reviews_data and isinstance(reviews_data, list):
        ratings = [r.get('rating') for r in reviews_data if r.get('rating')]
        if ratings:
            avg_rating_given = Decimal(str(sum(ratings) / len(ratings))).quantize(Decimal('0.01'))

    # ── 4. Determine segment ──
    segment = _determine_segment(total_orders, last_order_date)

    # ── 5. Update summary ──
    summary.total_orders = total_orders
    summary.total_spent = total_spent
    summary.avg_order_value = avg_order_value
    summary.favorite_categories = favorite_categories
    summary.favorite_authors = favorite_authors
    summary.avg_rating_given = avg_rating_given
    summary.purchase_frequency_days = purchase_frequency_days
    summary.last_order_date = last_order_date
    summary.segment = segment
    summary.save()

    logger.info(
        "Behavior analysis for customer #%s: segment=%s, orders=%d, spent=%s",
        customer_id, segment, total_orders, total_spent,
    )

    return summary
