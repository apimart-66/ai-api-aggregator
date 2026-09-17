#!/usr/bin/env python3
"""Route a task to a model from the local catalog, print the cost arithmetic, and show safe retries.

    python examples/router.py --task image --model gpt-image-2.5-ext --count 250
    python examples/router.py --task video --model seedance-2.0-mini --resolution 480P --seconds 8 --count 25
    python examples/router.py --task text  --model claude-opus-5 --input-tokens 400000 --output-tokens 60000
    python examples/router.py --list --spec image
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "models.json"
BASE = "https://api.apimart.ai/v1"


def load() -> dict[str, dict]:
    return {m["id"]: m for m in json.loads(DATA.read_text())["models"]}


def price(model: dict, key: str, variant: str = "flare") -> float:
    prices = model.get("prices") or {}
    for candidate in (f"{variant}@{key}", key, "default"):
        if candidate in prices:
            entry = prices[candidate]
            return float(entry.get("effective", entry.get("list")) if isinstance(entry, dict) else entry)
    raise SystemExit(f"no price for {key} on {model['id']}; available: {sorted(prices)}")


def submit_headers(idempotency_key: str) -> dict:
    return {
        "Authorization": "Bearer $APIMART_API_KEY",   # export APIMART_API_KEY=... before running for real
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key,
        "X-APIMart-Response-Version": "2026-07-27",
    }


def poll_plan() -> list[int]:
    """Backoff schedule for task polling: quick first checks, then widen."""
    return [1, 2, 3, 5, 8, 10, 10, 10]


def main() -> None:
    ap = argparse.ArgumentParser(description="Catalog-backed router and cost estimator")
    sub = ap.add_subparsers(dest="mode", required=False)
    for name in ("image", "video", "text"):
        p = sub.add_parser(name)
        p.add_argument("--model", required=True)
        p.add_argument("--count", type=int, default=1)
        if name == "image":
            p.add_argument("--resolution", default="1K")
            p.add_argument("--variant", default="flare")
        elif name == "video":
            p.add_argument("--resolution", default="720P")
            p.add_argument("--seconds", type=float, default=5)
        else:
            p.add_argument("--input-tokens", type=int, required=True)
            p.add_argument("--output-tokens", type=int, required=True)
    p_list = sub.add_parser("list")
    p_list.add_argument("--spec")
    p_list.add_argument("--grep")
    args = ap.parse_args()
    if not args.mode:
        ap.print_help()
        return

    models = load()
    if args.mode == "list":
        for mid, m in sorted(models.items()):
            if args.spec and m.get("specification") != args.spec:
                continue
            if args.grep and args.grep.lower() not in mid.lower():
                continue
            print(f"{mid:44} {m.get('specification'):8} {m.get('unit')}")
        return

    if args.model not in models:
        raise SystemExit(f"unknown model id {args.model!r}; try: python examples/router.py list --grep {args.model.split('-')[0]}")
    model = models[args.model]

    if args.mode == "image":
        unit = price(model, args.resolution, args.variant)
        print(f"[route] image -> {args.model} @ {args.resolution}")
        print(f"[cost ] ${unit:.4f}/image x {args.count} = ${unit * args.count:,.2f}")
    elif args.mode == "video":
        unit = price(model, args.resolution)
        total = unit * args.seconds * args.count
        print(f"[route] video -> {args.model} @ {args.resolution}")
        print(f"[cost ] ${unit:.4f}/second x {args.seconds}s x {args.count} = ${total:,.2f}")
    else:
        eff = (model.get("prices") or {}).get("effective", {})
        cost_in = args.input_tokens / 1_000_000 * float(eff.get("input", 0))
        cost_out = args.output_tokens / 1_000_000 * float(eff.get("output", 0))
        print(f"[route] text -> {args.model}")
        print(f"[cost ] input ${cost_in:.4f} + output ${cost_out:.4f} = ${cost_in + cost_out:,.4f}")

    key = str(uuid.uuid4())
    print("[retry] reuse this idempotency key on any retry:", key)
    print("[poll ] schedule (seconds):", poll_plan())
    print("[note ] POST", f"{BASE}/{'images/generations' if args.mode != 'text' else 'chat/completions'}",
          "| headers:", ", ".join(submit_headers(key)))
    print("[note ] sum `cost` from completed tasks for reconciliation; failed tasks are not billable images")


if __name__ == "__main__":
    main()
