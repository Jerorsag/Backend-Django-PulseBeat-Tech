from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.urls import path
from django.template.response import TemplateResponse
from .models import Product, Cart, CartItem, Transaction

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['subtotal']

    def subtotal(self, obj):
        return obj.quantity * obj.product.price

    subtotal.short_description = 'Subtotal'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'price', 'category', 'stock_status')
    list_filter = ('category',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 20
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'description', 'price', 'category')
        }),
        ('Media', {
            'fields': ('image',)
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />',
                               obj.image.url)
        return "No Image"

    image_preview.short_description = 'Image'

    def stock_status(self, obj):
        # This is a placeholder - implement actual stock tracking if needed
        return format_html('<span style="color: green; font-weight: bold;">In Stock</span>')

    stock_status.short_description = 'Stock Status'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('cart_code', 'user', 'total_items', 'total_amount', 'paid', 'created_at')
    list_filter = ('paid', 'created_at')
    search_fields = ('cart_code', 'user__username', 'user__email')
    readonly_fields = ('cart_code', 'created_at', 'modified_at', 'total_amount')
    inlines = [CartItemInline]
    date_hierarchy = 'created_at'

    def total_items(self, obj):
        return obj.items.aggregate(Sum('quantity'))['quantity__sum'] or 0

    total_items.short_description = 'Items'

    def total_amount(self, obj):
        total = 0
        for item in obj.items.all():
            total += item.quantity * item.product.price
        return f"${total:.2f}"

    total_amount.short_description = 'Total'

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of paid carts
        if obj and obj.paid:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('ref', 'user', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('ref', 'user__username', 'user__email')
    readonly_fields = ('ref', 'cart', 'amount', 'currency', 'created_at', 'modified_at')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        # Transactions should only be created programmatically
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of completed transactions
        if obj and obj.status in ['completed', 'successful']:
            return False
        return super().has_delete_permission(request, obj)

# Register additional inlines or customizations as needed