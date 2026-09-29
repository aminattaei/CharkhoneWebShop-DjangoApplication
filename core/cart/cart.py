class CartSession:
    def __init__(self, session):
        self.session = session
        self._cart = self.session.setdefault("cart", {
            "items": [],
            "total_price": 0,
            "total_items": 0
        })
        self._update_totals()

    def add_product(self, product_id):
        for item in self._cart['items']:
            if item["product_id"] == product_id:
                item["quantity"] += 1
                break
        else:
            new_product = {
                "product_id": product_id,
                "quantity": 1
            }
            self._cart["items"].append(new_product)
        self._update_totals()

    def _update_totals(self):
        from shop.models import ProductModel
        product_ids = [item["product_id"] for item in self._cart["items"]]
        products = ProductModel.objects.filter(pk__in=product_ids)
        product_map = {str(p.pk): p for p in products}
        total_price = 0
        total_items = 0
        for item in self._cart["items"]:
            product = product_map.get(str(item["product_id"]))
            if product:
                total_price += float(product.final_price) * item["quantity"]
                total_items += item["quantity"]
        self._cart["total_price"] = total_price
        self._cart["total_items"] = total_items

    @property
    def items(self):
        return self._cart["items"]

    @property
    def total_items(self):
        return self._cart["total_items"]

    @property
    def total_price(self):
        return self._cart["total_price"]

    def save(self):
        self.session.modified = True

    def clear(self):
        self._cart = {
            "items": [],
            "total_price": 0,
            "total_items": 0
        }
        self.save()

