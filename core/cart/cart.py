from decimal import Decimal

from shop.models import ProductModel


class CartSession:
    SESSION_KEY = "cart"

    def __init__(self, session):
        self.session = session

        self._cart = self.session.setdefault(
            self.SESSION_KEY,
            {
                "items": [],
                "total_price": "0",
                "total_items": 0,
            },
        )

        self._cart.setdefault("items", [])
        self._cart.setdefault("total_price", "0")
        self._cart.setdefault("total_items", 0)

        self._update_totals()

    @staticmethod
    def _normalize_product_id(product_id):
        if product_id is None or not str(product_id).strip():
            raise ValueError("شناسه محصول نامعتبر است.")

        return str(product_id)

    @staticmethod
    def _validate_quantity(quantity):
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity < 1
        ):
            raise ValueError("تعداد محصول نامعتبر است.")

        return quantity

    def add_product(self, product_id):
        product_id = self._normalize_product_id(product_id)

        for item in self._cart["items"]:
            if str(item["product_id"]) == product_id:
                current_quantity = self._validate_quantity(
                    item["quantity"]
                )

                item["quantity"] = current_quantity + 1
                break
        else:
            self._cart["items"].append(
                {
                    "product_id": product_id,
                    "quantity": 1,
                }
            )

        self._update_totals()
        self.save()

    def get_cart_dict(self):
        return self._cart

    def update_quantity(self, product_id, quantity):
        product_id = self._normalize_product_id(product_id)
        quantity = self._validate_quantity(quantity)

        for item in self._cart["items"]:
            if str(item["product_id"]) == product_id:
                item["quantity"] = quantity
                break
        else:
            raise KeyError("محصول در سبد خرید وجود ندارد.")

        self._update_totals()
        self.save()

    def _update_totals(self):
        product_ids = [
            item["product_id"]
            for item in self._cart["items"]
        ]

        products = ProductModel.objects.filter(
            pk__in=product_ids
        )

        product_map = {
            str(product.pk): product
            for product in products
        }

        total_price = Decimal("0")
        total_items = 0

        for item in self._cart["items"]:
            product_id = str(item["product_id"])
            product = product_map.get(product_id)

            if product is None:
                continue

            quantity = self._validate_quantity(item["quantity"])

            product_price = Decimal(
                str(product.final_price or 0)
            )

            total_price += product_price * quantity
            total_items += quantity

        new_total_price = str(total_price)

        if (
            self._cart.get("total_price") != new_total_price
            or self._cart.get("total_items") != total_items
        ):
            self._cart["total_price"] = new_total_price
            self._cart["total_items"] = total_items
            self.save()

    @property
    def items(self):
        return self._cart["items"]

    @property
    def total_items(self):
        return self._cart["total_items"]

    @property
    def total_price(self):
        return Decimal(str(self._cart["total_price"]))

    def save(self):
        self.session.modified = True

    def clear(self):
        self._cart = {
            "items": [],
            "total_price": "0",
            "total_items": 0,
        }

        self.session[self.SESSION_KEY] = self._cart
        self.save()