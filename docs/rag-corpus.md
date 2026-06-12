# Kimi Report RAG Corpus

The source report is transformed into a reproducible, page-cited corpus under
`data/rag/kimi-world-cup-report/`.

## Artifacts

- `manifest.json`: source identity, SHA-256, generation time, and chunk policy.
- `pages.jsonl`: one complete record per PDF page.
- `chunks.jsonl`: retrieval-ready, page-bounded semantic chunks.
- `sections.json`: chapter and detected section navigation.
- `corpus.md`: human-readable full extraction with page headings.

Each chunk includes:

- stable `id` and `source_id`
- `page_start`, `page_end`, and ready-to-display `citation`
- inferred `chapter` and `section`
- thematic `keywords` and `content_type`
- extracted `text`
- source PDF SHA-256 for lineage

Quantitative statements remain report assertions until independently verified.
Retrieval consumers should preserve the citation and verification status when
turning a chunk into an answer or model feature.

## Regenerate

```bash
python3 scripts/build_report_rag.py \
  --source /Users/jiaqi/Downloads/Kimi_2026_World_Cup_Report.pdf
python3 scripts/validate_rag_corpus.py
```

The builder requires `pypdf`. It deliberately keeps chunks within a single PDF
page so every retrieved claim has an unambiguous citation.

## Local Retrieval Check

```bash
python3 scripts/search_report_rag.py "WBGT 旅行疲劳"
python3 scripts/search_report_rag.py "Brier 校准 模型漂移" --json
```

This lexical search is a smoke test, not the production retriever. For vector
RAG, embed the `text` field and store the remaining fields as filterable
metadata. A useful retrieval flow is:

1. Filter by chapter, keyword, content type, or report date when the question
   supplies a clear scope.
2. Retrieve semantically similar chunks.
3. Rerank for provenance, uncertainty, and calibration content.
4. Return the chunk citation with every report-derived claim.
5. Mark claims as source assertions unless another source verifies them.

For model-design questions, prefer chunks tagged `data_provenance`,
`uncertainty`, `calibration`, or `dynamic_update`.
