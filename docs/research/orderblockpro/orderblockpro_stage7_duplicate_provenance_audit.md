# OrderBlockPro — Stage 7 Duplicate Provenance Audit

## Result

The newest screenshot batch contains **8 files and 0 new unique images**.

All eight files are byte-for-byte duplicates of screenshots already present in the analysis workspace. They should therefore **not** be added as new reaction events, not be treated as independent confirmations, and not increase the sample size.

## Current screenshot integrity summary

- Image files currently present in workspace: **38**
- Unique image hashes: **29**
- Duplicate hash groups: **7**
- New files in this batch: **8**
- New unique evidence from this batch: **0**

## Important research consequence

The current event dataset should remain unchanged. Duplicate screenshots can be useful for provenance and source tracking, but counting them more than once would bias:

- apparent setup frequency,
- apparent confirmation count,
- reaction success frequency,
- confidence scoring,
- any later machine-learning or statistical model.

## Duplicate groups involving this batch

- `cachedImage(20260926-012624).png` → duplicate of: cachedImage(1).png; cachedImage(2).png; cachedImage(20260926-012629).png

- `cachedImage(20260926-012629).png` → duplicate of: cachedImage(20260926-012624).png; cachedImage(1).png; cachedImage(2).png

- `cachedImage(20260926-012613).png` → duplicate of: cachedImage.png

- `Image_10-09-2026_at_11.43(2).jpeg` → duplicate of: Image_10-09-2026_at_11.43.jpeg

- `cachedMedia(20260926-012600).jpeg` → duplicate of: cachedMedia(4).jpeg

- `Image_02-09-2026_at_02.08(2).jpeg` → duplicate of: Image_02-09-2026_at_02.08.jpeg

- `Image_02-09-2026_at_10.09(2).jpeg` → duplicate of: Image_02-09-2026_at_10.09.jpeg

- `cachedMedia(20260926-012543).jpeg` → duplicate of: cachedMedia.jpeg

## Dataset rule going forward

Every screenshot and extracted video frame should receive a content hash before being admitted to the event dataset.

Recommended ingestion rule:

```text
new asset
  → compute SHA-256
  → if hash already exists:
       attach as provenance only
       do NOT create a new event
    else:
       inspect and classify
       create event only if it contributes a distinct market episode or distinct structural state
```

This keeps the research sample clean and prevents curated reposts from masquerading as independent evidence.
