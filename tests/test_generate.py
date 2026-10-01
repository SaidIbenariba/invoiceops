import json
import random

import pytest

from invoiceops.synth.generate import check_no_leakage, generate, split_carriers


def test_split_is_60_20_20_and_disjoint():
    ids = [f"C{k:02d}" for k in range(1, 16)]
    split = split_carriers(ids, random.Random(0))
    counts = {s: sum(1 for v in split.values() if v == s) for s in ("dev", "calibration", "test")}
    assert counts == {"dev": 9, "calibration": 3, "test": 3}


def test_leakage_check_raises_on_shared_carrier():
    entries = [{"split": "dev", "carrier_id": "C01"}, {"split": "test", "carrier_id": "C01"}]
    with pytest.raises(ValueError, match="leakage"):
        check_no_leakage(entries)


def test_manifest_counts_and_files(tiny_dataset):
    manifest = json.loads((tiny_dataset / "manifest.json").read_text())
    assert len(manifest["entries"]) == 10 * 3 * 2
    for e in manifest["entries"]:
        assert (tiny_dataset / e["path"]).exists()
        assert e["record"]["supplier_id"] == e["carrier_id"]
    test_carriers = {e["carrier_id"] for e in manifest["entries"] if e["split"] == "test"}
    dev_carriers = {e["carrier_id"] for e in manifest["entries"] if e["split"] == "dev"}
    assert test_carriers and not (test_carriers & dev_carriers)


def test_test_hash_is_deterministic(tmp_path):
    a = generate(tmp_path / "a", seed=11, n_carriers=5, per_template=1)
    b = generate(tmp_path / "b", seed=11, n_carriers=5, per_template=1)
    c = generate(tmp_path / "c", seed=12, n_carriers=5, per_template=1)
    assert a["test_hash"] == b["test_hash"] != c["test_hash"]


def test_discrepancy_rate_is_roughly_15_percent(tmp_path):
    m = generate(tmp_path / "d", seed=3, n_carriers=10, per_template=10)
    rate = sum(e["discrepancy"] for e in m["entries"]) / len(m["entries"])
    assert 0.08 < rate < 0.22


def test_n_carriers_below_five_raises():
    with pytest.raises(ValueError):
        split_carriers([f"C{k:02d}" for k in range(1, 4)], random.Random(0))


def test_generate_n_carriers_below_five_raises(tmp_path):
    with pytest.raises(ValueError):
        generate(tmp_path / "too_small", seed=1, n_carriers=4, per_template=1)


def test_manifest_path_is_posix(tiny_dataset):
    manifest = json.loads((tiny_dataset / "manifest.json").read_text())
    for e in manifest["entries"]:
        assert "\\" not in e["path"]


def test_second_generate_without_force_raises(tmp_path):
    out = tmp_path / "e"
    generate(out, seed=1, n_carriers=5, per_template=1)
    with pytest.raises(FileExistsError):
        generate(out, seed=2, n_carriers=5, per_template=1)


def test_second_generate_with_force_succeeds_and_matches_manifest(tmp_path):
    out = tmp_path / "f"
    generate(out, seed=1, n_carriers=5, per_template=1)
    m = generate(out, seed=2, n_carriers=5, per_template=1, force=True)
    on_disk = {str(p.relative_to(out).as_posix()) for p in out.rglob("*.xlsx")}
    assert on_disk == {e["path"] for e in m["entries"]}
