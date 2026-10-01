"""Target fields a carrier spreadsheet column can map to, and their expected value kinds."""

from invoiceops.mapping.text import normalize

FIELD_TYPES: dict[str, str] = {
    "invoice_no": "id",
    "invoice_date": "date",
    "currency": "currency",
    "charge_type": "text",
    "description": "text",
    "quantity": "number",
    "unit_price": "number",
    "amount": "number",
}
TABLE_FIELDS: tuple[str, ...] = tuple(FIELD_TYPES)
REQUIRED_TABLE_FIELDS: tuple[str, ...] = ("invoice_no", "invoice_date", "currency", "charge_type", "amount")

CHARGE_LABELS: dict[str, dict[str, str]] = {
    "voice": {"en": "Voice", "fr": "Voix", "es": "Voz"},
    "sms": {"en": "SMS", "fr": "SMS", "es": "SMS"},
    "data": {"en": "Data", "fr": "Données", "es": "Datos"},
    "recurring": {"en": "Monthly fee", "fr": "Abonnement", "es": "Cuota mensual"},
}
CHARGE_LOOKUP: dict[str, str] = {
    normalize(label): charge for charge, labels in CHARGE_LABELS.items() for label in labels.values()
}
