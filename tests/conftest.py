import pytest

from invoiceops.synth.generate import generate


@pytest.fixture(scope="session")
def tiny_dataset(tmp_path_factory):
    out = tmp_path_factory.mktemp("synthetic")
    generate(out, seed=7, n_carriers=10, per_template=2)
    return out
