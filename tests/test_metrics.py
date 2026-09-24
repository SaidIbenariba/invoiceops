from invoiceops.evals.metrics import accuracy, false_map_rate, file_counts, refusal_rate
from invoiceops.mapping import MappingResult

RESULT = MappingResult(
    header_row=0,
    headers=["a", "b", "c"],
    assignments={0: "amount", 1: "currency"},
    scores={0: 1.0, 1: 0.9},
    margins={0: 1.0, 1: 0.5},
    unmapped_required=[],
)
TRUTH = ["amount", None, "currency"]


def test_counts_for_emitted_record_with_a_wrong_map():
    c = file_counts(RESULT, TRUTH, refused=False)
    assert c.tolist() == [1, 2, 1, 2, 1, 0, 1]  # correct, n_target, wrong, n_mapped, silent, refused, n_files
    assert accuracy(c) == 0.5
    assert false_map_rate(c) == 0.5
    assert refusal_rate(c) == 0.0


def test_refused_record_is_never_silent():
    c = file_counts(RESULT, TRUTH, refused=True)
    assert c[4] == 0 and c[5] == 1
