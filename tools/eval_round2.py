"""Score the classifier against each round-2 label set and record the spread."""
import csv, io, json, sys
from pathlib import Path
sys.path.insert(0, r"C:/dev/cti-platform")
from services import agreement, classify

DATA = Path(r"C:/dev/cti-platform/data")
SHEETS = {
    "annotator_a": DATA / "holdout2_labels_round1.csv",
    "annotator_b": DATA / "holdout2_labels_b.csv",
    "adjudicated": DATA / "holdout2_labels.csv",
}

def rows(path):
    return [r for r in csv.DictReader(io.open(path, encoding="utf-8-sig", newline="")) if r.get("label")]

first = rows(SHEETS["annotator_a"])
titles = {r["id"]: r["title"] for r in first}
model = {key: classify.classify(title)[0] for key, title in titles.items()}

out = {}
for name, path in SHEETS.items():
    labelled = rows(path)
    gold = [r["label"].strip().upper() for r in labelled]
    pred = [model[r["id"]] for r in labelled]
    correct = sum(1 for g, p in zip(gold, pred) if g == p)
    from collections import Counter
    majority = Counter(gold).most_common(1)[0]
    out[name] = {
        "rows": len(labelled),
        "accuracy": round(correct / len(labelled), 3),
        "majority_label": majority[0],
        "majority_accuracy": round(majority[1] / len(labelled), 3),
    }

a = {r["id"]: r["label"].strip().upper() for r in rows(SHEETS["annotator_a"])}
b = {r["id"]: r["label"].strip().upper() for r in rows(SHEETS["annotator_b"])}
adj = {r["id"]: r["label"].strip().upper() for r in rows(SHEETS["adjudicated"])}
ids = sorted(a)
disputes = [k for k in ids if a[k] != b[k]]
out["agreement"] = {
    "raw": round(sum(1 for k in ids if a[k] == b[k]) / len(ids), 3),
    "kappa": round(agreement.cohen_kappa([a[k] for k in ids], [b[k] for k in ids]), 3),
    "disputes": len(disputes),
    "adjudicated_with_model": sum(1 for k in disputes if adj[k] == model[k]),
    "adjudicated_with_a": sum(1 for k in disputes if adj[k] == a[k]),
    "adjudicated_with_b": sum(1 for k in disputes if adj[k] == b[k]),
}
(DATA / "holdout2_combined.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
