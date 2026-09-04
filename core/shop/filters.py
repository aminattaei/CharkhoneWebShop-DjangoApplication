from django.db.models import Q


class ProductFilter:
    param: str

    def apply(self, queryset, params):
        value = params.get(self.param, "").strip()

        if not value:
            return queryset

        return self.apply_filter(queryset, value)

    def apply_filter(self, queryset, value):
        raise NotImplementedError


# ==========================================
# Search
# ==========================================

class SearchProductFilter(ProductFilter):

    param = "q"

    def apply_filter(self, queryset, value):

        return queryset.filter(
            Q(title__icontains=value)
            | Q(brief_description__icontains=value)
            | Q(description__icontains=value)
        )


# ==========================================
# Minimum Price
# ==========================================

class MinPriceProductFilter(ProductFilter):

    param = "min_price"

    def apply_filter(self, queryset, value):

        return queryset.filter(
            price__gte=value
        )


# ==========================================
# Maximum Price
# ==========================================

class MaxPriceProductFilter(ProductFilter):

    param = "max_price"

    def apply_filter(self, queryset, value):

        return queryset.filter(
            price__lte=value
        )


# ==========================================
# Category
# ==========================================

class CategoryProductFilter(ProductFilter):

    param = "category_slug"

    def apply_filter(self, queryset, value):

        return queryset.filter(
            category__slug=value
        )


# ==========================================
# Ordering
# ==========================================

class OrderByProductFilter(ProductFilter):

    param = "order_by"

    choices = (
        "-created_date",
        "created_date",
        "-price",
        "price",
    )

    def apply_filter(self, queryset, value):

        if value in self.choices:
            return queryset.order_by(value)

        return queryset


# ==========================================
# Default Filters
# ==========================================

DEFAULT_PRODUCT_FILTERS = [
    SearchProductFilter,
    MinPriceProductFilter,
    MaxPriceProductFilter,
    CategoryProductFilter,
    OrderByProductFilter,
]


# ==========================================
# Apply Filters
# ==========================================

def apply_product_filters(
    queryset,
    params,
    filter_classes=DEFAULT_PRODUCT_FILTERS,
):

    for filter_class in filter_classes:

        queryset = filter_class().apply(
            queryset,
            params,
        )

    return queryset