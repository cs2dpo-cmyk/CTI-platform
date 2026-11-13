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
# Re-labelling pass: did the clarified rules make the two annotators converge?
relabel_a = DATA / "relabel2_labels_round1.csv"
relabel_b = DATA / "relabel2_labels_b.csv"
if relabel_a.exists() and relabel_b.exists():
    ra = {r["id"]: r["label"].strip().upper() for r in rows(relabel_a)}
    rb = {r["id"]: r["label"].strip().upper() for r in rows(relabel_b)}
    shared = sorted(set(ra) & set(rb))
    before = DATA / "holdout2_labels_pre_relabel.csv"
    changed = None
    if before.exists():
        old = {r["id"]: r["label"].strip().upper() for r in rows(before)}
        changed = sum(1 for key in shared if old.get(key) != adj.get(key))
    out["relabel"] = {
        "rows": len(shared),
        "raw": round(sum(1 for key in shared if ra[key] == rb[key]) / len(shared), 3),
        "kappa": round(agreement.cohen_kappa([ra[key] for key in shared], [rb[key] for key in shared]), 3),
        "changed_vs_previous": changed,
    }

(DATA / "holdout2_combined.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
