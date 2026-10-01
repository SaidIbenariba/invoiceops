import pytest

from invoiceops.mapping.stages import default_encoder


@pytest.mark.slow
def test_multilingual_model_relates_translations():
    enc = default_encoder()
    v = enc(["montant", "amount", "destination"])
    assert v[0] @ v[1] > v[0] @ v[2]
