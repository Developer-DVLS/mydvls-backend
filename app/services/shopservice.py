
class ShopService:
    def get_discount_value(self, offer):
        if not offer:
            return 0

        if offer.discount_type == "PERCENT":
            return offer.discount_value  # percentage

        if offer.discount_type == "FLAT":
            return offer.discount_value  # flat amount

        return 0

    def collect_applicable_offers(
        self,
        product,
        item_map,
        category_map,
        store_offer
    ):
        offers = []

        for variant in product.variants:
            # ITEM
            offer = item_map.get(variant.product_id)
            if offer:
                offers.append(offer)

            # CATEGORY
            category_id = getattr(variant.product, "category_id", None)
            offer = category_map.get(category_id)
            if offer:
                offers.append(offer)

            # STORE
            if store_offer:
                offers.append(store_offer)

        return offers
    
    
    def pick_best_offer(self, offers):
        if not offers:
            return None

        return max(
            offers,
            key=lambda o: self.get_discount_value(o)
        )