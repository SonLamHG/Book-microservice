from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils.translation import gettext as _
import requests
import json
import os
import threading

CUSTOMER_SERVICE_URL = "http://customer-service:8000"
STAFF_SERVICE_URL = "http://staff-service:8000"
MANAGER_SERVICE_URL = "http://manager-service:8000"
PRODUCT_SERVICE_URL = "http://product-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8000"
AUTH_SERVICE_URL = "http://auth-service:8000"
AI_SERVICE_URL = "http://ai-service:8006"


def _flash(request, message, flash_type='success'):
    request.session['flash_message'] = message
    request.session['flash_type'] = flash_type


def _fetch_json(url, timeout=5):
    try:
        r = requests.get(url, timeout=timeout)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def _post_json(url, payload, timeout=8, headers=None):
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        return r.json() if r.status_code in (200, 201) else {}
    except Exception:
        return {}


def _fetch_customers():
    return _fetch_json(f"{CUSTOMER_SERVICE_URL}/customers/")


def _fetch_products(params=None):
    try:
        r = requests.get(f"{PRODUCT_SERVICE_URL}/api/v1/products/", params=params, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("results", []) if isinstance(data, dict) else data
        return []
    except Exception:
        return []


def _paginate(items, request, per_page=10):
    if not isinstance(items, list):
        return items, 1, 1
    page = int(request.GET.get('page', 1))
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    return items[start:start + per_page], page, total_pages


# --- AI Tracking ---
def _track_event_async(event_data, jwt_token):
    def send_event():
        try:
            headers = {"Authorization": f"Bearer {jwt_token}"} if jwt_token else {}
            requests.post(f"{AI_SERVICE_URL}/ai/events", json=event_data, headers=headers, timeout=3)
        except Exception as e:
            print(f"Failed to track event: {e}")
    threading.Thread(target=send_event).start()


def _track_user_action(request, action, product_id=None, query=None):
    # Retrieve customer_id if logged in, else use user_id from token
    user_id = request.session.get('customer_id') or (request.session.get('user_data', {}).get('id'))
    if not user_id:
        return
    jwt_token = request.session.get('jwt_token')
    if not jwt_token:
        return
    event_data = {
        "user_id": user_id,
        "action": action
    }
    if product_id:
        event_data["product_id"] = product_id
    if query:
        event_data["query"] = query
    _track_event_async(event_data, jwt_token)


# ---- Home (Dashboard) ----

def home(request):
    products = _fetch_products()
    customers = _fetch_customers()
    orders = _fetch_json(f"{ORDER_SERVICE_URL}/orders/")
    staff = _fetch_json(f"{STAFF_SERVICE_URL}/staff/")
    categories = _fetch_json(f"{CATALOG_SERVICE_URL}/categories/")
    stats = {
        'products': len(products) if isinstance(products, list) else 0,
        'customers': len(customers) if isinstance(customers, list) else 0,
        'orders': len(orders) if isinstance(orders, list) else 0,
        'staff': len(staff) if isinstance(staff, list) else 0,
        'categories': len(categories) if isinstance(categories, list) else 0,
    }
    return render(request, 'home.html', {'stats': stats})


# ---- Book/Product Management ----

def product_list(request):
    categories = _fetch_json(f"{CATALOG_SERVICE_URL}/categories/")
    cat_map = {str(c['id']): c for c in categories} if isinstance(categories, list) else {}
    selected_category_id = request.GET.get('category', '').strip()
    search = request.GET.get('search', '').strip()

    params = {}
    if search:
        params['search'] = search
    if selected_category_id and selected_category_id in cat_map:
        params['category'] = cat_map[selected_category_id].get('slug')

    products = _fetch_products(params=params)

    # Tracking view event for search/browsing
    _track_user_action(request, action="view", query=search if search else None)

    books, page, total_pages = _paginate(products, request)
    
    customers = _fetch_customers()
    return render(request, 'products.html', {
        'products': books,
        'customers': customers,
        'categories': categories,
        'selected_category': selected_category_id,
        'search': search,
        'page': page,
        'total_pages': total_pages,
    })


def product_create(request):
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        data = {
            'name': request.POST.get('title'), # title maps to name
            'author': request.POST.get('author'),
            'price': request.POST.get('price'),
            'stock': request.POST.get('stock'),
            'isbn': request.POST.get('isbn', ''),
            'description': request.POST.get('description', ''),
            'category_id': int(category_id) if category_id else None,
        }
        try:
            r = requests.post(f"{PRODUCT_SERVICE_URL}/api/v1/products/", json=data, timeout=5)
            if r.status_code == 201:
                _flash(request, _('Book "{}" created successfully!').format(data["name"]))
            else:
                _flash(request, _('Failed to create book.'), 'danger')
        except Exception:
            _flash(request, _('Product service unavailable.'), 'danger')
        return redirect('product_list')
    categories = _fetch_json(f"{CATALOG_SERVICE_URL}/categories/")
    return render(request, 'product_form.html', {'categories': categories})


def product_edit(request, pk):
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        data = {
            'name': request.POST.get('title'),
            'author': request.POST.get('author'),
            'price': request.POST.get('price'),
            'stock': request.POST.get('stock'),
            'isbn': request.POST.get('isbn', ''),
            'description': request.POST.get('description', ''),
            'category_id': int(category_id) if category_id else None,
        }
        try:
            r = requests.put(f"{PRODUCT_SERVICE_URL}/api/v1/products/{pk}/", json=data, timeout=5)
            if r.status_code == 200:
                _flash(request, _('Book updated!'))
            else:
                _flash(request, _('Failed to update book.'), 'danger')
        except Exception:
            _flash(request, _('Product service unavailable.'), 'danger')
        return redirect('product_list')

    book_data = None
    try:
        r = requests.get(f"{PRODUCT_SERVICE_URL}/api/v1/products/{pk}/", timeout=5)
        if r.status_code == 200:
            book_data = r.json()
            # map name to title for the template
            book_data['title'] = book_data.get('name')
    except Exception:
        pass
    if not book_data:
        _flash(request, _('Book not found.'), 'danger')
        return redirect('product_list')
    categories = _fetch_json(f"{CATALOG_SERVICE_URL}/categories/")
    return render(request, 'product_form.html', {'edit': True, 'item': book_data, 'categories': categories})


def product_delete(request, pk):
    if request.method == 'POST':
        try:
            r = requests.delete(f"{PRODUCT_SERVICE_URL}/api/v1/products/{pk}/", timeout=5)
            if r.status_code == 204:
                _flash(request, _('Book deleted.'))
            else:
                _flash(request, _('Failed to delete book.'), 'danger')
        except Exception:
            _flash(request, _('Product service unavailable.'), 'danger')
    return redirect('product_list')


# ---- Customer ----

def customer_list(request):
    customers = _fetch_customers()
    customers, page, total_pages = _paginate(customers, request)
    return render(request, 'customers.html', {
        'customers': customers,
        'page': page,
        'total_pages': total_pages,
    })


def customer_register(request):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'phone': request.POST.get('phone', ''),
            'address': request.POST.get('address', ''),
        }
        try:
            r = requests.post(f"{CUSTOMER_SERVICE_URL}/customers/", json=data, timeout=5)
            if r.status_code == 201:
                _flash(request, _('Customer "{}" registered successfully!').format(data["name"]))
            else:
                _flash(request, _('Failed to register customer.'), 'danger')
        except Exception:
            _flash(request, _('Customer service unavailable.'), 'danger')
        return redirect('customer_list')
    return render(request, 'customer_form.html')


def customer_edit(request, pk):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'phone': request.POST.get('phone', ''),
            'address': request.POST.get('address', ''),
        }
        try:
            r = requests.put(f"{CUSTOMER_SERVICE_URL}/customers/{pk}/", json=data, timeout=5)
            if r.status_code == 200:
                _flash(request, _('Customer updated!'))
            else:
                _flash(request, _('Failed to update customer.'), 'danger')
        except Exception:
            _flash(request, _('Customer service unavailable.'), 'danger')
        return redirect('customer_list')

    item = None
    try:
        r = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/{pk}/", timeout=5)
        if r.status_code == 200:
            item = r.json()
    except Exception:
        pass
    if not item:
        _flash(request, _('Customer not found.'), 'danger')
        return redirect('customer_list')
    return render(request, 'customer_form.html', {'edit': True, 'item': item})


def customer_delete(request, pk):
    if request.method == 'POST':
        try:
            r = requests.delete(f"{CUSTOMER_SERVICE_URL}/customers/{pk}/", timeout=5)
            if r.status_code == 204:
                _flash(request, _('Customer deleted.'))
            else:
                _flash(request, _('Failed to delete customer.'), 'danger')
        except Exception:
            _flash(request, _('Customer service unavailable.'), 'danger')
    return redirect('customer_list')


# ---- Cart ----

def view_cart(request, customer_id):
    try:
        r = requests.get(f"{CART_SERVICE_URL}/carts/{customer_id}/", timeout=5)
        items = r.json() if r.status_code == 200 else []
    except Exception:
        items = []

    cart_total = 0
    for item in items if isinstance(items, list) else []:
        try:
            # item.book_id acts as product_id in new schema
            br = requests.get(f"{PRODUCT_SERVICE_URL}/api/v1/products/{item['book_id']}/", timeout=5)
            if br.status_code == 200:
                book_data = br.json()
                book_data['title'] = book_data.get('name')
                item['product'] = book_data
                price = float(item['product'].get('price', 0))
                qty = item.get('quantity', 0)
                item['subtotal'] = price * qty
                cart_total += item['subtotal']
            else:
                item['product'] = None
                item['subtotal'] = 0
        except Exception:
            item['product'] = None
            item['subtotal'] = 0

    customer_name = ''
    try:
        cr = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/{customer_id}/", timeout=5)
        if cr.status_code == 200:
            customer_name = cr.json().get('name', '')
    except Exception:
        pass

    products = _fetch_products()

    return render(request, 'cart.html', {
        'items': items,
        'customer_id': customer_id,
        'customer_name': customer_name,
        'cart_total': f"{cart_total:.2f}",
        'products': products,
    })


def add_to_cart(request):
    if request.method == 'POST':
        customer_id = int(request.POST.get('customer_id'))
        book_id = int(request.POST.get('book_id'))
        quantity = int(request.POST.get('quantity', 1))
        data = {
            'customer_id': customer_id,
            'book_id': book_id,
            'quantity': quantity,
        }
        try:
            r = requests.post(f"{CART_SERVICE_URL}/cart-items/", json=data, timeout=5)
            if r.status_code == 201:
                _flash(request, 'Item added to cart!')
                _track_user_action(request, action="add_to_cart", product_id=book_id)
            else:
                error = r.json().get('error', 'Failed to add item')
                _flash(request, error, 'danger')
        except Exception:
            _flash(request, 'Cart service unavailable.', 'danger')

        redirect_to = request.POST.get('redirect_to', '')
        if redirect_to == 'products':
            return redirect('product_list')
        return redirect('view_cart', customer_id=customer_id)
    return redirect('home')


def remove_cart_item(request, item_id):
    if request.method == 'POST':
        customer_id = int(request.POST.get('customer_id'))
        book_id = request.POST.get('book_id')
        try:
            r = requests.delete(f"{CART_SERVICE_URL}/cart-items/{item_id}/", timeout=5)
            if r.status_code == 204:
                _flash(request, 'Item removed from cart.')
                if book_id:
                    _track_user_action(request, action="remove_from_cart", product_id=int(book_id))
            else:
                _flash(request, 'Failed to remove item.', 'danger')
        except Exception:
            _flash(request, 'Cart service unavailable.', 'danger')
        return redirect('view_cart', customer_id=customer_id)
    return redirect('home')


def update_cart_item(request, item_id):
    if request.method == 'POST':
        customer_id = int(request.POST.get('customer_id'))
        quantity = int(request.POST.get('quantity', 1))
        try:
            r = requests.put(
                f"{CART_SERVICE_URL}/cart-items/{item_id}/",
                json={'quantity': quantity},
                timeout=5,
            )
            if r.status_code == 200:
                _flash(request, 'Quantity updated.')
            else:
                _flash(request, 'Failed to update quantity.', 'danger')
        except Exception:
            _flash(request, 'Cart service unavailable.', 'danger')
        return redirect('view_cart', customer_id=customer_id)
    return redirect('home')


# ---- Orders ----

def order_list(request, customer_id):
    try:
        r = requests.get(
            f"{ORDER_SERVICE_URL}/orders/",
            params={"customer_id": customer_id},
            timeout=5,
        )
        orders = r.json() if isinstance(r.json(), list) else []
    except Exception:
        orders = []

    # Enrich order items with book details
    for order in orders:
        for item in order.get('items', []):
            try:
                br = requests.get(f"{PRODUCT_SERVICE_URL}/api/v1/products/{item['book_id']}/", timeout=5)
                if br.status_code == 200:
                    book_data = br.json()
                    book_data['title'] = book_data.get('name')
                    item['product'] = book_data
            except Exception:
                item['product'] = None

    customer_name = ''
    try:
        cr = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/{customer_id}/", timeout=5)
        if cr.status_code == 200:
            customer_name = cr.json().get('name', '')
    except Exception:
        pass

    orders, page, total_pages = _paginate(orders, request, per_page=5)

    return render(request, 'orders.html', {
        'orders': orders,
        'customer_id': customer_id,
        'customer_name': customer_name,
        'page': page,
        'total_pages': total_pages,
    })


def create_order(request):
    if request.method == 'POST':
        customer_id = int(request.POST.get('customer_id'))
        data = {
            'customer_id': customer_id,
            'shipping_address': request.POST.get('shipping_address', ''),
            'payment_method': request.POST.get('payment_method', 'COD'),
            'shipping_method': request.POST.get('shipping_method', 'STANDARD'),
        }
        try:
            r = requests.post(f"{ORDER_SERVICE_URL}/orders/", json=data, timeout=10)
            if r.status_code == 201:
                _flash(request, 'Order placed successfully!')
                _track_user_action(request, action="purchase")
            else:
                error = r.json().get('error', 'Failed to place order')
                _flash(request, error, 'danger')
        except Exception:
            _flash(request, 'Order service unavailable.', 'danger')
        return redirect('order_list', customer_id=customer_id)
    return redirect('home')


# ---- Reviews ----

def product_reviews(request, product_id):
    _track_user_action(request, action="view", product_id=product_id)
    try:
        r = requests.get(
            f"{COMMENT_RATE_SERVICE_URL}/reviews/book/{product_id}/", timeout=5
        )
        data = r.json() if r.status_code == 200 else {}
    except Exception:
        data = {}

    book_data = None
    try:
        br = requests.get(f"{PRODUCT_SERVICE_URL}/api/v1/products/{product_id}/", timeout=5)
        if br.status_code == 200:
            book_data = br.json()
            book_data['title'] = book_data.get('name')
    except Exception:
        pass

    default_customer_id = request.GET.get('customer_id', '')

    return render(request, 'reviews.html', {
        'review_data': data,
        'book_id': product_id,
        'book_data': book_data,
        'default_customer_id': default_customer_id,
    })


def add_review(request):
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        data = {
            'book_id': int(book_id),
            'customer_id': int(request.POST.get('customer_id')),
            'rating': int(request.POST.get('rating')),
            'comment': request.POST.get('comment', ''),
        }
        try:
            r = requests.post(
                f"{COMMENT_RATE_SERVICE_URL}/reviews/", json=data, timeout=5
            )
            if r.status_code == 201:
                _flash(request, 'Review submitted!')
            else:
                _flash(request, 'Failed to submit review.', 'danger')
        except Exception:
            _flash(request, 'Review service unavailable.', 'danger')
        return redirect('product_reviews', product_id=book_id)
    return redirect('home')


# ---- AI Recommendations & Chatbot ----

def recommendations(request, customer_id):
    jwt_token = request.session.get('jwt_token')
    headers = {"Authorization": f"Bearer {jwt_token}"} if jwt_token else {}
    
    # Get recommendations from ai-service
    try:
        r = requests.get(f"{AI_SERVICE_URL}/ai/recommend", params={"user_id": customer_id, "limit": 6}, headers=headers, timeout=5)
        if r.status_code == 200:
            rec_data = r.json()
            items = rec_data.get("items", [])
            for item in items:
                # Format to match template expectations
                item['title'] = item.get('product', {}).get('name', 'Unknown')
                item['author'] = ""
                item['price'] = item.get('product', {}).get('price', '')
                item['category_name'] = item.get('product', {}).get('category', '')
                item['why_recommended'] = item.get('reason', '')
                item['book_id'] = item.get('product_id')
            data = {"recommended_books": items}
        else:
            data = {}
    except Exception:
        data = {}
        
    return render(request, 'recommendations.html', {
        'data': data,
        'customer_id': customer_id,
        'user_prompt': "What kind of book are you looking for?",
    })


def recommendations_ask(request, customer_id):
    if request.method == 'POST':
        user_prompt = request.POST.get('user_prompt', '').strip()
        jwt_token = request.session.get('jwt_token')
        headers = {"Authorization": f"Bearer {jwt_token}"} if jwt_token else {}
        
        payload = {
            "message": user_prompt,
            "user_id": customer_id
        }
        
        try:
            r = requests.post(f"{AI_SERVICE_URL}/ai/chatbot", json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                chat_data = r.json()
                items = chat_data.get("recommended_products", [])
                for item in items:
                    item['title'] = item.get('product', {}).get('name', 'Unknown')
                    item['author'] = ""
                    item['price'] = item.get('product', {}).get('price', '')
                    item['category_name'] = item.get('product', {}).get('category', '')
                    item['why_recommended'] = item.get('reason', '')
                    item['book_id'] = item.get('product_id')
                
                data = {
                    "answer_text": chat_data.get("answer"),
                    "recommended_books": items,
                    "follow_up_questions": chat_data.get("follow_up_questions", [])
                }
            else:
                data = {"answer_text": "Xin lỗi, chatbot đang gặp sự cố. Vui lòng thử lại sau."}
        except Exception:
            data = {"answer_text": "Không thể kết nối đến hệ thống AI."}
            
        return render(request, 'recommendations.html', {
            'data': data,
            'customer_id': customer_id,
            'user_prompt': user_prompt,
        })
    return redirect('recommendations', customer_id=customer_id)


# ---- Staff ----

def staff_list(request):
    staff = _fetch_json(f"{STAFF_SERVICE_URL}/staff/")
    return render(request, 'staff.html', {'staff': staff})


def staff_create(request):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'role': request.POST.get('role', ''),
        }
        try:
            r = requests.post(f"{STAFF_SERVICE_URL}/staff/", json=data, timeout=5)
            if r.status_code == 201:
                _flash(request, f'Staff "{data["name"]}" created!')
            else:
                _flash(request, 'Failed to create staff.', 'danger')
        except Exception:
            _flash(request, 'Staff service unavailable.', 'danger')
        return redirect('staff_list')
    return render(request, 'staff_form.html')


def staff_edit(request, pk):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'role': request.POST.get('role', ''),
        }
        try:
            r = requests.put(f"{STAFF_SERVICE_URL}/staff/{pk}/", json=data, timeout=5)
            if r.status_code == 200:
                _flash(request, 'Staff updated!')
            else:
                _flash(request, 'Failed to update staff.', 'danger')
        except Exception:
            _flash(request, 'Staff service unavailable.', 'danger')
        return redirect('staff_list')

    staff_data = None
    try:
        r = requests.get(f"{STAFF_SERVICE_URL}/staff/{pk}/", timeout=5)
        if r.status_code == 200:
            staff_data = r.json()
    except Exception:
        pass
    if not staff_data:
        _flash(request, 'Staff not found.', 'danger')
        return redirect('staff_list')
    return render(request, 'staff_form.html', {'edit': True, 'item': staff_data})


def staff_delete(request, pk):
    if request.method == 'POST':
        try:
            r = requests.delete(f"{STAFF_SERVICE_URL}/staff/{pk}/", timeout=5)
            if r.status_code == 204:
                _flash(request, 'Staff deleted.')
            else:
                _flash(request, 'Failed to delete staff.', 'danger')
        except Exception:
            _flash(request, 'Staff service unavailable.', 'danger')
    return redirect('staff_list')


# ---- Manager ----

def manager_list(request):
    managers = _fetch_json(f"{MANAGER_SERVICE_URL}/managers/")
    return render(request, 'managers.html', {'managers': managers})


def manager_create(request):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'department': request.POST.get('department', ''),
        }
        try:
            r = requests.post(f"{MANAGER_SERVICE_URL}/managers/", json=data, timeout=5)
            if r.status_code == 201:
                _flash(request, f'Manager "{data["name"]}" created!')
            else:
                _flash(request, 'Failed to create manager.', 'danger')
        except Exception:
            _flash(request, 'Manager service unavailable.', 'danger')
        return redirect('manager_list')
    return render(request, 'manager_form.html')


def manager_edit(request, pk):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'department': request.POST.get('department', ''),
        }
        try:
            r = requests.put(f"{MANAGER_SERVICE_URL}/managers/{pk}/", json=data, timeout=5)
            if r.status_code == 200:
                _flash(request, 'Manager updated!')
            else:
                _flash(request, 'Failed to update manager.', 'danger')
        except Exception:
            _flash(request, 'Manager service unavailable.', 'danger')
        return redirect('manager_list')

    item = None
    try:
        r = requests.get(f"{MANAGER_SERVICE_URL}/managers/{pk}/", timeout=5)
        if r.status_code == 200:
            item = r.json()
    except Exception:
        pass
    if not item:
        _flash(request, 'Manager not found.', 'danger')
        return redirect('manager_list')
    return render(request, 'manager_form.html', {'edit': True, 'item': item})


def manager_delete(request, pk):
    if request.method == 'POST':
        try:
            r = requests.delete(f"{MANAGER_SERVICE_URL}/managers/{pk}/", timeout=5)
            if r.status_code == 204:
                _flash(request, 'Manager deleted.')
            else:
                _flash(request, 'Failed to delete manager.', 'danger')
        except Exception:
            _flash(request, 'Manager service unavailable.', 'danger')
    return redirect('manager_list')


# ---- Catalog ----

def category_list(request):
    categories = _fetch_json(f"{CATALOG_SERVICE_URL}/categories/")
    return render(request, 'categories.html', {'categories': categories})


def category_create(request):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'description': request.POST.get('description', ''),
        }
        try:
            r = requests.post(f"{CATALOG_SERVICE_URL}/categories/", json=data, timeout=5)
            if r.status_code == 201:
                _flash(request, f'Category "{data["name"]}" created!')
            else:
                _flash(request, 'Failed to create category.', 'danger')
        except Exception:
            _flash(request, 'Catalog service unavailable.', 'danger')
        return redirect('category_list')
    return render(request, 'category_form.html')


def category_edit(request, pk):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'description': request.POST.get('description', ''),
        }
        try:
            r = requests.put(f"{CATALOG_SERVICE_URL}/categories/{pk}/", json=data, timeout=5)
            if r.status_code == 200:
                _flash(request, 'Category updated!')
            else:
                _flash(request, 'Failed to update category.', 'danger')
        except Exception:
            _flash(request, 'Catalog service unavailable.', 'danger')
        return redirect('category_list')

    item = None
    try:
        r = requests.get(f"{CATALOG_SERVICE_URL}/categories/{pk}/", timeout=5)
        if r.status_code == 200:
            item = r.json()
    except Exception:
        pass
    if not item:
        _flash(request, 'Category not found.', 'danger')
        return redirect('category_list')
    return render(request, 'category_form.html', {'edit': True, 'item': item})


def category_delete(request, pk):
    if request.method == 'POST':
        # Legacy: used to check books first
        try:
            r = requests.delete(f"{CATALOG_SERVICE_URL}/categories/{pk}/", timeout=5)
            if r.status_code == 204:
                _flash(request, 'Category deleted.')
            else:
                _flash(request, 'Failed to delete category.', 'danger')
        except Exception:
            _flash(request, 'Catalog service unavailable.', 'danger')
    return redirect('category_list')


# ---- Auth ----

def auth_login(request):
    if request.method == 'POST':
        data = {
            'username': request.POST.get('username'),
            'password': request.POST.get('password'),
        }
        try:
            r = requests.post(f"{AUTH_SERVICE_URL}/auth/login/", json=data, timeout=5)
            if r.status_code == 200:
                result = r.json()
                request.session['jwt_token'] = result['token']
                request.session['user_data'] = result['user']

                # Look up linked profile based on role
                if result['user'].get('role') == 'CUSTOMER':
                    try:
                        customers = requests.get(
                            f"{CUSTOMER_SERVICE_URL}/customers/", timeout=5
                        ).json()
                        for c in customers:
                            if c.get('auth_user_id') == result['user']['id'] or c.get('email') == result['user'].get('email'):
                                request.session['customer_id'] = c['id']
                                break
                    except Exception:
                        pass
                elif result['user'].get('role') == 'STAFF':
                    try:
                        staff_list = requests.get(
                            f"{STAFF_SERVICE_URL}/staff/", timeout=5
                        ).json()
                        for s in staff_list:
                            if s.get('auth_user_id') == result['user']['id'] or s.get('email') == result['user'].get('email'):
                                request.session['staff_id'] = s['id']
                                break
                    except Exception:
                        pass
                elif result['user'].get('role') == 'MANAGER':
                    try:
                        manager_list = requests.get(
                            f"{MANAGER_SERVICE_URL}/managers/", timeout=5
                        ).json()
                        for m in manager_list:
                            if m.get('auth_user_id') == result['user']['id'] or m.get('email') == result['user'].get('email'):
                                request.session['manager_id'] = m['id']
                                break
                    except Exception:
                        pass

                _flash(request, f'Welcome back, {result["user"]["username"]}!')
                return redirect('home')
            else:
                return render(request, 'login.html', {'error': 'Invalid credentials'})
        except Exception:
            return render(request, 'login.html', {'error': 'Auth service unavailable'})
    return render(request, 'login.html')


def auth_register(request):
    if request.method == 'POST':
        data = {
            'username': request.POST.get('username'),
            'email': request.POST.get('email'),
            'password': request.POST.get('password'),
            'role': request.POST.get('role', 'CUSTOMER'),
        }
        try:
            r = requests.post(f"{AUTH_SERVICE_URL}/auth/register/", json=data, timeout=5)
            if r.status_code == 201:
                result = r.json()
                request.session['jwt_token'] = result['token']
                request.session['user_data'] = result['user']

                # Auto-create profile based on role
                if data['role'] == 'CUSTOMER':
                    try:
                        cr = requests.post(
                            f"{CUSTOMER_SERVICE_URL}/customers/",
                            json={
                                'name': data['username'],
                                'email': data['email'],
                                'auth_user_id': result['user']['id'],
                            },
                            timeout=5,
                        )
                        if cr.status_code == 201:
                            request.session['customer_id'] = cr.json()['id']
                    except Exception:
                        pass
                elif data['role'] == 'STAFF':
                    try:
                        sr = requests.post(
                            f"{STAFF_SERVICE_URL}/staff/",
                            json={
                                'name': data['username'],
                                'email': data['email'],
                                'auth_user_id': result['user']['id'],
                            },
                            timeout=5,
                        )
                        if sr.status_code == 201:
                            request.session['staff_id'] = sr.json()['id']
                    except Exception:
                        pass
                elif data['role'] == 'MANAGER':
                    try:
                        mr = requests.post(
                            f"{MANAGER_SERVICE_URL}/managers/",
                            json={
                                'name': data['username'],
                                'email': data['email'],
                                'auth_user_id': result['user']['id'],
                            },
                            timeout=5,
                        )
                        if mr.status_code == 201:
                            request.session['manager_id'] = mr.json()['id']
                    except Exception:
                        pass

                _flash(request, f'Welcome, {data["username"]}! Account created.')
                return redirect('home')
            else:
                error = r.json().get('error', 'Registration failed')
                return render(request, 'register.html', {'error': error})
        except Exception:
            return render(request, 'register.html', {'error': 'Auth service unavailable'})
    return render(request, 'register.html')


def auth_logout(request):
    request.session.flush()
    return redirect('auth_login')


def health_check(request):
    return JsonResponse({'status': 'healthy', 'service': 'api-gateway'})
