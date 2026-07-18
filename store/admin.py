from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Product, ProductImage,
    Cart, CartItem, Order, OrderItem,
    Review, Wishlist, CustomerProfile, OTPChallenge,
    OrderNotification
)

admin.site.site_header = "🛒 Uday Mart Admin"
admin.site.site_title = "Uday Mart"
admin.site.index_title = "Welcome to Uday Mart Dashboard"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'rating', 'is_available', 'is_featured']
    list_filter = ['category', 'is_available', 'is_featured']
    list_editable = ['price', 'stock', 'is_available', 'is_featured']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'brand', 'description']
    inlines = [ProductImageInline]
    list_per_page = 25


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'price', 'quantity']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'user', 'total_price', 'delivery_fee', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    list_editable = ['status']
    readonly_fields = [
        'order_id', 'user', 'total_price', 'delivery_fee', 'created_at',
        'current_location_link',
    ]
    inlines = [OrderItemInline]
    search_fields = ['order_id', 'user__username', 'full_name', 'phone']

    def current_location_link(self, obj):
        if not obj or not obj.has_current_location:
            return 'Customer did not share a current location.'
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Open shared location in Maps</a>',
            obj.current_location_map_url,
        )
    current_location_link.short_description = 'Shared current location'


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'phone_verified_at', 'email_verified_at', 'whatsapp_opt_in']
    list_filter = ['whatsapp_opt_in', 'phone_verified_at', 'email_verified_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['phone_verified_at', 'email_verified_at', 'whatsapp_opt_in_at', 'created_at', 'updated_at']


@admin.register(OTPChallenge)
class OTPChallengeAdmin(admin.ModelAdmin):
    list_display = ['user', 'purpose', 'recipient', 'created_at', 'expires_at', 'attempts', 'verified_at']
    list_filter = ['purpose', 'channel', 'verified_at']
    search_fields = ['user__username', 'recipient']
    readonly_fields = ['user', 'channel', 'purpose', 'recipient', 'expires_at', 'attempts', 'verified_at', 'created_at']
    exclude = ['code_hash']


@admin.register(OrderNotification)
class OrderNotificationAdmin(admin.ModelAdmin):
    list_display = ['order', 'channel', 'status', 'provider_message_id', 'created_at', 'sent_at']
    list_filter = ['channel', 'status', 'event']
    search_fields = ['order__order_id', 'order__user__username', 'provider_message_id']
    readonly_fields = [
        'order', 'event', 'channel', 'status', 'provider_message_id',
        'error_message', 'created_at', 'sent_at',
    ]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'title', 'created_at']
    list_filter = ['rating']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_items', 'total_price']


admin.site.register(Wishlist)
