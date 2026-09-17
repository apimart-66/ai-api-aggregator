# Contributing

Useful contributions:

1. A routing pattern (fallback chain, modality router, cost guard) with the failure mode it prevents.
2. A client example for another SDK or language that keeps the same request envelope.
3. Corrections to the catalog: a missing model, a wrong billing unit, or a wrong headline price — include the model id and the source you checked.

Before opening a pull request:

```bash
python tools/catalog.py --from-file your_saved_pricing_page.html   # refresh data/models.json, CATALOG.md, README tables
python tools/check_links.py
python examples/router.py --task image --model gpt-image-2.5-ext --count 10
```

Every APIMart link must be an attributed `go.apimart.ai` short link minted through the promo link API; hand-made tracking parameters fail CI.
