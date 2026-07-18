import re
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Cart, CartItem, Category, CustomerProfile, Order, OrderNotification, Product
from .services import normalize_phone, send_email_otp, send_order_confirmation, verify_email_otp


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class PhoneAndRegistrationTests(TestCase):
    def test_normalize_indian_mobile_number(self):
        self.assertEqual(normalize_phone('98765 43210'), '+919876543210')
        self.assertEqual(normalize_phone('+14155552671'), '+14155552671')

    @override_settings(OTP_AUTH_ENABLED=False)
    def test_registration_saves_a_normalized_customer_phone(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Asha',
            'last_name': 'Kumar',
            'email': 'asha@example.com',
            'phone': '9876543210',
            'username': 'asha',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'whatsapp_opt_in': 'on',
        })

        self.assertRedirects(response, reverse('home'))
        profile = CustomerProfile.objects.get(user__username='asha')
        self.assertEqual(profile.phone, '+919876543210')
        self.assertTrue(profile.whatsapp_opt_in)

    @override_settings(
        OTP_AUTH_ENABLED=True,
        EMAIL_HOST='smtp.example.com',
        DEFAULT_FROM_EMAIL='shop@example.com',
        TWILIO_ACCOUNT_SID='ACtest',
        TWILIO_AUTH_TOKEN='token',
        TWILIO_VERIFY_SERVICE_SID='VAtest',
    )
    @patch('store.views.request_dual_otp')
    def test_otp_registration_creates_an_inactive_pending_account(self, request_dual_otp):
        response = self.client.post(reverse('register'), {
            'first_name': 'Ravi',
            'last_name': 'Kumar',
            'email': 'ravi@example.com',
            'phone': '9876543211',
            'username': 'ravi',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })

        self.assertRedirects(response, reverse('verify_registration_otp'))
        user = User.objects.get(username='ravi')
        self.assertFalse(user.is_active)
        self.assertEqual(user.customer_profile.phone, '+919876543211')
        request_dual_otp.assert_called_once_with(user, 'registration')

    def test_pending_registration_verification_page_renders(self):
        user = User.objects.create_user('pending', 'pending@example.com', 'SecurePass123!')
        user.is_active = False
        user.save(update_fields=['is_active'])
        CustomerProfile.objects.create(user=user, phone='+919876543213')
        session = self.client.session
        session['otp_registration_user_id'] = user.pk
        session.save()

        response = self.client.get(reverse('verify_registration_otp'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verify Your Account')


@override_settings(
    DEBUG=True,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='shop@example.com',
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
)
class EmailOTPTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('otpuser', 'otp@example.com', 'SecurePass123!')

    def test_email_code_is_hashed_and_can_be_verified_once(self):
        challenge = send_email_otp(self.user, 'login')
        self.assertNotEqual(challenge.code_hash, '')
        self.assertEqual(len(mail.outbox), 1)
        code = re.search(r'code is (\d{6})', mail.outbox[0].body).group(1)

        valid, message = verify_email_otp(self.user, 'login', code)
        self.assertTrue(valid, message)
        valid_again, _ = verify_email_otp(self.user, 'login', code)
        self.assertFalse(valid_again)


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class CheckoutAndNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('buyer', 'buyer@example.com', 'SecurePass123!')
        category = Category.objects.create(name='Groceries', slug='groceries')
        self.product = Product.objects.create(
            category=category,
            name='Rice Bag',
            slug='rice-bag',
            description='Fresh rice',
            price=Decimal('100.00'),
            stock=10,
        )
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

    @patch('store.views.send_order_confirmation')
    def test_checkout_saves_delivery_fee_final_total_and_location(self, _send_confirmation):
        self.client.force_login(self.user)
        response = self.client.post(reverse('checkout'), {
            'full_name': 'Buyer Kumar',
            'phone': '9876543212',
            'address_line1': 'Main Road',
            'address_line2': '',
            'city': 'Hyderabad',
            'state': 'Telangana',
            'pincode': '500001',
            'payment_method': 'COD',
            'location_latitude': '17.385044',
            'location_longitude': '78.486671',
            'location_accuracy': '22',
        })

        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse('order_success', kwargs={'order_id': order.order_id}))
        self.assertEqual(order.delivery_fee, Decimal('40.00'))
        self.assertEqual(order.total_price, Decimal('240.00'))
        self.assertEqual(order.phone, '+919876543212')
        self.assertTrue(order.has_current_location)

    @override_settings(
        EMAIL_HOST='',
        DEFAULT_FROM_EMAIL='',
        ORDER_EMAIL_NOTIFICATIONS_ENABLED=True,
        WHATSAPP_NOTIFICATIONS_ENABLED=False,
    )
    def test_unconfigured_notifications_are_logged_as_skipped(self):
        order = Order.objects.create(
            user=self.user,
            order_id='UMTEST123',
            total_price=Decimal('100.00'),
            full_name='Buyer Kumar',
            phone='+919876543212',
            address_line1='Main Road',
            city='Hyderabad',
            state='Telangana',
            pincode='500001',
        )
        send_order_confirmation(order.pk)

        statuses = dict(OrderNotification.objects.filter(order=order).values_list('channel', 'status'))
        self.assertEqual(statuses['email'], OrderNotification.STATUS_SKIPPED)
        self.assertEqual(statuses['whatsapp'], OrderNotification.STATUS_SKIPPED)
