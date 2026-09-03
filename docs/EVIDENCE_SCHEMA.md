# Evidence schema

Schema identifier: `faceproof.evidence.v1`

The readable and canonical files contain the same fields. The canonical file is the exact SHA-256 input.

## Top level fields

| Field | Meaning |
|---|---|
| `schema_version` | Fixed schema and payload interpretation identifier |
| `collected_at` | UTC time when the evidence manifest was created |
| `input` | Fingerprint and model facts for the submitted image |
| `search` | Provider and fresh search provenance |
| `discovered_content` | Public post and retrieved media facts |
| `face_match` | Comparison metric, score, threshold, and decision |
| `privacy` | Explicit statement of data excluded from storage and the chain |

## Input

| Field | Type | Meaning |
|---|---|---|
| `sha256` | 64 character hex string | SHA-256 of the normalized input JPEG |
| `crop_sha256` | 64 character hex string | SHA-256 of the contextual face crop sent to visual search |
| `faces_detected` | Integer | Number of faces encoded in the input |
| `selected_box` | Four integers | Selected face position as x, y, width, and height |
| `detection_score` | Number | YuNet detection score rounded to six places |
| `embedding_dimensions` | Integer | Number of values in the in-memory face embedding |
| `detector_model` | String | Pinned detector model name |
| `recognizer_model` | String | Pinned recognition model name |

The embedding and raw image are not present.

## Search

`provider` is `SerpApi Google Lens`. `live_search` and `cache_disabled` are always `true`. `queries` contains the crop and full image traces. Each trace records the query kind, provider name, returned search identifier when available, provider status, provider creation time when available, total result count, and accepted social result count.

## Discovered content

| Field | Meaning |
|---|---|
| `platform` | Provider supplied source or social platform name |
| `post_url` | Public result URL returned by the live search |
| `title` | Provider supplied result title |
| `source_media_url` | Media or thumbnail URL used for local comparison |
| `retrieved_media_sha256` | SHA-256 of the normalized locally reviewed candidate image |

## Face match

The metric is `cosine_similarity`. The score is rounded to six decimal places. The threshold is the configured decision boundary. `decision` is present only as `match` because an evidence manifest is not created when no candidate passes. `exact_visual_match_reported` preserves the provider signal without treating it as the local decision. `query_kind` identifies which of the two live searches found the selected result.

## Privacy

The manifest states that no embedding and no raw image were put onchain. The declared blockchain payload is `schema marker and SHA-256 fingerprint only`.

## Canonicalization

1. Validate the readable object against the strict schema. Unknown fields, malformed SHA-256 values, out of range scores, and invalid counts are rejected.
2. Normalize every string to Unicode NFC.
3. Sort object keys.
4. Encode as UTF-8 JSON.
5. Use no optional whitespace.
6. Reject NaN and infinite numeric values.
7. Calculate SHA-256 over the resulting bytes.

Example command:

```bash
uv run faceproof hash-evidence .context/runs/RUN_ID/evidence.json
```

The output must equal the `evidence_id` in the saved run and the 32 byte digest after the `FACEPROOF` version prefix in the transaction data.
