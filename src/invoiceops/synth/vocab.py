"""Multilingual header vocabulary for the synthetic generator.

The LAST variant of every list is a held-out synonym: only test carriers may use it,
so the alias dictionary built from dev carriers never contains it (scoping §9).
"""

LANGUAGES = ("en", "fr", "es")
CURRENCIES = ("EUR", "USD", "GBP")

HEADERS: dict[str, dict[str, list[str]]] = {
    "invoice_no": {
        "en": ["Invoice No", "Invoice Number", "Inv #", "Bill Ref", "Document No"],
        "fr": ["N° facture", "Numéro de facture", "Réf. facture", "N° pièce"],
        "es": ["N.º factura", "Número de factura", "Ref. factura", "Nº documento"],
    },
    "invoice_date": {
        "en": ["Invoice Date", "Bill Date", "Date Issued", "Doc Date"],
        "fr": ["Date facture", "Date d'émission", "Date pièce"],
        "es": ["Fecha factura", "Fecha de emisión", "Fecha doc."],
    },
    "currency": {
        "en": ["Currency", "Curr", "CCY"],
        "fr": ["Devise", "Monnaie"],
        "es": ["Moneda", "Divisa"],
    },
    "charge_type": {
        "en": ["Charge Type", "Service", "Traffic Type", "Usage Category"],
        "fr": ["Type de charge", "Service", "Type de trafic", "Catégorie"],
        "es": ["Tipo de cargo", "Servicio", "Tipo de tráfico", "Categoría"],
    },
    "description": {
        "en": ["Description", "Details", "Line Description", "Item"],
        "fr": ["Description", "Libellé", "Détail"],
        "es": ["Descripción", "Concepto", "Detalle"],
    },
    "quantity": {
        "en": ["Quantity", "Qty", "Volume", "Units", "Minutes"],
        "fr": ["Quantité", "Qté", "Volume", "Unités"],
        "es": ["Cantidad", "Cant.", "Volumen", "Unidades"],
    },
    "unit_price": {
        "en": ["Unit Price", "Rate", "Price/Unit", "Unit Cost"],
        "fr": ["Prix unitaire", "Tarif", "PU", "Coût unitaire"],
        "es": ["Precio unitario", "Tarifa", "P. unit.", "Coste unitario"],
    },
    "amount": {
        "en": ["Amount", "Line Total", "Charge", "Net Amount", "Inb usage cost"],
        "fr": ["Montant", "Total ligne", "Montant HT", "Coût trafic entrant"],
        "es": ["Importe", "Total línea", "Cargo", "Importe neto"],
    },
}

# (header, value kind). Some are adversarial: "Amount Prev. Period" looks like amount.
DISTRACTORS: dict[str, list[tuple[str, str]]] = {
    "en": [("Destination", "text"), ("Route ID", "id"), ("Account Manager", "text"), ("Tax Rate %", "number"),
           ("Amount Prev. Period", "number"), ("Call Count", "number"), ("Region Code", "id"), ("Internal Ref", "id")],
    "fr": [("Destination", "text"), ("ID route", "id"), ("Gestionnaire", "text"), ("Taux TVA %", "number"),
           ("Montant période préc.", "number"), ("Nb appels", "number"), ("Code région", "id"), ("Réf. interne", "id")],
    "es": [("Destino", "text"), ("ID ruta", "id"), ("Gestor de cuenta", "text"), ("Tipo IVA %", "number"),
           ("Importe periodo ant.", "number"), ("Nº llamadas", "number"), ("Código región", "id"), ("Ref. interna", "id")],
}

BANNERS: dict[str, list[str]] = {
    "en": ["{carrier} — Interconnect invoice statement", "Billing period: {period}"],
    "fr": ["{carrier} — Relevé de facturation interconnexion", "Période : {period}"],
    "es": ["{carrier} — Extracto de facturación de interconexión", "Periodo: {period}"],
}
