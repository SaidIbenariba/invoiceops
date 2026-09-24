"""Canonical invoice contract (system design §2.2). Required fields have no default."""

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ChargeType(str, Enum):
    VOICE = "voice"
    SMS = "sms"
    DATA = "data"
    RECURRING = "recurring"
    ONE_OFF = "one_off"
    OTHER = "other"


class Line(BaseModel):
    charge_type: ChargeType
    amount: Decimal
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    description: str | None = None


class Invoice(BaseModel):
    invoice_no: str = Field(min_length=1)
    supplier_id: str = Field(min_length=1)
    invoice_date: date
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    period_start: date | None = None
    period_end: date | None = None
    net: Decimal
    tax: Decimal | None = None
    gross: Decimal
    lines: list[Line] = Field(min_length=1)


class Refusal(BaseModel):
    reason: str
    missing: list[str] = []
