"""Tests for the CartSession quantity-update API and the update-quantity view."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from cart.cart import CartSession
from shop.models import ProductCategory, ProductModel

User = get_user_model()


class FakeSession(dict):
    modified = False


class CartSessionUpdateQuantityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="shopper@example.com", password="testpass123"
        )
        cls.category = ProductCategory.objects.create(
            title="دسته‌بندی", slug="cart-category"
        )
        cls.first = cls._create_product("first", price="100000", discount_percent=0)
        cls.second = cls._create_product("second", price="25000", discount_percent=20)

    @classmethod
    def _create_product(cls, slug, price, discount_percent=0):
        return ProductModel.objects.create(
            user=cls.user,
            category=cls.category,
            title=f"محصول {slug}",
            slug=slug,
            description="توضیحات",
            brief_description="خلاصه",
            price=price,
            discount_percent=discount_percent,
            stock=10,
        )

    def setUp(self):
        self.session = FakeSession()

    def _cart(self):
        return CartSession(self.session)

    def _add(self, product_id, qty=1):
        for _ in range(qty):
            c = self._cart()
            c.add_product(product_id)
            c.save()

    def test_update_quantity_changes_existing_item(self):
        self._add(self.first.pk, 1)

        c = self._cart()
        c.update_quantity(self.first.pk, 4)
        c.save()

        self.assertEqual(c.items[0]["quantity"], 4)

    def test_update_quantity_recalculates_total_items(self):
        self._add(self.first.pk, 1)
        self._add(self.second.pk, 2)

        c = self._cart()
        c.update_quantity(self.first.pk, 4)
        c.save()

        self.assertEqual(c.total_items, 6)

    def test_update_quantity_recalculates_total_price(self):
        # first=100000 * 4, second=25000*0.8 * 1 = 400000 + 20000 = 420000
        self._add(self.first.pk, 1)
        self._add(self.second.pk, 1)

        c = self._cart()
        c.update_quantity(self.first.pk, 4)
        c.save()

        self.assertEqual(c.total_price, Decimal("420000"))

    def test_update_quantity_does_not_affect_other_items(self):
        self._add(self.first.pk, 1)
        self._add(self.second.pk, 2)

        c = self._cart()
        c.update_quantity(self.first.pk, 4)
        c.save()

        self.assertEqual(c.items[1]["quantity"], 2)

    def test_update_quantity_raises_for_missing_product(self):
        self._add(self.first.pk, 1)
        c = self._cart()

        with self.assertRaises(KeyError):
            c.update_quantity(self.second.pk, 3)

    def test_update_quantity_raises_for_quantity_zero(self):
        self._add(self.first.pk, 1)

        c = self._cart()
        with self.assertRaises(ValueError):
            c.update_quantity(self.first.pk, 0)

    def test_update_quantity_raises_for_negative_quantity(self):
        self._add(self.first.pk, 1)

        c = self._cart()
        with self.assertRaises(ValueError):
            c.update_quantity(self.first.pk, -1)

    def test_clear_replaces_session_cart(self):
        self._add(self.first.pk, 1)
        self._add(self.second.pk, 1)

        c = self._cart()
        c.clear()

        self.assertEqual(c.items, [])
        self.assertEqual(self.session["cart"]["items"], [])


class UpdateQuantityViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="shopper@example.com", password="testpass123"
        )
        cls.category = ProductCategory.objects.create(
            title="دسته‌بندی", slug="cart-category"
        )
        cls.product = ProductModel.objects.create(
            user=cls.user,
            category=cls.category,
            title="محصول تست",
            slug="test-product",
            description="توضیحات",
            brief_description="خلاصه",
            price="50000",
            discount_percent=0,
            stock=10,
        )
        cls.url = reverse("cart:update_quantity")

    def setUp(self):
        self.client = Client()
        self._seed_cart()

    def _seed_cart(self):
        session = self.client.session
        session["cart"] = {
            "items": [{"product_id": self.product.pk, "quantity": 1}],
            "total_price": 50000,
            "total_items": 1,
        }
        session.save()

    def _post_json(self, payload):
        return self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
        )

    # --- happy path ----------------------------------------------------------

    def test_post_returns_success_true_and_updated_totals(self):
        response = self._post_json({
            "product_id": self.product.pk,
            "quantity": 4,
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_items"], 4)
        # 50000 * 4 = 200000
        self.assertEqual(data["total_price"], 200000)

    def test_post_updates_session_cart(self):
        self._post_json({"product_id": self.product.pk, "quantity": 3})

        session = self.client.session
        items = session["cart"]["items"]
        self.assertEqual(items[0]["quantity"], 3)

    # --- invalid / missing input ---------------------------------------------

    def test_missing_product_id_returns_400(self):
        response = self._post_json({"quantity": 1})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])

    def test_missing_quantity_returns_400(self):
        response = self._post_json({"product_id": self.product.pk})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])

    def test_quantity_zero_returns_400(self):
        response = self._post_json({
            "product_id": self.product.pk,
            "quantity": 0,
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "تعداد محصول نامعتبر است.")

    def test_quantity_negative_returns_400(self):
        response = self._post_json({
            "product_id": self.product.pk,
            "quantity": -1,
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            self.url,
            data="not json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])

    def test_non_integer_quantity_returns_400(self):
        response = self._post_json({
            "product_id": self.product.pk,
            "quantity": "abc",
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])

    # --- product not in cart -------------------------------------------------

    def test_product_not_in_cart_returns_404(self):
        response = self._post_json({
            "product_id": self.product.pk + 999,
            "quantity": 1,
        })

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["success"])

    def test_nonexistent_product_id_returns_404(self):
        response = self._post_json({
            "product_id": 99999,
            "quantity": 1,
        })

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["success"])

    # --- method enforcement --------------------------------------------------

    def test_get_is_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    # --- CSRF ----------------------------------------------------------------

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            self.url,
            data={"product_id": self.product.pk, "quantity": 2},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)