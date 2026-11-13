from services import agreement


def test_perfect_agreement_is_kappa_one():
    labels = ["VULN", "MALWARE", "OTHER", "RESEARCH"]
    assert agreement.cohen_kappa(labels, labels) == 1.0


def test_known_kappa_example():
    # po = 0.75, pe = 0.5, kappa = 0.5
    left = ["1", "1", "0", "0"]
    right = ["1", "0", "0", "0"]
    assert round(agreement.cohen_kappa(left, right), 3) == 0.5


def test_total_disagreement_is_negative():
    left = ["A", "A", "B", "B"]
    right = ["B", "B", "A", "A"]
    assert agreement.cohen_kappa(left, right) < 0


def test_degenerate_all_same_label_is_zero_not_crash():
    assert agreement.cohen_kappa(["A", "A"], ["A", "A"]) == 0.0


def test_describe_reports_confusion_and_per_class():
    left = ["VULN", "MALWARE", "OTHER"]
    right = ["VULN", "MALWARE", "RESEARCH"]
    stats = agreement.describe(left, right, ["VULN", "MALWARE", "RESEARCH", "OTHER"])
    assert stats["rows"] == 3
    assert stats["agree"] == 2
    assert stats["confusion"]["OTHER"]["RESEARCH"] == 1
    assert stats["per_class_kappa"]["VULN"] == 1.0
