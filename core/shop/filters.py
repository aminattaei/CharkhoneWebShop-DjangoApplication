from django.db.models import Q


class ProductFilter:
    param: str = None

    def apply(self, queryset, params):
        value = params.get(self.param, "").strip()
        if not value:
            return queryset
        return self.apply_filter(queryset, value)

    def apply_filter(self, queryset, value):
        raise NotImplementedError


class SearchProductFilter(ProductFilter):
    param = "q"

    def apply_filter(self, queryset, value):
        return queryset.filter(
            Q(title__icontains=value)
            | Q(brief_description__icontains=value)
            | Q(description__icontains=value)
        )


class MinPriceProductFilter(ProductFilter):
    param = "min_price"

    def apply_filter(self, queryset, value):
        return queryset.filter(price__gte=value)


class MaxPriceProductFilter(ProductFilter):
    param = "max_price"

    def apply_filter(self, queryset, value):
        return queryset.filter(price__lte=value)


class CategoryProductFilter(ProductFilter):
    param = "category_id"

    def apply_filter(self, queryset, value):
        if value.isdigit():
            return queryset.filter(category_id=value)
        return queryset


class OrderByProductFilter(ProductFilter):
    param = "order_by"
    choices = ("-created_date", "created_date", "-price", "price")

    def apply_filter(self, queryset, value):
        if value in self.choices:
            return queryset.order_by(value)
        return queryset


DEFAULT_PRODUCT_FILTERS = [
    SearchProductFilter,
    MinPriceProductFilter,
    MaxPriceProductFilter,
    CategoryProductFilter,
    OrderByProductFilter,
]


def apply_product_filters(queryset, params, filter_classes=DEFAULT_PRODUCT_FILTERS):
    for filter_class in filter_classes:
        queryset = filter_class().apply(queryset, params)
    return queryset