#!/usr/bin/env python3
"""Point the official OpenAI SDK at the aggregator: one key, chat + image + streaming.

    export APIMART_API_KEY=sk-...
    python examples/openai_sdk_client.py --prompt "Explain idempotency keys in two sentences"
"""
from __future__ import annotations

import argparse
import os
import uuid

from openai import OpenAI

BASE_URL = os.environ.get("APIMART_BASE_URL", "https://api.apimart.ai/v1")


def main() -> None:
    ap = argparse.ArgumentParser(description="OpenAI SDK against an aggregator base URL")
    ap.add_argument("--prompt", default="Explain idempotency keys in two sentences")
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--image-model", default="gpt-image-2.5-ext")
    ap.add_argument("--image-prompt", default="A ceramic espresso cup on a stone pedestal, soft window light")
    args = ap.parse_args()

    client = OpenAI(base_url=BASE_URL, api_key=os.environ["APIMART_API_KEY"],
                    default_headers={"Idempotency-Key": str(uuid.uuid4())})

    chat = client.chat.completions.create(
        model=args.model,
        messages=[{"role": "user", "content": args.prompt}],
    )
    print("chat:", chat.choices[0].message.content[:400])
    print("usage:", chat.usage.model_dump() if chat.usage else None)

    stream = client.chat.completions.create(
        model=args.model,
        messages=[{"role": "user", "content": "List three retry rules, one per line."}],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()

    # Image routes are asynchronous on the relayed per-image unit: submit, then poll the task id.
    image = client.images.generate(model=args.image_model, prompt=args.image_prompt,
                                   size="1024x1024", n=1, extra_body={"version": "flare", "resolution": "1K"})
    print("image task:", image.model_dump())


if __name__ == "__main__":
    main()
