from datetime import datetime
from app.integrations.base_adapter import BaseAdapter
from app.schemas.order import OrderCreate


class ShopifyAdapter(BaseAdapter):
    """Maps a Shopify order webhook payload to OrderCreate.

    Shopify order webhook fields used:
      shipping_address.address1, city, province, zip  → delivery address
      line_items[].quantity                            → quantity_units
      total_weight                                     → weight_kg (grams → kg)
      created_at                                       → scheduled_date
    """

    def transform(self, raw: dict) -> OrderCreate:
        addr = raw.get("shipping_address", {})
        parts = [addr.get("address1", ""), addr.get("city", ""), addr.get("province", "")]
        address = ", ".join(p for p in parts if p)

        lat = addr.get("latitude")
        lng = addr.get("longitude")

        quantity = sum(
            int(li.get("quantity", 0)) for li in raw.get("line_items", [])
        ) or None

        weight_grams = raw.get("total_weight", 0)
        weight_kg = (weight_grams / 1000.0) if weight_grams else None

        scheduled_date = datetime.now()
        raw_date = raw.get("created_at", "")
        if raw_date:
            try:
                scheduled_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except ValueError:
                pass

        return OrderCreate(
            delivery_address=address or "Unknown Shopify address",
            delivery_latitude=float(lat) if lat else None,
            delivery_longitude=float(lng) if lng else None,
            scheduled_date=scheduled_date,
            quantity_units=quantity,
            weight_kg=weight_kg,
            priority="NORMAL",
            external_ref=str(raw.get("order_number", "")),
            notes=f"Shopify order #{raw.get('order_number')}",
        )
