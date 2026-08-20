from django.contrib import admin

from .models import ProductCategory, ProductImageModel, ProductModel


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


    