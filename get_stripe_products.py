# uses python v3.12.1

import stripe

stripe.api_key = "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"

# gets all active products and their payment links based on a flag in the metadata of the payment link: name = "product_name"
def get_products():
    products = stripe.Product.list(limit=100)
    links = stripe.PaymentLink.list(active=True, limit=100)

    product_data = {}

    for product in products.data:
        prices = stripe.Price.list(product=product.id, limit=1)
        if not prices.data:
            continue

        link_url = None
        for link in links:
            if link.metadata.get("name") == product.name:

                link_url = link.url
                break

        if prices.data and link_url:
            price = prices.data[0]
            if price.unit_amount is not None:
                amount = price.unit_amount / 100
                currency = price.currency.upper()
                product_data[product.name] = {
                    "price": f"${amount:.2f} {currency}",
                    "link": link_url
                }

    return product_data