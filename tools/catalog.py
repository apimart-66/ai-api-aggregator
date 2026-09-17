#!/usr/bin/env python3
"""Build the unified model catalog from the public pricing payload.

Outputs:
    data/models.json    machine-readable catalog (id, name, alias, modality, billing unit, prices)
    CATALOG.md          human-readable catalog grouped by modality
    README.md           refreshes the summary and headline tables between marker blocks

Usage:
    python tools/catalog.py                 # fetch live, regenerate everything
    python tools/catalog.py --from-file X   # parse a saved pricing page
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "models.json"
CATALOG = ROOT / "CATALOG.md"
README = ROOT / "README.md"
PAGE = "https://apimart.ai/en/pricing"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36")

HEADLINE = {
    "image": [("gpt-image-2.5-ext", "image2.5 per-image route"),
              ("gemini-3-pro-image-preview", "Nano Banana Pro"),
              ("gemini-3.1-flash-image-preview", "Nano Banana 2"),
              ("gemini-2.5-flash-image-preview", "Nano Banana"),
              ("grok-imagine-1.5-apimart", "Grok Image 1.5"),
              ("seedream-4-5", "Seedance 4.5 image route")],
    "second": [("seedance-2.5", "Seedance 2.5"), ("seedance-2.0", "Seedance 2.0"),
               ("seedance-2.0-mini", "Seedance 2.0 mini"), ("kling-3.0-turbo", "Kling 3.0 Turbo")],
    "token": [("gpt-5.5", "GPT-5.5"), ("gpt-5.5-pro", "GPT-5.5 Pro"), ("claude-opus-5", "Claude Opus 5"),
              ("claude-sonnet-4-6", "Claude Sonnet 4.6"), ("deepseek-v4-pro", "DeepSeek V4 Pro"),
              ("deepseek-v4-flash", "DeepSeek V4 Flash"), ("gpt-5-mini", "GPT-5 mini")],
}


def fetch(url: str = PAGE) -> str:
    cp = subprocess.run(["curl", "-sL", "-m", "45", "-H", f"User-Agent: {UA}", url], capture_output=True, text=True)
    if not cp.stdout:
        raise SystemExit("failed to fetch the pricing page")
    return cp.stdout


def rsc_blob(html: str) -> str:
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)
    return "".join(c.encode().decode("unicode_escape", errors="ignore") for c in chunks)


def balanced(text: str) -> list[str]:
    out, i, n = [], 0, len(text)
    while True:
        i = text.find('{"id":"', i)
        if i < 0:
            return out
        depth, j = 0, i
        while j < n:
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(text[i:j + 1])
        i = j + 1


def parse(blob: str) -> list[dict]:
    models = []
    for raw in balanced(blob):
        try:
            rec = json.loads(raw)
        except Exception:
            continue
        if not isinstance(rec, dict) or not rec.get("id"):
            continue
        fixed, pricing = rec.get("fixed_prices") or {}, rec.get("pricing") or {}
        entry = {"id": rec["id"], "name": rec.get("name"), "alias": rec.get("alias"),
                 "specification": rec.get("specification")}
        if fixed.get("items"):
            entry["unit"] = fixed.get("unit")
            entry["prices"] = {i["key"]: {"list": i.get("original_price"), "effective": i.get("after_discount")}
                               for i in fixed["items"]}
        elif pricing.get("rates"):
            entry["unit"] = pricing.get("unit")
            entry["prices"] = {"list": pricing.get("rates"), "effective": pricing.get("effective_rates")}
            entry["billing_type"] = pricing.get("billing_type")
        else:
            continue
        models.append(entry)
    return models


def money(v) -> str:
    if v in (None, ""):
        return "—"
    v = float(v)
    if v == 0:
        return "free"
    if v < 0.01:
        return f"${v:.6f}".rstrip("0").rstrip(".")
    if v < 1:
        return f"${v:.4f}".rstrip("0").rstrip(".")
    return f"${v:,.2f}"


def cell(model: dict) -> str:
    prices = model.get("prices") or {}
    flat = {k: (v.get("effective") if isinstance(v, dict) else v) for k, v in prices.items()}
    for key in ("default", "1K", "720P", "480P", "1080P", "flare@1K"):
        if key in flat:
            return money(flat[key])
    if "effective" in prices and isinstance(prices["effective"], dict):
        return money(prices["effective"].get("input"))
    return "—"


def headline_table(models: dict, spec: str) -> str:
    rows = ["| Model id | Route | Headline price | Billing unit |", "| --- | --- | --- | --- |"]
    for mid, label in HEADLINE.get(spec, []):
        m = models.get(mid)
        if not m:
            continue
        rows.append(f"| `{mid}` | {label} | {cell(m)} | {m.get('unit') or '—'} |")
    return "\n".join(rows)


def catalog_md(models: list[dict], snapshot: dict) -> str:
    lines = ["# Unified model catalog", "",
             f"{len(models)} models captured from `{PAGE}` on {snapshot['extracted_at']}.",
             "", "| Model id | Display name | Alias | Modality | Billing unit | Headline |",
             "| --- | --- | --- | --- | --- | --- |"]
    for m in sorted(models, key=lambda x: ((x.get("specification") or ""), x["id"])):
        lines.append(f"| `{m['id']}` | {m.get('name') or ''} | {m.get('alias') or '—'} | "
                     f"{m.get('specification') or '—'} | {m.get('unit') or '—'} | {cell(m)} |")
    lines += ["", "Regenerate with `python tools/catalog.py`. Effective prices include the default group discount; "
              "list prices are in `data/models.json`.", ""]
    return "\n".join(lines)


def replace_block(text: str, name: str, body: str) -> str:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"marker block {name} missing in README")
    return pattern.sub(f"{start}\n{body}\n{end}", text)


def main() -> None:
    ap = argparse.ArgumentParser(description="Rebuild the unified model catalog")
    ap.add_argument("--from-file")
    ap.add_argument("--check", action="store_true", help="exit 1 when the catalog changed")
    args = ap.parse_args()

    html = pathlib.Path(args.from_file).read_text(errors="ignore") if args.from_file else fetch()
    models = parse(rsc_blob(html))
    by_id = {m["id"]: m for m in models}
    counts: dict[str, int] = {}
    for m in models:
        counts[m.get("specification") or "other"] = counts.get(m.get("specification") or "other", 0) + 1
    snapshot = {"source": PAGE,
                "method": "React Server Component payload of the public pricing page (no API key required)",
                "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "model_count": len(models), "specification_counts": counts, "models": models}
    new_json = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    old_json = DATA.read_text() if DATA.exists() else ""
    if args.check:
        print("catalog changed" if new_json != old_json else "catalog unchanged")
        sys.exit(1 if new_json != old_json else 0)

    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(new_json)
    CATALOG.write_text(catalog_md(models, snapshot))

    readme = README.read_text()
    summary = ["| Modality | Models captured | Typical billing unit |", "| --- | --- | --- |",
               f"| Image | {counts.get('image', 0)} | per delivered image (by resolution) |",
               f"| Video | {counts.get('second', 0)} | per second of output (by resolution) |",
               f"| Text / multimodal | {counts.get('token', 0)} | per million tokens (input / cached / output) |",
               f"| Other (per call, per track) | {counts.get('times', 0)} | fixed unit per call |"]
    readme = replace_block(readme, "catalog:summary", "\n".join(summary))
    readme = replace_block(readme, "catalog:image", headline_table(by_id, "image"))
    readme = replace_block(readme, "catalog:video", headline_table(by_id, "second"))
    readme = replace_block(readme, "catalog:token", headline_table(by_id, "token"))
    readme = re.sub(r"<!-- snapshot:date -->[^<]*<!-- /snapshot:date -->",
                    f"<!-- snapshot:date -->{snapshot['extracted_at'][:10]}<!-- /snapshot:date -->", readme)
    README.write_text(readme)
    print(f"catalog rebuilt: {len(models)} models {counts}")


if __name__ == "__main__":
    main()
