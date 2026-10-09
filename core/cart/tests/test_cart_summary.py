"""Tests for the CartSummaryTemplateView."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from cart.cart import CartSession
from shop.models import ProductCategory, ProductModel

User = get_user_model()


class FakeSession(dict):
    """Minimal stand-in for a Django session used by CartSession."""

    modified = False


class CartSummaryViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="shopper@example.com", password="testpass123"
        )
        cls.category = ProductCategory.objects.create(
            title="دسته‌بندی", slug="cart-summary-category"
        )
        cls.product1 = cls._create_product("product1", price="100000", discount_percent=0)
        cls.product2 = cls._create_product("product2", price="50000", discount_percent=10)

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
        self.client = Client()
        self.url = reverse("cart:cart_summary")

    def _seed_session_cart(self, items):
        """Seed the session with cart data."""
        session = self.client.session
        session["cart"] = {
            "items": items,
            "total_price": "0",
            "total_items": 0,
        }
        session.save()
        # Recalculate totals by creating CartSession
        cart = CartSession(session)
        cart.save()

    def test_cart_summary_returns_200_for_empty_cart(self):
        """Test that cart summary page returns HTTP 200 for empty cart."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_cart_summary_displays_empty_cart_message(self):
        """Test that empty cart shows appropriate message."""
        response = self.client.get(self.url)
        self.assertContains(response, "سبد خرید شما خالی است")

    def test_cart_summary_displays_products_from_session(self):
        """Test that products in session cart appear in rendered response."""
        self._seed_session_cart([
            {"product_id": self.product1.pk, "quantity": 2},
            {"product_id": self.product2.pk, "quantity": 1},
        ])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Check product titles appear
        self.assertContains(response, self.product1.title)
        self.assertContains(response, self.product2.title)

        # Check quantities
        self.assertContains(response, "2")  # quantity for product1
        self.assertContains(response, "1")  # quantity for product2

    def test_cart_summary_displays_correct_total_items(self):
        """Test that total items count is displayed correctly."""
        self._seed_session_cart([
            {"product_id": self.product1.pk, "quantity": 2},
            {"product_id": self.product2.pk, "quantity": 3},
        ])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Total items = 2 + 3 = 5
        self.assertContains(response, "5")

    def test_cart_summary_displays_correct_total_price(self):
        """Test that total price is calculated and displayed correctly."""
        # product1: 100000 * 2 = 200000
        # product2: 50000 * 0.9 * 1 = 45000 (with 10% discount)
        # Total: 245000
        self._seed_session_cart([
            {"product_id": self.product1.pk, "quantity": 2},
            {"product_id": self.product2.pk, "quantity": 1},
        ])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Check total price appears (formatted with commas)
        self.assertContains(response, "245,000")

    def test_cart_summary_shows_product_images(self):
        """Test that product images are referenced in the response."""
        self._seed_session_cart([
            {"product_id": self.product1.pk, "quantity": 1},
        ])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Should have img tag for product image
        self.assertContains(response, "<img")

    def test_cart_summary_quantity_selectors_present(self):
        """Test that quantity selectors are rendered for each item."""
        self._seed_session_cart([
            {"product_id": self.product1.pk, "quantity": 1},
        ])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Check for quantity select element
        self.assertContains(response, "product-quantity")
        self.assertContains(response, "data-product-id")

    def test_cart_summary_includes_csrf_token(self):
        """Test that CSRF token meta tag is present for AJAX."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Check for CSRF token meta tag
        self.assertContains(response, 'name="csrf-token"')

    def test_cart_summary_continue_shopping_link(self):
        """Test that continue shopping link is present."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Check for continue shopping link
        self.assertContains(response, "به خرید ادامه دهید")

    def test_cart_summary_checkout_link(self):
        """Test that checkout link is present."""
        self._seed_session_cart([
            {"product_id": self.product1.pk, "quantity": 1},
        ])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Check for checkout button
        self.assertContains(response, "ثبت سفارش")


class CartSummaryAuthenticatedUserTests(TestCase):
    """Tests for cart summary with authenticated user (uses Cart model)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="authenticated@example.com", password="testpass123"
        )
        cls.category = ProductCategory.objects.create(
            title="دسته‌بندی", slug="auth-cart-category"
        )
        cls.product = cls._create_product("auth-product", price="75000", discount_percent=0)

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
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("cart:cart_summary")

    def test_authenticated_user_sees_cart(self):
        """Test that authenticated user can see cart summary."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_cart_shows_items(self):
        """Test that authenticated user's cart shows items."""
        from cart.models import Cart

        cart = Cart.get_or_create_for_user(self.user)
        cart.add_item(self.product.pk, 2)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.title)
        self.assertContains(response, "2")  # quantity