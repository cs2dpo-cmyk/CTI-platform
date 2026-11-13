#!/usr/bin/env python3
"""Rebuild the corpus from the three publishers.

Pipeline: collect listing items -> fetch each article -> clean text -> cluster
per region (K chosen by silhouette) -> classify per article -> write the CSVs
the platform reads.

Bodies are cached under data/.cache so a re-run does not hammer the publishers.
Run with the research virtualenv (it has requests / bs4 / jieba / sklearn):

    python tools/build_corpus.py --thn 100 --ithome 50 --twcert 50
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"
CACHE = DATA / ".cache"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SESSION = requests.Session()
SESSION.headers.update(UA)

from services import classify  # noqa: E402


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #


def fetch(url: str, *, retries: int = 3, cache: bool = True) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    path = CACHE / f"{key}.html"
    if cache and path.exists() and path.stat().st_size > 500:
        return path.read_text(encoding="utf-8", errors="replace")
    last = None
    for attempt in range(retries):
        try:
            response = SESSION.get(url, timeout=30)
            if response.status_code == 200:
                if cache:
                    path.write_text(response.text, encoding="utf-8")
                return response.text
            last = f"HTTP {response.status_code}"
        except Exception as error:  # network hiccup: retry with backoff
            last = f"{type(error).__name__}: {error}"
        time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


# --------------------------------------------------------------------------- #
# Listing collectors
# --------------------------------------------------------------------------- #


def collect_thn(limit: int) -> list[dict[str, str]]:
    feed = json.loads(fetch("https://thehackernews.com/feeds/posts/default?alt=json&max-results=200"))
    items = []
    for entry in feed.get("feed", {}).get("entry", []):
        link = next((l["href"] for l in entry.get("link", []) if l.get("rel") == "alternate"), "")
        title = entry.get("title", {}).get("$t", "").strip()
        stamp = entry.get("published", {}).get("$t", "")[:10]
        if title and link and stamp:
            # The Blogger feed still hands out http:// links.
            link = link.replace("http://thehackernews.com", "https://thehackernews.com")
            items.append({"title": title, "url": link, "date": stamp, "source": "THN", "lang": "en"})
        if len(items) >= limit:
            break
    return items


def collect_twcert(pages: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for page in range(1, pages + 1):
        suffix = "" if page == 1 else f"-{page}-20"
        html = fetch(f"https://www.twcert.org.tw/tw/lp-104-1{suffix}.html")
        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if "cp-104" not in href:
                continue
            text = anchor.get_text(" ", strip=True)
            match = re.search(r"(\d{4}-\d{2}-\d{2})\s*$", text)
            if not match:
                continue
            title = re.sub(r"^\d+\s+", "", text[: match.start()]).strip()
            url = href if href.startswith("http") else "https://www.twcert.org.tw" + href
            if title and url not in seen:
                seen.add(url)
                items.append({"title": title, "url": url, "date": match.group(1),
                              "source": "TWCERT", "lang": "zh"})
        time.sleep(0.4)
    return items


def collect_ithome(limit: int, max_pages: int = 12) -> list[dict[str, str]]:
    """Listing pages link to the same article several times (thumbnail, title).

    Keep the shortest anchor text per URL -- that is the headline -- and walk up
    the DOM until the date is found, instead of trusting the first anchor.
    """
    found: dict[str, dict[str, str]] = {}
    for page in range(1, max_pages + 1):
        html = fetch(f"https://www.ithome.com.tw/news?page={page}")
        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if not re.fullmatch(r"/news/\d+", href):
                continue
            url = "https://www.ithome.com.tw" + href
            title = anchor.get_text(" ", strip=True)
            if len(title) < 8:
                continue
            existing = found.get(url)
            if existing and len(existing["title"]) <= len(title):
                continue
            node = anchor
            date = ""
            for _ in range(7):
                node = node.parent
                if node is None:
                    break
                match = re.search(r"(\d{4}-\d{2}-\d{2})", node.get_text(" ", strip=True))
                if match:
                    date = match.group(1)
                    break
            if not date:
                continue
            found[url] = {"title": title, "url": url, "date": date,
                          "source": "iThome", "lang": "zh"}
        if len(found) >= limit:
            break
        time.sleep(0.4)
    return list(found.values())[:limit]


# --------------------------------------------------------------------------- #
# Article body
# --------------------------------------------------------------------------- #


def article_body(url: str, source: str) -> str:
    try:
        html = fetch(url)
    except Exception:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    if source == "THN":
        node = soup.select_one("div.articlebody")
    elif source == "iThome":
        node = soup.select_one("article div.content") or soup.select_one("div.content")
    else:
        node = soup.select_one("section.cp")
    if node is None:
        return ""
    for junk in node.select("script, style, figure, .ad, .related"):
        junk.decompose()
    return node.get_text(" ", strip=True)


def clean_text(text: str, lang: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    if lang == "zh":
        import jieba

        text = text.lower()
        text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
        tokens = [token.strip() for token in jieba.cut(text)]
        return " ".join(t for t in tokens if t and not re.fullmatch(r"\W+", t))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(t for t in text.split() if len(t) > 1)


# --------------------------------------------------------------------------- #
# Assemble
# --------------------------------------------------------------------------- #


def read_existing() -> tuple[list[dict], list[dict]]:
    """Keep the rows already published (they anchor the gold-label set)."""
    out = {}
    for region, name in (("taiwan", "Taiwan_security_dataset_with_dates.csv"),
                         ("global", "Global_security_dataset_with_dates.csv")):
        path = DATA / name
        if not path.exists():
            continue
        with io.open(path, encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                row["region"] = region
                row["lang"] = "zh" if region == "taiwan" else "en"
                row["source"] = row.get("platform") or ("THN" if region == "global" else "UNKNOWN")
                out[(region, row["title"])] = row
    return [r for r in out.values() if r["region"] == "taiwan"], [r for r in out.values() if r["region"] == "global"]


def pick(existing: list[dict], candidates: list[dict], total: int, per_source: dict[str, int]) -> list[dict]:
    rows = [dict(row) for row in existing]
    have = {row["source"]: 0 for row in rows}
    for row in rows:
        have[row["source"]] = have.get(row["source"], 0) + 1
    for candidate in candidates:
        source = candidate["source"]
        if have.get(source, 0) >= per_source.get(source, 0):
            continue
        if any(row["title"] == candidate["title"] for row in rows):
            continue
        rows.append(candidate)
        have[source] = have.get(source, 0) + 1
        if len(rows) >= total:
            break
    return rows[:total]


def cluster_region(rows: list[dict], k: int = 3) -> tuple[list[int], int, dict]:
    """K-Means with the thesis' K=3.

    Silhouette on this corpus sits around 0.05-0.06 for every k in 2..5, i.e.
    the vocabulary does not form well-separated groups. Picking the argmax
    would therefore chase noise (it produced a 3-item cluster at k=5), so K=3
    is kept for continuity with the research design and the scores are reported
    as a diagnostic instead.
    """
    texts = [row["cleaned_text"] for row in rows]
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import silhouette_score

    vectorizer = TfidfVectorizer(max_features=1200, min_df=2, token_pattern=r"(?u)\S+")
    matrix = vectorizer.fit_transform(texts)

    labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(matrix)
    scores = {}
    for probe in range(2, 6):
        model = KMeans(n_clusters=probe, random_state=42, n_init=10).fit(matrix)
        scores[probe] = round(float(silhouette_score(matrix, model.labels_, metric="cosine")), 4)
    return [int(x) for x in labels], k, {"k": k, "silhouette": scores.get(k), "by_k": scores}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thn", type=int, default=100)
    parser.add_argument("--ithome", type=int, default=50)
    parser.add_argument("--twcert", type=int, default=50)
    args = parser.parse_args()

    tw_existing, gl_existing = read_existing()

    candidates_tw = collect_twcert(pages=4) + collect_ithome(limit=args.ithome + 15)
    candidates_en = collect_thn(limit=args.thn + 20)

    tw_rows = pick(tw_existing, candidates_tw, args.ithome + args.twcert,
                   {"iThome": args.ithome, "TWCERT": args.twcert})
    en_rows = pick(gl_existing, candidates_en, args.thn, {"THN": args.thn})

    # Existing rows carry "published_at"; freshly scraped ones carry "date".
    for row in tw_rows + en_rows:
        row["published_at"] = row.get("published_at") or row.get("date") or ""
        row["url"] = row.get("url") or row.get("source_url") or ""

    summary = {"sources": {}, "fetched": 0, "empty_bodies": []}
    for label, rows in (("taiwan", tw_rows), ("global", en_rows)):
        for index, row in enumerate(rows, start=1):
            body = article_body(row["url"], row["source"]) if row.get("url") else ""
            if len(body) < 80:
                body = row["title"]
                summary["empty_bodies"].append(row["title"][:60])
            row["cleaned_text"] = clean_text(body, row["lang"])
            summary["fetched"] += 1
            if index % 20 == 0:
                print(f"{label}: {index}/{len(rows)}", flush=True)
            time.sleep(0.25)

    for label, rows in (("taiwan", tw_rows), ("global", en_rows)):
        labels, k, info = cluster_region(rows)
        for row, cluster in zip(rows, labels):
            row["cluster"] = str(cluster)
        summary["sources"][label] = {
            "rows": len(rows), "k": k, "silhouette": info["silhouette"],
            "by_source": {s: sum(1 for r in rows if r["source"] == s)
                          for s in sorted({r["source"] for r in rows})},
            "clusters": {str(c): labels.count(c) for c in sorted(set(labels))},
        }

    fields = ["platform", "title", "cleaned_text", "cluster", "published_at",
              "date_source", "source_url", "date_note"]
    written = {}
    for label, rows, name in (
        ("taiwan", tw_rows, "Taiwan_security_dataset_with_dates.csv"),
        ("global", en_rows, "Global_security_dataset_with_dates.csv"),
    ):
        # Sort before opening the file: a failure here must not truncate the
        # corpus to a header row (that is how the original rows were lost once).
        ordered = sorted(rows, key=lambda r: r["published_at"])
        payload = []
        for row in ordered:
            payload.append({
                "platform": row.get("source") or row.get("platform") or "",
                "title": row["title"],
                "cleaned_text": row["cleaned_text"],
                "cluster": row["cluster"],
                "published_at": row["published_at"],
                "date_source": row.get("date_source") or {
                    "THN": "thehackernews.com", "iThome": "ithome.com.tw",
                    "TWCERT": "twcert.org.tw"}.get(row.get("source"), ""),
                "source_url": row.get("url") or row.get("source_url") or "",
                "date_note": "",
            })
        with io.open(DATA / name, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in payload:
                writer.writerow(row)

        written[name] = len(rows)

    classification = {}
    for row in tw_rows + en_rows:
        # Headline only: the body mentions attacks in every third sentence and
        # would drag almost everything into MALWARE (measured: 88/100 vs 50/100).
        category, _ = classify.classify(row["title"])
        classification[category] = classification.get(category, 0) + 1

    summary["written"] = written
    summary["classification"] = classification
    (DATA / "corpus_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
