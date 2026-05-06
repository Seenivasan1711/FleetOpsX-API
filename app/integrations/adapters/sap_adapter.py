from datetime import datetime, date
from app.integrations.base_adapter import BaseAdapter
from app.schemas.order import OrderCreate

_SAP_PRIORITY = {
    "01": "CRITICAL",   # Express
    "02": "HIGH",       # Priority
    "03": "NORMAL",
    "04": "LOW",
}


class SAPAdapter(BaseAdapter):
    """Maps SAP IDOC/JSON delivery order fields to OrderCreate.

    Expected SAP field names (subset):
      ADRC.CITY1, ADRC.STREET  → delivery address
      VSART                    → shipping type code → priority
      WADAT_IST                → scheduled date (YYYYMMDD)
      BRGEW                    → gross weight kg
    """

    def transform(self, raw: dict) -> OrderCreate:
        adrc = raw.get("ADRC", {})
        city   = adrc.get("CITY1", "")
        street = adrc.get("STREET", "")
        address = f"{street}, {city}".strip(", ")

        priority = _SAP_PRIORITY.get(str(raw.get("VSART", "03")), "NORMAL")

        scheduled_date = datetime.now()
        raw_date = raw.get("WADAT_IST", "")
        if raw_date and len(raw_date) == 8:
            try:
                d = date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8]))
                scheduled_date = datetime.combine(d, datetime.min.time())
            except ValueError:
                pass

        weight = None
        try:
            weight = float(raw.get("BRGEW", 0)) or None
        except (TypeError, ValueError):
            pass

        return OrderCreate(
            delivery_address=address or "Unknown SAP address",
            priority=priority,
            scheduled_date=scheduled_date,
            weight_kg=weight,
            external_ref=raw.get("VBELN"),
            notes=f"SAP import: VSART={raw.get('VSART')}",
        )
