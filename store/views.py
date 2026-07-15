from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Q, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import uuid
import json

from .models import (
    Product, Category, Cart, CartItem,
    Order, OrderItem, Review, Wishlist
)
from .forms import (
    RegisterForm, CheckoutForm, ReviewForm
)


# ─── HOME ───────────────────────────────────────────────────────────────────

def home(request):
    categories = Category.objects.all()[:8]
    featured_products = Product.objects.filter(is_featured=True, is_available=True)[:8]
    new_arrivals = Product.objects.filter(is_available=True).order_by('-created_at')[:8]
    best_sellers = Product.objects.filter(is_available=True).order_by('-review_count')[:8]

    context = {
        'categories': categories,
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'best_sellers': best_sellers,
    }
    return render(request, 'store/home.html', context)


# ─── PRODUCTS ───────────────────────────────────────────────────────────────

def product_list(request):
    products = Product.objects.filter(is_available=True)
    categories = Category.objects.all()
    category_slug = request.GET.get('category')
    sort = request.GET.get('sort', '')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    selected_category = None

    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)

    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'rating':
        products = products.order_by('-rating')
    elif sort == 'newest':
        products = products.order_by('-created_at')

    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'sort': sort,
    }
    return render(request, 'store/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_available=True)
    related_products = Product.objects.filter(
        category=product.category, is_available=True
    ).exclude(slug=slug)[:4]
    reviews = product.reviews.all()
    review_form = ReviewForm()
    in_wishlist = False

    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    if request.method == 'POST' and request.user.is_authenticated:
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            # ── FIX: use update_or_create to handle the unique(product, user) constraint ──
            Review.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={
                    'rating':  review_form.cleaned_data['rating'],
                    'title':   review_form.cleaned_data['title'],
                    'comment': review_form.cleaned_data['comment'],
                }
            )
            # Update product rating
            avg = product.reviews.aggregate(Avg('rating'))['rating__avg']
            product.rating = round(avg, 1)
            product.review_count = product.reviews.count()
            product.save()
            messages.success(request, 'Review submitted successfully!')
            return redirect('product_detail', slug=slug)

    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'review_form': review_form,
        'in_wishlist': in_wishlist,
    }
    return render(request, 'store/product_detail.html', context)


def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_available=True)
    return render(request, 'store/category_products.html', {
        'category': category,
        'products': products
    })


def search(request):
    query = request.GET.get('q', '')
    products = []
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(brand__icontains=query) |
            Q(category__name__icontains=query),
            is_available=True
        ).distinct()
    return render(request, 'store/search.html', {
        'products': products,
        'query': query
    })


# ─── CART ───────────────────────────────────────────────────────────────────

def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def cart(request):
    cart_obj = get_or_create_cart(request.user)
    items = cart_obj.items.select_related('product').all()
    return render(request, 'store/cart.html', {
        'cart': cart_obj,
        'items': items
    })


@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    cart_obj = get_or_create_cart(request.user)
    quantity = int(request.POST.get('quantity', 1))

    item, created = CartItem.objects.get_or_create(cart=cart_obj, product=product)
    if not created:
        item.quantity += quantity
    else:
        item.quantity = quantity
    item.save()

    messages.success(request, f'"{product.name}" added to cart!')
    return redirect(request.META.get('HTTP_REFERER', 'cart'))


@login_required
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    quantity = int(request.POST.get('quantity', 1))
    if quantity > 0:
        item.quantity = quantity
        item.save()
    else:
        item.delete()
    return redirect('cart')


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('cart')


# ─── CHECKOUT & ORDERS ──────────────────────────────────────────────────────

@login_required
def checkout(request):
    cart_obj = get_or_create_cart(request.user)
    items = cart_obj.items.select_related('product').all()

    if not items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    form = CheckoutForm(initial={
        'full_name': request.user.get_full_name(),
    })

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(
                user=request.user,
                order_id='UM' + str(uuid.uuid4().hex[:8].upper()),
                total_price=cart_obj.total_price,
                full_name=form.cleaned_data['full_name'],
                phone=form.cleaned_data['phone'],
                address_line1=form.cleaned_data['address_line1'],
                address_line2=form.cleaned_data.get('address_line2', ''),
                city=form.cleaned_data['city'],
                state=form.cleaned_data['state'],
                pincode=form.cleaned_data['pincode'],
                payment_method=form.cleaned_data['payment_method'],
            )
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    price=item.product.price,
                    quantity=item.quantity,
                )
                # Reduce stock
                item.product.stock -= item.quantity
                item.product.save()

            cart_obj.items.all().delete()
            messages.success(request, f'Order #{order.order_id} placed successfully! 🎉')
            return redirect('order_success', order_id=order.order_id)

    context = {
        'cart': cart_obj,
        'items': items,
        'form': form,
    }
    return render(request, 'store/checkout.html', context)


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'store/order_success.html', {'order': order})


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'store/order_list.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})


# ─── WISHLIST ───────────────────────────────────────────────────────────────

@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    obj, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        obj.delete()
        messages.info(request, f'Removed "{product.name}" from wishlist.')
    else:
        messages.success(request, f'Added "{product.name}" to wishlist! ❤️')
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def wishlist(request):
    items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'store/wishlist.html', {'items': items})


# ─── AUTH ───────────────────────────────────────────────────────────────────

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Uday Mart, {user.first_name}! 🎉')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'store/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}! 👋')
            return redirect(request.GET.get('next', 'home'))
    else:
        form = AuthenticationForm()
    return render(request, 'store/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user)[:5]
    return render(request, 'store/profile.html', {'orders': orders})