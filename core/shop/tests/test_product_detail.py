"""Regression tests for public access to products.

The product detail URL used to read from the unrestricted queryset, so a draft
product was reachable by anyone who knew its slug. The public detail page must
only ever resolve published products.
"""

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse

from shop.models import ProductCategory, ProductModel, ProductStatusType
from shop.views import ProductDetailView

User = get_user_model()


class ProductDetailVisibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="seller@example.com", password="testpass123"
        )
        cls.category = ProductCategory.objects.create(
            title="دسته‌بندی", slug="test-category"
        )

    def _create_product(self, status, slug, **kwargs):
        defaults = {
            "user": self.user,
            "category": self.category,
            "title": f"محصول {slug}",
            "description": "توضیحات",
            "brief_description": "خلاصه",
            "price": "100000",
            "stock": 5,
            "status": status,
        }
        defaults.update(kwargs)
        return ProductModel.objects.create(slug=slug, **defaults)

    @staticmethod
    def _url(slug):
        return reverse("shop:product_detail", kwargs={"slug": slug})

    # 1. published product detail returns 200
    def test_published_product_detail_returns_200(self):
        product = self._create_product(ProductStatusType.publish, "published-p")

        response = self.client.get(self._url("published-p"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["product"], product)

    # 2. draft product detail returns 404
    def test_draft_product_detail_returns_404(self):
        self._create_product(ProductStatusType.draft, "draft-p")

        response = self.client.get(self._url("draft-p"))

        self.assertEqual(response.status_code, 404)

    # 3. any other non-published status returns 404
    def test_other_non_published_status_returns_404(self):
        # status is a plain IntegerField, so values outside the declared choices
        # must not become reachable either.
        for status in (0, 3, 99):
            with self.subTest(status=status):
                self._create_product(status, f"other-{status}")

                response = self.client.get(self._url(f"other-{status}"))

                self.assertEqual(response.status_code, 404)

    # 4. unknown slug returns 404
    def test_unknown_slug_returns_404(self):
        response = self.client.get(self._url("no-such-product"))

        self.assertEqual(response.status_code, 404)

    def test_missing_slug_still_raises_404(self):
        request = RequestFactory().get("/shop/product/")
        view = ProductDetailView()
        view.setup(request, slug=None)

        with self.assertRaises(Http404):
            view.get_object()

    # 5. published product still loads its related images
    def test_published_product_still_loads_related_images(self):
        product = self._create_product(ProductStatusType.publish, "img-p")

        response = self.client.get(self._url("img-p"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("images", response.context)
        self.assertEqual(
            list(response.context["images"]),
            list(product.product_images.all()),
        )

    def test_detail_view_prefetches_product_images(self):
        self._create_product(ProductStatusType.publish, "prefetch-p")
        request = RequestFactory().get(self._url("prefetch-p"))
        view = ProductDetailView()
        view.setup(request, slug="prefetch-p")

        obj = view.get_object()

        self.assertIn("product_images", obj._prefetched_objects_cache)
        with self.assertNumQueries(0):
            list(obj.product_images.all())

    def test_draft_slug_does_not_leak_published_product(self):
        draft = self._create_product(ProductStatusType.draft, "secret-p")
        published = self._create_product(ProductStatusType.publish, "real-p")

        response = self.client.get(self._url(draft.slug))

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, draft.title, status_code=404)
        self.assertEqual(self.client.get(self._url(published.slug)).status_code, 200)

    def test_detail_page_scope_matches_published_queryset(self):
        published = self._create_product(ProductStatusType.publish, "pub-p")
        draft = self._create_product(ProductStatusType.draft, "draft-p")

        self.assertEqual(list(ProductModel.objects.published()), [published])
        self.assertNotIn(
            draft.pk,
            ProductModel.objects.published().values_list("pk", flat=True),
        )