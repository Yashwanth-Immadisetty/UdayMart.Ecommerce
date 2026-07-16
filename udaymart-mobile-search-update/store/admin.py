from django.contrib import admin
from .models import (
    Category, Product, ProductImage,
    Cart, CartItem, Order, OrderItem,
    Review, Wishlist
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
    list_display = ['order_id', 'user', 'total_price', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    list_editable = ['status']
    readonly_fields = ['order_id', 'user', 'total_price', 'created_at']
    inlines = [OrderItemInline]
    search_fields = ['order_id', 'user__username', 'full_name', 'phone']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'title', 'created_at']
    list_filter = ['rating']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_items', 'total_price']


admin.site.register(Wishlist)
