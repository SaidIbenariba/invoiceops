"""Build the canonical contract from a draft dict, or refuse with a reason. Never raises on bad data."""

from collections.abc import Mapping

from pydantic import ValidationError

from invoiceops.contract.models import Invoice, Refusal

REQUIRED_INVOICE = ("invoice_no", "supplier_id", "invoice_date", "currency", "net", "gross", "lines")
REQUIRED_LINE = ("charge_type", "amount")


def _missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    return False


def build_contract(draft: dict) -> Invoice | Refusal:
    missing = [f for f in REQUIRED_INVOICE if _missing(draft.get(f))]
    lines = draft.get("lines")
    if isinstance(lines, (list, tuple)):
        for i, line in enumerate(lines):
            if not isinstance(line, Mapping):
                missing.append(f"lines[{i}]")
                continue
            missing += [f"lines[{i}].{f}" for f in REQUIRED_LINE if _missing(line.get(f))]
    if missing:
        return Refusal(reason="missing_required", missing=missing)

    try:
        inv = Invoice.model_validate(draft)
    except ValidationError as e:
        fields = sorted({".".join(str(p) for p in err["loc"]) for err in e.errors()})
        return Refusal(reason="invalid", missing=fields)

    if inv.tax is None and inv.gross != inv.net:
        return Refusal(reason="tax_missing_and_gross_ne_net", missing=["tax"])

    return inv
