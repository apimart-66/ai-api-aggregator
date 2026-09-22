# AI API Aggregator — One Key, One Base URL, 300+ Models

<!-- conv-kit:v1 -->

<p align="center">
  <img src="assets/badges/price.svg" alt="observed unit price"> <img src="assets/badges/billing.svg" alt="billing model"> <img src="assets/badges/compat.svg" alt="OpenAI-compatible endpoint">
</p>

> **image2.5 from $0.0085 per 1K image** · Seedance 2.5 from $0.0961/sec · cached LLM input from $0.40/M — one OpenAI-compatible endpoint at `https://api.apimart.ai/v1`, no monthly plan required. *(observed 2026-09-17)*

**[Get an API key](https://go.apimart.ai/k-eca2fa)** · **[Live pricing](https://go.apimart.ai/k-07eb41)** · **[Model page](https://go.apimart.ai/k-e73309)**

**Why teams route through APIMart**

- **One key, entire catalog.** The same `https://api.apimart.ai/v1` base URL and `Authorization` header reach the whole catalog behind one key and 300+ other image, video and language models — switch the `model` field, not your client.
- **$1 minimum, pay as you go.** No subscription and no prepaid plan to size up front: top up from $1 and spend it on calls. There is no free quota to burn through first, so the price in this table is the price you pay.
- **The charge comes back in the response.** Every call reports the amount billed (`cost` / `credits_cost`), so a spend number is read per call instead of guessed at month end.
- **Async by design.** Submit, take the `task_id`, poll `GET /v1/tasks/{id}` — batching and retries are ordinary queue work, not a bespoke integration.

<!-- /conv-kit:v1 -->

An **AI API aggregator** concentrates access: one credential, one base URL, one billing surface, many models.
This repository is the working companion to that idea — a machine-readable model catalog, the request shapes for each
modality behind the same key, and the routing patterns that keep a pipeline from double-charging or silently failing over.

<!-- snapshot:date -->2026-09-22<!-- /snapshot:date -->

## What is in here

| File | Why it exists |
| --- | --- |
| [`data/models.json`](data/models.json) | the full catalog: model id, display name, alias, modality, billing unit, prices |
| [`CATALOG.md`](CATALOG.md) | the same catalog as a readable table, regenerated in CI |
| [`tools/catalog.py`](tools/catalog.py) | builds the catalog from the public pricing payload — no API key needed |
| [`examples/router.py`](examples/router.py) | routes a task to a model, prints the cost arithmetic, retries safely |
| [`examples/openai_sdk_client.py`](examples/openai_sdk_client.py) | the OpenAI SDK pointed at the aggregator base URL |
| [`examples/curl.sh`](examples/curl.sh) | chat, image and async task polling with plain curl |

## Catalog coverage

<!-- catalog:summary:start -->
| Modality | Models captured | Typical billing unit |
| --- | --- | --- |
| Image | 40 | per delivered image (by resolution) |
| Video | 49 | per second of output (by resolution) |
| Text / multimodal | 187 | per million tokens (input / cached / output) |
| Other (per call, per track) | 6 | fixed unit per call |
<!-- catalog:summary:end -->

The full list lives in [`CATALOG.md`](CATALOG.md). Headline routes below are the ones most requests land on.

### Image routes

<!-- catalog:image:start -->
| Model id | Route | Headline price | Billing unit |
| --- | --- | --- | --- |
| `gpt-image-2.5-ext` | image2.5 per-image route | $0.0085 | usd_per_image |
| `gemini-3-pro-image-preview` | Nano Banana Pro | $0.03 | usd_per_image |
| `gemini-3.1-flash-image-preview` | Nano Banana 2 | $0.015 | usd_per_image |
| `gemini-2.5-flash-image-preview` | Nano Banana | $0.0125 | usd_per_image |
| `grok-imagine-1.5-apimart` | Grok Image 1.5 | $0.015 | usd_per_image |
| `seedream-4-5` | Seedance 4.5 image route | $0.026 | usd_per_image |
<!-- catalog:image:end -->

### Video routes

<!-- catalog:video:start -->
| Model id | Route | Headline price | Billing unit |
| --- | --- | --- | --- |
| `seedance-2.5` | Seedance 2.5 | $0.216 | usd_per_second |
| `seedance-2.0` | Seedance 2.0 | $0.142 | usd_per_second |
| `seedance-2.0-mini` | Seedance 2.0 mini | $0.0229 | usd_per_second |
| `kling-3.0-turbo` | Kling 3.0 Turbo | $0.1144 | usd_per_second |
<!-- catalog:video:end -->

### Text and multimodal routes

<!-- catalog:token:start -->
| Model id | Route | Headline price | Billing unit |
| --- | --- | --- | --- |
| `gpt-5.5` | GPT-5.5 | $4.00 | usd_per_million_tokens |
| `claude-opus-5` | Claude Opus 5 | $4.00 | usd_per_million_tokens |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 | $2.40 | usd_per_million_tokens |
| `deepseek-v4-pro` | DeepSeek V4 Pro | $1.03 | usd_per_million_tokens |
| `deepseek-v4-flash` | DeepSeek V4 Flash | $0.3429 | usd_per_million_tokens |
| `gpt-5-mini` | GPT-5 mini | $0.2 | usd_per_million_tokens |
<!-- catalog:token:end -->

## One key, several request shapes

An aggregator is only useful if the same credential works across modalities. All three shapes below use
`Authorization: Bearer $APIMART_API_KEY` against `https://api.apimart.ai/v1`.

```python
from openai import OpenAI

client = OpenAI(base_url="https://api.apimart.ai/v1", api_key=os.environ["APIMART_API_KEY"])
chat = client.chat.completions.create(model="gpt-5.5", messages=[{"role": "user", "content": "Explain idempotency keys"}])
```

```bash
# image route: submit, then poll the task until completed
curl -sS https://api.apimart.ai/v1/images/generations \
  -H "Authorization: Bearer $APIMART_API_KEY" -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"model":"gpt-image-2.5-ext","version":"flare","prompt":"A pasta dish on a slate table, side light","size":"1:1","resolution":"1K","n":1}'
```

```bash
# task polling returns status, progress, cost and the result URLs
curl -sS https://api.apimart.ai/v1/tasks/task_01EXAMPLE -H "Authorization: Bearer $APIMART_API_KEY"
```

Video routes follow the same envelope with a per-second unit, so a 10-second clip is `rate × 10` on the resolution tier
you asked for.

## Routing patterns that hold up in production

1. **Route by modality, not by brand.** Pick the image route from the image table, the video route from the per-second
   table, and the text route from the token table; comparing them on one axis (price per artefact) avoids nonsense
   comparisons.
2. **Retry with an idempotency key.** `429` and `5xx` are retryable, `400` / `401` / `402` are not; reusing the same
   `Idempotency-Key` collapses a retry into the original task instead of buying a second image.
3. **Poll with backoff, stop on terminal states.** `pending → processing → completed | failed`; schedule the first
   polls a few seconds apart and widen from there.
4. **Log cost per task, not per request.** The task response carries `cost` and `credits_cost`; summing those is the only
   reconciliation that matches the invoice.
5. **Keep a fallback chain per modality.** Same-modality fallback is usually safe; cross-modality fallback is not
   (an edit prompt rarely survives a different vendor's model).

## Aggregator or direct vendor?

| Question | Aggregator | Direct vendor |
| --- | --- | --- |
| Credentials to manage | one key | one per vendor |
| Response envelopes | normalised, with a task model for long jobs | vendor-specific |
| Model choice | swap a string | new integration per vendor |
| Pricing model | mixed units (per image, per second, per token) under one bill | vendor-specific billing |
| Failure modes | one hop to debug, provider quirks can leak through | fewer layers, fewer abstractions |
| Best fit | teams that ship several modalities and want one budget line | single-model products with deep vendor-specific needs |

## Estimate before you spend

```bash
python examples/router.py image --model gpt-image-2.5-ext --count 250
python examples/router.py video --model seedance-2.0-mini --resolution 480P --seconds 8 --count 25
python examples/router.py text  --model claude-opus-5 --input-tokens 400000 --output-tokens 60000
python examples/router.py list --spec image | head
```


<!-- conv-kit:v1:scale -->
### What that costs at scale

| Workload | Cost at the observed rates |
| --- | --- |
| 1,000 GPT Image 2.5 renders (1K) | $8.50 |
| 10 minutes of Seedance 2.5 at 480P (600s) | $57.66 |
| 1M cached LLM input tokens | from $0.40 |

Linear at the observed per-unit rate, no volume discount assumed. Snapshot 2026-09-17; re-check the live table before committing a budget.
<!-- /conv-kit:v1:scale -->

<!-- conv-kit:v1:fix -->
## First-call troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `401` / `invalid api key` | key missing, truncated, or a stray newline pasted into the header | Re-copy it from the console; the header is `Authorization: Bearer $APIMART_API_KEY` |
| balance / credit error | the account has no balance | Top up from $1 in the console — there is no free quota to fall back on |
| `429` | concurrent requests on one key | Back off, then retry the same request with the same `Idempotency-Key` |
| `400` / model not found | wrong route for the id: the per-unit alias needs its `version`, the official id must not send one | Copy the exact `model` value from the route table above |
| task ends `failed` | prompt rejected by the filter, or a reference image URL expired | Re-submit with a **new** `Idempotency-Key` and re-host the reference image |
| result URL stops working | result links expire | Download the file as soon as the task reports `completed` |
<!-- /conv-kit:v1:fix -->

## FAQ

**What counts as an AI API aggregator?**
A single gateway that resells access to many models behind one key, one base URL and one bill. It usually normalises the
request envelope, adds a task model for long-running jobs, and hides provider-specific endpoints.

**Does aggregating change the models' output?**
Generation happens upstream, so quality comes from the model. What changes is the parameter surface (each model accepts a
slightly different subset), the safety layer, and the response envelope — pin the response version header and verify one
paid request per model.

**How do I stop a retry from billing twice?**
Send `Idempotency-Key` on submit and reuse the identical body when retrying. Without it, a timeout plus a retry is two
generations, not one.

**Which modality should I benchmark first?**
Whichever dominates the bill. In practice image and video batches dominate flat-rate spend, while text workloads dominate
volume — the catalog lists the billing unit for every route so you can sort by the unit you actually pay in.

## Related searches

- `ai api aggregator`
- `unified ai api`
- `ai api gateway`
- `one api key many models`
- `openai compatible api`
- `ai api pricing comparison`
- `llm api comparison`

<!-- conv-kit:v1:cta -->
---

**Start with $1.** [Get an API key](https://go.apimart.ai/k-eca2fa) → [check live pricing](https://go.apimart.ai/k-07eb41) → [open the whole catalog behind one key in the model library](https://go.apimart.ai/k-e73309). The first call is three steps: submit, poll `task_id`, read the charged amount off the response.
<!-- /conv-kit:v1:cta -->

## Attributed links (how this repository is measured)

| Purpose | Attributed link | Target |
| --- | --- | --- |
| Browse the model catalog | <https://go.apimart.ai/k-e73309> | `apimart.ai/model` |
| Current pricing page | <https://go.apimart.ai/k-07eb41> | `apimart.ai/pricing` |
| Get an API key | <https://go.apimart.ai/k-eca2fa> | `apimart.ai/keys` |

Outbound APIMart links are minted through the promo link API so traffic from this repository is attributed; hand-made
tracking parameters are rejected by `tools/check_links.py` in CI.

## Disclosure

APIMart is the aggregator documented here; this repository is published to document it, not to claim official status.
Model names, prices and documentation belong to their respective owners, and relayed `ext` routes are third-party relay
endpoints rather than first-party vendor endpoints. Snapshot date: <!-- snapshot:date -->2026-09-22<!-- /snapshot:date -->.

## Repository map

```text
README.md      aggregator overview, catalog summary, routing patterns, FAQ
CATALOG.md     full model catalog (regenerated by CI)
data/models.json  machine-readable catalog
tools/catalog.py  builds the catalog from the public pricing payload
tools/check_links.py  attribution + data guard
examples/      router, OpenAI SDK client, curl recipes
.github/workflows/  daily catalog refresh + validation
```

## License

MIT — see [LICENSE](LICENSE).
