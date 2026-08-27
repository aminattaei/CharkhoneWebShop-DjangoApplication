from django.db import models


class ProductQuerySet(models.QuerySet):
    def published(self):
        from .models import ProductStatusType

        return self.filter(status=ProductStatusType.publish)
