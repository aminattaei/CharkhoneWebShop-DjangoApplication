"""Tests for the Cart items API and the reverse-manager name collision.

``Cart`` used to declare a property named ``items`` while ``CartItem.cart``
declared ``related_name="items"``. The reverse manager is contributed to
``Cart`` after the class body is evaluated, so the descriptor silently
replaced the property: ``cart.items`` was a manager, the documented
session-friendly list of dicts was unreachable, and the two meanings of the
name could not coexist.

These tests pin the two concepts apart: ``cart.items`` is the public
representation shared with ``CartSession``, and the queryset of ``CartItem``
rows is reachable under its own name.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Manager
from django.test import TestCase

from cart.cart import CartSession
from cart.models import Cart, CartItem
from shop.models import ProductCategory, ProductModel

User = get_user_model()


class FakeSession(dict):
    """Minimal stand-in for a Django session used by CartSession."""

    modified = False


class CartItemsApiTests(TestCase):
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
        self.cart = Cart.objects.create(user=self.user)

    # --- the collision itself -------------------------------------------------

    def test_items_is_not_the_reverse_manager(self):
        # Guards the original defect: the descriptor overwrote the property.
        self.assertNotIsInstance(self.cart.items, Manager)
        self.assertIsInstance(self.cart.items, list)

    def test_items_property_is_reachable_on_the_class(self):
        # The property must actually exist and not be shadowed away.
        self.assertIsInstance(type(self.cart).items, property)

    def test_reverse_manager_is_reachable_under_its_own_name(self):
        self.assertIsInstance(self.cart.line_items, Manager)

    def test_items_and_reverse_manager_agree_on_the_same_rows(self):
        self.cart.add_item(self.first.pk, 2)

        from_property = sorted(
            (entry["product_id"], entry["quantity"]) for entry in self.cart.items
        )
        from_manager = sorted(
            (item.product_id, item.quantity) for item in self.cart.line_items.all()
        )

        self.assertEqual(from_property, from_manager)

    # --- adding an item -------------------------------------------------------

    def test_add_item_creates_a_cart_item(self):
        cart_item = self.cart.add_item(self.first.pk)

        self.assertIsInstance(cart_item, CartItem)
        self.assertEqual(cart_item.product_id, self.first.pk)
        self.assertEqual(cart_item.quantity, 1)
        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 1)

    def test_add_item_accepts_an_explicit_quantity(self):
        cart_item = self.cart.add_item(self.first.pk, quantity=4)

        self.assertEqual(cart_item.quantity, 4)

    def test_add_item_increments_quantity_for_an_existing_product(self):
        self.cart.add_item(self.first.pk, 2)
        self.cart.add_item(self.first.pk, 3)

        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 1)
        self.assertEqual(self.cart.line_items.get().quantity, 5)

    def test_add_item_keeps_distinct_products_separate(self):
        self.cart.add_item(self.first.pk, 2)
        self.cart.add_item(self.second.pk, 1)

        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 2)
        self.assertEqual(self.cart.total_items, 3)

    # --- retrieving cart items ------------------------------------------------

    def test_items_returns_product_id_and_quantity_pairs(self):
        self.cart.add_item(self.first.pk, 2)

        self.assertEqual(
            self.cart.items,
            [{"product_id": self.first.pk, "quantity": 2}],
        )

    def test_items_is_empty_for_a_new_cart(self):
        self.assertEqual(self.cart.items, [])

    def test_items_is_a_plain_list_of_dicts(self):
        self.cart.add_item(self.first.pk)

        for entry in self.cart.items:
            self.assertIsInstance(entry, dict)
            self.assertEqual(set(entry), {"product_id", "quantity"})

    # --- totals ---------------------------------------------------------------

    def test_total_items_sums_quantities_across_products(self):
        self.cart.add_item(self.first.pk, 2)
        self.cart.add_item(self.second.pk, 5)

        self.assertEqual(self.cart.total_items, 7)

    def test_total_items_is_zero_for_an_empty_cart(self):
        self.assertEqual(self.cart.total_items, 0)

    def test_total_price_uses_final_price_times_quantity(self):
        # 100000 + (25000 * 0.8 * 2) = 140000
        self.cart.add_item(self.first.pk, 1)
        self.cart.add_item(self.second.pk, 2)

        self.assertEqual(self.cart.total_price, Decimal("140000"))

    def test_total_price_reflects_a_quantity_increment(self):
        self.cart.add_item(self.first.pk, 1)
        self.cart.add_item(self.first.pk, 1)

        self.assertEqual(self.cart.total_price, Decimal("200000"))

    def test_total_price_is_zero_for_an_empty_cart(self):
        self.assertEqual(self.cart.total_price, 0)

    # --- merging a session cart into a user cart -----------------------------

    def test_merge_session_cart_adds_every_session_item(self):
        session = FakeSession()
        session_cart = CartSession(session)
        session_cart.add_product(self.first.pk)
        session_cart.add_product(self.second.pk)

        self.cart.merge_session_cart(session_cart)

        self.assertEqual(self.cart.total_items, 2)
        self.assertEqual(
            sorted(entry["product_id"] for entry in self.cart.items),
            sorted([self.first.pk, self.second.pk]),
        )

    def test_merge_session_cart_preserves_session_quantities(self):
        session = FakeSession()
        session_cart = CartSession(session)
        session_cart.add_product(self.first.pk)
        session_cart.add_product(self.first.pk)
        session_cart.add_product(self.first.pk)

        self.cart.merge_session_cart(session_cart)

        self.assertEqual(self.cart.total_items, 3)
        self.assertEqual(self.cart.items[0]["quantity"], 3)

    def test_merge_session_cart_sums_into_existing_user_items(self):
        self.cart.add_item(self.first.pk, 1)

        session = FakeSession()
        session_cart = CartSession(session)
        session_cart.add_product(self.first.pk)
        session_cart.add_product(self.first.pk)

        self.cart.merge_session_cart(session_cart)

        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 1)
        self.assertEqual(self.cart.items[0]["quantity"], 3)

    def test_merge_session_cart_empties_the_session_cart(self):
        session = FakeSession()
        session_cart = CartSession(session)
        session_cart.add_product(self.first.pk)

        self.cart.merge_session_cart(session_cart)

        self.assertEqual(session_cart.items, [])
        self.assertEqual(session_cart.total_items, 0)
        self.assertTrue(session.modified)

    def test_merge_session_cart_of_an_empty_session_changes_nothing(self):
        session = FakeSession()
        session_cart = CartSession(session)
        self.cart.add_item(self.first.pk, 2)

        self.cart.merge_session_cart(session_cart)

        self.assertEqual(self.cart.total_items, 2)

    def test_cart_items_use_the_same_shape_as_cart_session_items(self):
        # The reason the property exists: a Cart and a CartSession must expose
        # items in the same shape so one can be consumed where the other is
        # expected.
        session = FakeSession()
        session_cart = CartSession(session)
        session_cart.add_product(self.first.pk)
        session_cart.add_product(self.second.pk)

        self.cart.add_item(self.first.pk)
        self.cart.add_item(self.second.pk)

        cart_shape = [sorted(entry) for entry in self.cart.items]
        session_shape = [sorted(entry) for entry in session_cart.items]

        self.assertEqual(cart_shape, session_shape)
        self.assertEqual(cart_shape, [["product_id", "quantity"]] * 2)

    def test_merged_cart_reflects_what_the_session_cart_held(self):
        session = FakeSession()
        session_cart = CartSession(session)
        session_cart.add_product(self.first.pk)
        session_cart.add_product(self.first.pk)
        session_cart.add_product(self.second.pk)

        expected = sorted(
            (entry["product_id"], entry["quantity"]) for entry in session_cart.items
        )

        self.cart.merge_session_cart(session_cart)

        self.assertEqual(
            sorted(
                (entry["product_id"], entry["quantity"]) for entry in self.cart.items
            ),
            expected,
        )


class CartGetOrCreateForUserTests(TestCase):
    def test_get_or_create_for_user_reuses_an_existing_cart(self):
        user = User.objects.create_user(
            email="reuse@example.com", password="testpass123"
        )
        first = Cart.get_or_create_for_user(user)
        second = Cart.get_or_create_for_user(user)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Cart.objects.filter(user=user).count(), 1)
