from django.contrib import admin

from .models import (
    ProductCategory, 
    ProductImageModel,
    ProductModel,
    Subscriber,
    Newsletter,
    NewsletterRecipient
    )


class ProductImageInline(admin.TabularInline):
    model = ProductImageModel
    extra = 1


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "slug", "created_date", "updated_date")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_date", "updated_date")
    ordering = ("-created_date",)


@admin.register(ProductModel)
class ProductModelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "slug",
        "user",
        "category",
        "stock",
        "status",
        "price",
        "discount_percent",
        "created_date",
    )
    list_filter = ("status", "category", "created_date")
    search_fields = ("title", "slug", "description", "brief_description")
    list_select_related = ("user", "category")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_date", "updated_date")
    raw_id_fields = ("user",)
    autocomplete_fields = ("category",)
    inlines = (ProductImageInline,)
    ordering = ("-created_date",)


@admin.register(ProductImageModel)
class ProductImageModelAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "file", "created_date", "updated_date")
    search_fields = ("product__title",)
    list_select_related = ("product",)
    readonly_fields = ("created_date", "updated_date")
    autocomplete_fields = ("product",)
    ordering = ("-created_date",)



@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'is_active', 'is_verified', 'subscribed_at')
    list_filter = ('is_active', 'is_verified', 'subscribed_at')
    search_fields = ('email', 'name')
    actions = ['unsubscribe_selected']
    
    def unsubscribe_selected(self, request, queryset):
        for subscriber in queryset:
            subscriber.unsubscribe()
        self.message_user(request, f"{queryset.count()} subscribers unsubscribed.")
    unsubscribe_selected.brief_description = "Unsubscribe selected"


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('subject', 'status', 'created_by', 'created_at', 'get_recipient_count')
    list_filter = ('status', 'created_at')
    search_fields = ('subject', 'preview_text')
    readonly_fields = ('sent_at', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Content', {
            'fields': ('subject', 'preview_text', 'content', 'plain_text_content')
        }),
        ('Status & Scheduling', {
            'fields': ('status', 'scheduled_for', 'sent_at')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def get_recipient_count(self, obj):
        return obj.get_recipient_count()
    get_recipient_count.brief_description = "Recipients"


@admin.register(NewsletterRecipient)
class NewsletterRecipientAdmin(admin.ModelAdmin):
    list_display = ('newsletter', 'subscriber', 'status', 'sent_at', 'opened_at')
    list_filter = ('status',)
    search_fields = ('newsletter__subject', 'subscriber__email')
    raw_id_fields = ('newsletter', 'subscriber')