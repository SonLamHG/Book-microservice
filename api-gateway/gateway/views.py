from django.shortcuts import render, redirect
from django.http import JsonResponse
import requests
import json

CUSTOMER_SERVICE_URL = "http://customer-service:8000"
STAFF_SERVICE_URL = "http://staff-service:8000"
MANAGER_SERVICE_URL = "http://manager-service:8000"
BOOK_SERVICE_URL = "http://book-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8000"
RECOMMENDER_SERVICE_URL = "http://recommender-ai-service:8000"
AUTH_SERVICE_URL = "http://auth-service:8000"


def home(request):
    return render(request, 'home.html')


# ---- Book Management (Staff) ----

def book_list(request):
    try:
        r = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=5)
        books = r.json()
    except Exception:
        books = []
    return render(request, 'books.html', {'books': books})


def book_create(request):
    if request.method == 'POST':
        data = {
            'title': request.POST.get('title'),
            'author': request.POST.get('author'),
            'price': request.POST.get('price'),
            'stock': request.POST.get('stock'),
            'isbn': request.POST.get('isbn', ''),
            'description': request.POST.get('description', ''),
        }
        try:
            requests.post(f"{BOOK_SERVICE_URL}/books/", json=data, timeout=5)
        except Exception:
            pass
        return redirect('book_list')
    return render(request, 'book_form.html')


# ---- Customer ----

def customer_list(request):
    try:
        r = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/", timeout=5)
        customers = r.json()
    except Exception:
        customers = []
    return render(request, 'customers.html', {'customers': customers})


def customer_register(request):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'phone': request.POST.get('phone', ''),
            'address': request.POST.get('address', ''),
        }
        try:
            requests.post(f"{CUSTOMER_SERVICE_URL}/customers/", json=data, timeout=5)
        except Exception:
            pass
        return redirect('customer_list')
    return render(request, 'customer_form.html')


# ---- Cart ----

def view_cart(request, customer_id):
    try:
        r = requests.get(f"{CART_SERVICE_URL}/carts/{customer_id}/", timeout=5)
        items = r.json() if r.status_code == 200 else []
    except Exception:
        items = []

    # Enrich cart items with book details
    for item in items if isinstance(items, list) else []:
        try:
            br = requests.get(f"{BOOK_SERVICE_URL}/books/{item['book_id']}/", timeout=5)
            if br.status_code == 200:
                item['book'] = br.json()
        except Exception:
            item['book'] = None

    return render(request, 'cart.html', {'items': items, 'customer_id': customer_id})


def add_to_cart(request):
    if request.method == 'POST':
        data = {
            'customer_id': int(request.POST.get('customer_id')),
            'book_id': int(request.POST.get('book_id')),
            'quantity': int(request.POST.get('quantity', 1)),
        }
        try:
            requests.post(f"{CART_SERVICE_URL}/cart-items/", json=data, timeout=5)
        except Exception:
            pass
        return redirect('view_cart', customer_id=data['customer_id'])
    return redirect('home')


# ---- Orders ----

def order_list(request, customer_id):
    try:
        r = requests.get(
            f"{ORDER_SERVICE_URL}/orders/",
            params={"customer_id": customer_id},
            timeout=5,
        )
        orders = r.json()
    except Exception:
        orders = []
    return render(request, 'orders.html', {'orders': orders, 'customer_id': customer_id})


def create_order(request):
    if request.method == 'POST':
        data = {
            'customer_id': int(request.POST.get('customer_id')),
            'shipping_address': request.POST.get('shipping_address', ''),
            'payment_method': request.POST.get('payment_method', 'COD'),
            'shipping_method': request.POST.get('shipping_method', 'STANDARD'),
        }
        try:
            requests.post(f"{ORDER_SERVICE_URL}/orders/", json=data, timeout=10)
        except Exception:
            pass
        return redirect('order_list', customer_id=data['customer_id'])
    return redirect('home')


# ---- Reviews ----

def book_reviews(request, book_id):
    try:
        r = requests.get(
            f"{COMMENT_RATE_SERVICE_URL}/reviews/book/{book_id}/", timeout=5
        )
        data = r.json() if r.status_code == 200 else {}
    except Exception:
        data = {}
    return render(request, 'reviews.html', {'review_data': data, 'book_id': book_id})


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
            requests.post(
                f"{COMMENT_RATE_SERVICE_URL}/reviews/", json=data, timeout=5
            )
        except Exception:
            pass
        return redirect('book_reviews', book_id=book_id)
    return redirect('home')


# ---- Recommendations ----

def recommendations(request, customer_id):
    try:
        r = requests.get(
            f"{RECOMMENDER_SERVICE_URL}/recommendations/{customer_id}/", timeout=5
        )
        data = r.json() if r.status_code == 200 else {}
    except Exception:
        data = {}
    return render(request, 'recommendations.html', {
        'data': data,
        'customer_id': customer_id,
    })


# ---- Staff ----

def staff_list(request):
    try:
        r = requests.get(f"{STAFF_SERVICE_URL}/staff/", timeout=5)
        staff = r.json()
    except Exception:
        staff = []
    return render(request, 'staff.html', {'staff': staff})


def staff_create(request):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'role': request.POST.get('role', ''),
        }
        try:
            requests.post(f"{STAFF_SERVICE_URL}/staff/", json=data, timeout=5)
        except Exception:
            pass
        return redirect('staff_list')
    return render(request, 'staff_form.html')


# ---- Manager ----

def manager_list(request):
    try:
        r = requests.get(f"{MANAGER_SERVICE_URL}/managers/", timeout=5)
        managers = r.json()
    except Exception:
        managers = []
    return render(request, 'managers.html', {'managers': managers})


def manager_create(request):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'department': request.POST.get('department', ''),
        }
        try:
            requests.post(f"{MANAGER_SERVICE_URL}/managers/", json=data, timeout=5)
        except Exception:
            pass
        return redirect('manager_list')
    return render(request, 'manager_form.html')


# ---- Catalog ----

def category_list(request):
    try:
        r = requests.get(f"{CATALOG_SERVICE_URL}/categories/", timeout=5)
        categories = r.json()
    except Exception:
        categories = []
    return render(request, 'categories.html', {'categories': categories})


def category_create(request):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'description': request.POST.get('description', ''),
        }
        try:
            requests.post(f"{CATALOG_SERVICE_URL}/categories/", json=data, timeout=5)
        except Exception:
            pass
        return redirect('category_list')
    return render(request, 'category_form.html')


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
    from django.http import JsonResponse
    return JsonResponse({'status': 'healthy', 'service': 'api-gateway'})
