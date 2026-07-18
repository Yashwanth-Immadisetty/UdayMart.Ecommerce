from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Avg
from django.http import JsonResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from decimal import Decimal
import uuid
import json

from .models import (
    Product, Category, Cart, CartItem,
    Order, OrderItem, Review, Wishlist, CustomerProfile
)
from .forms import (
    RegisterForm, CheckoutForm, ReviewForm, OTPLoginStartForm,
    OTPVerificationForm
)
from .services import (
    OTPConfigurationError, OTPDeliveryError, OTPRateLimitError,
    PhoneNumberError, normalize_phone, otp_auth_enabled,
    otp_delivery_is_configured, otp_configuration_message,
    request_dual_otp, send_order_confirmation, verify_email_otp,
    verify_sms_otp,
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
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('cat', '').strip()
    products = Product.objects.filter(is_available=True)

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(brand__icontains=query) |
            Q(category__name__icontains=query)
        )
    if category_slug:
        products = products.filter(category__slug=category_slug)

    products = products.distinct()
    return render(request, 'store/search.html', {
        'products': products,
        'query': query
    })


def search_suggestions(request):
    """Return a compact list for the header's live product search."""
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('cat', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    products = Product.objects.filter(is_available=True).filter(
        Q(name__icontains=query) |
        Q(brand__icontains=query) |
        Q(category__name__icontains=query)
    )
    if category_slug:
        products = products.filter(category__slug=category_slug)

    results = []
    for product in products.select_related('category').distinct()[:6]:
        results.append({
            'name': product.name,
            'brand': product.brand or product.category.name,
            'url': product.get_absolute_url(),
            'image': product.image.url if product.image else '',
        })
    return JsonResponse({'results': results})


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

    initial_data = {'full_name': request.user.get_full_name()}
    try:
        initial_data['phone'] = request.user.customer_profile.phone
    except CustomerProfile.DoesNotExist:
        pass
    form = CheckoutForm(initial=initial_data)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Calculate the same grand total shown in the checkout page.  The
            # previous version saved only the subtotal when a delivery charge
            # applied, which made confirmations show the wrong amount.
            subtotal = sum((item.subtotal for item in items), Decimal('0.00'))
            delivery_fee = Decimal('0.00') if subtotal >= Decimal('499.00') else Decimal('40.00')

            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    order_id='UM' + str(uuid.uuid4().hex[:8].upper()),
                    total_price=subtotal + delivery_fee,
                    delivery_fee=delivery_fee,
                    full_name=form.cleaned_data['full_name'],
                    phone=form.cleaned_data['phone'],
                    address_line1=form.cleaned_data['address_line1'],
                    address_line2=form.cleaned_data.get('address_line2', ''),
                    city=form.cleaned_data['city'],
                    state=form.cleaned_data['state'],
                    pincode=form.cleaned_data['pincode'],
                    location_latitude=form.cleaned_data.get('location_latitude'),
                    location_longitude=form.cleaned_data.get('location_longitude'),
                    location_accuracy=form.cleaned_data.get('location_accuracy'),
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
                # Notifications must never undo a completed order.  Their
                # result is recorded separately in the admin panel.
                transaction.on_commit(lambda order_pk=order.pk: send_order_confirmation(order_pk))

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


def _safe_next_url(request, candidate):
    """Only redirect to a path from this website after authentication."""

    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return None


def _pending_otp_user(request, purpose):
    user_id = request.session.get(f'otp_{purpose}_user_id')
    if not user_id:
        return None
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        request.session.pop(f'otp_{purpose}_user_id', None)
        return None


def _start_otp_flow(request, user, purpose, next_url=None):
    """Send both codes and retain only the pending user id in the session."""

    if not otp_delivery_is_configured():
        messages.error(request, 'Secure email and SMS verification is not configured yet. Please contact Uday Mart.')
        return False
    request.session[f'otp_{purpose}_user_id'] = user.pk
    if next_url:
        request.session[f'otp_{purpose}_next'] = next_url
    try:
        request_dual_otp(user, purpose)
    except OTPRateLimitError as error:
        messages.warning(request, str(error))
        return False
    except (OTPConfigurationError, OTPDeliveryError):
        messages.error(request, 'We could not send both verification codes. Please try again shortly.')
        return False
    return True


def _finish_otp_verification(request, user, purpose, form):
    """Verify each channel independently and return whether both succeeded."""

    try:
        profile = user.customer_profile
    except CustomerProfile.DoesNotExist:
        messages.error(request, 'This account does not have a registered mobile number.')
        return False

    email_valid = profile.email_is_verified
    phone_valid = profile.phone_is_verified
    errors = []

    if not email_valid:
        email_code = form.cleaned_data['email_code']
        if not email_code:
            errors.append('Enter the code sent to your email address.')
        else:
            email_valid, email_error = verify_email_otp(user, purpose, email_code)
            if not email_valid:
                errors.append(email_error)

    if not phone_valid:
        phone_code = form.cleaned_data['phone_code']
        if not phone_code:
            errors.append('Enter the code sent by SMS.')
        else:
            try:
                phone_valid = verify_sms_otp(profile.phone, phone_code)
            except (OTPConfigurationError, OTPDeliveryError):
                errors.append('We could not validate the SMS code. Please try again shortly.')
            else:
                if not phone_valid:
                    errors.append('The SMS code is incorrect or has expired.')

    if not email_valid or not phone_valid:
        for error in errors:
            messages.error(request, error)
        return False

    now = timezone.now()
    changed_fields = []
    if not profile.email_verified_at:
        profile.email_verified_at = now
        changed_fields.append('email_verified_at')
    if not profile.phone_verified_at:
        profile.phone_verified_at = now
        changed_fields.append('phone_verified_at')
    if profile.whatsapp_opt_in and not profile.whatsapp_opt_in_at:
        profile.whatsapp_opt_in_at = now
        changed_fields.append('whatsapp_opt_in_at')
    if changed_fields:
        profile.save(update_fields=changed_fields)
    return True


def _render_otp_verification(request, user, form, purpose):
    return render(request, 'store/verify_otp.html', {
        'form': form,
        'purpose': purpose,
        'email': user.email,
        'phone': user.customer_profile.phone,
        'email_verified': user.customer_profile.email_is_verified,
        'phone_verified': user.customer_profile.phone_is_verified,
    })


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # OTP can be kept off until the shop owner has entered the SMTP
            # and Twilio keys in Render.  That preserves the current website
            # while the external services are being set up.
            if not otp_auth_enabled():
                with transaction.atomic():
                    user = form.save()
                    CustomerProfile.objects.create(
                        user=user,
                        phone=form.cleaned_data['phone'],
                        whatsapp_opt_in=form.cleaned_data['whatsapp_opt_in'],
                    )
                login(request, user)
                messages.success(request, f'Welcome to Uday Mart, {user.first_name}! 🎉')
                return redirect('home')

            if not otp_delivery_is_configured():
                messages.error(request, 'Account verification is being set up. Please try again later.')
            else:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.is_active = False
                    user.save()
                    CustomerProfile.objects.create(
                        user=user,
                        phone=form.cleaned_data['phone'],
                        whatsapp_opt_in=form.cleaned_data['whatsapp_opt_in'],
                    )
                _start_otp_flow(request, user, 'registration')
                messages.info(request, 'Enter the separate codes sent to your email and mobile number.')
                return redirect('verify_registration_otp')
    else:
        form = RegisterForm()
    return render(request, 'store/register.html', {'form': form})


@never_cache
def verify_registration_otp(request):
    user = _pending_otp_user(request, 'registration')
    if not user:
        messages.warning(request, 'Start registration before entering a verification code.')
        return redirect('register')
    if user.is_active:
        request.session.pop('otp_registration_user_id', None)
        return redirect('login')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid() and _finish_otp_verification(request, user, 'registration', form):
            user.is_active = True
            user.save(update_fields=['is_active'])
            request.session.pop('otp_registration_user_id', None)
            login(request, user)
            messages.success(request, f'Your email and mobile number are verified. Welcome, {user.first_name}!')
            return redirect('home')
    else:
        form = OTPVerificationForm()
    return _render_otp_verification(request, user, form, 'registration')


@require_POST
def resend_registration_otp(request):
    user = _pending_otp_user(request, 'registration')
    if not user:
        return redirect('register')
    if _start_otp_flow(request, user, 'registration'):
        messages.success(request, 'New verification codes have been sent.')
    return redirect('verify_registration_otp')


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            next_url = _safe_next_url(request, request.POST.get('next') or request.GET.get('next'))
            if otp_auth_enabled() and not user.is_staff:
                try:
                    profile = user.customer_profile
                except CustomerProfile.DoesNotExist:
                    profile = None
                if profile:
                    if _start_otp_flow(request, user, 'login', next_url):
                        messages.info(request, 'Enter the codes sent to your registered email and mobile number.')
                        return redirect('verify_login_otp')
                    # Password validation succeeded, but never skip OTP when
                    # the feature is enabled for a verified account.
                    return render(request, 'store/login.html', {'form': form})
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}! 👋')
            return redirect(next_url or 'home')
    else:
        form = AuthenticationForm()
    return render(request, 'store/login.html', {'form': form})


def otp_login_start(request):
    """Passwordless option for customers who prefer a verified OTP sign-in."""

    if request.user.is_authenticated:
        return redirect('home')
    if not otp_auth_enabled():
        messages.info(request, 'OTP sign-in is not enabled yet.')
        return redirect('login')
    if request.method == 'POST':
        form = OTPLoginStartForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            user = User.objects.filter(email__iexact=identifier).first()
            if not user:
                try:
                    user = User.objects.filter(customer_profile__phone=normalize_phone(identifier)).first()
                except PhoneNumberError:
                    user = User.objects.filter(username=identifier).first()

            if not user or not user.is_active:
                messages.error(request, 'We could not start OTP sign-in for those account details.')
            else:
                try:
                    profile = user.customer_profile
                except CustomerProfile.DoesNotExist:
                    profile = None
                if not profile or not profile.email_is_verified or not profile.phone_is_verified:
                    messages.error(request, 'This account has not completed email and mobile verification yet.')
                elif _start_otp_flow(request, user, 'login', _safe_next_url(request, request.GET.get('next'))):
                    messages.info(request, 'Enter the codes sent to your verified email and mobile number.')
                    return redirect('verify_login_otp')
    else:
        form = OTPLoginStartForm()
    return render(request, 'store/otp_login.html', {'form': form})


@never_cache
def verify_login_otp(request):
    user = _pending_otp_user(request, 'login')
    if not user:
        messages.warning(request, 'Start sign-in before entering a verification code.')
        return redirect('otp_login_start')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid() and _finish_otp_verification(request, user, 'login', form):
            next_url = request.session.pop('otp_login_next', None)
            request.session.pop('otp_login_user_id', None)
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect(_safe_next_url(request, next_url) or 'home')
    else:
        form = OTPVerificationForm()
    return _render_otp_verification(request, user, form, 'login')


@require_POST
def resend_login_otp(request):
    user = _pending_otp_user(request, 'login')
    if not user:
        return redirect('otp_login_start')
    if _start_otp_flow(request, user, 'login'):
        messages.success(request, 'New verification codes have been sent.')
    return redirect('verify_login_otp')


def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user)[:5]
    try:
        customer_profile = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        customer_profile = None
    return render(request, 'store/profile.html', {
        'orders': orders,
        'customer_profile': customer_profile,
    })
