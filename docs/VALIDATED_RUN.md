# Validated public run

FaceProof completed a public Base Sepolia run on September 3, 2026. The source code did not contain the selected social post or the search results before the run.

## Input

The run used a portrait of Sundar Pichai by Lukasz Kobus for the European Commission. Wikimedia Commons provides the image under the [CC BY 4.0 license](https://commons.wikimedia.org/wiki/File:Sundar_Pichai_(2023)_cropped.jpg).

The input image remains outside Git. Run `./scripts/demo-input.sh` to download the reviewed file and verify its SHA 256 value.

## Live search

FaceProof sent two new images to SerpApi Google Lens with caching disabled.

1. The face crop search returned 68 visual results and 11 social results. Its provider search ID was `6a98e718f9c5e9dc7bac23c2`.
2. The full image search returned 77 visual results and 23 social results. Its provider search ID was `6a98e71d3d34ddd56c9ee803`.

FaceProof selected a [Stanford Facebook post about Sundar Pichai](https://www.facebook.com/Stanford/posts/sundar-pichai-ceo-of-google-and-alphabet-inc-and-a-stanford-alum-will-return-to-/1363544992482875/). The local SFace comparison produced a cosine similarity of `0.954334`. The required threshold was `0.45`.

## Evidence

FaceProof created deterministic evidence JSON for the selected result. The SHA 256 fingerprint was:

```text
c759628e8dd16e3f5bb397e52f0db4746739dcb8694dccd05de401a753053a0e
```

The local evidence files remain outside Git because they contain the collected search record. The recording guide explains how to download them from the running application.

## Public proof

FaceProof signed a zero value transaction with the disposable test wallet. The transaction contains the FaceProof format marker and the 32 byte evidence fingerprint.

Network: `Base Sepolia`

Chain ID: `84532`

Block: `46336968`

Transaction: [`0x7053f316d2955ce978245318450dcf2b94c30702a71bd7d7c966eb687a1d6975`](https://sepolia.basescan.org/tx/0x7053f316d2955ce978245318450dcf2b94c30702a71bd7d7c966eb687a1d6975)

Wallet: [`0xEF84548E72A17A1B6B4783D4a762e2442302896A`](https://sepolia.basescan.org/address/0xEF84548E72A17A1B6B4783D4a762e2442302896A)

## Repeat verification

The application read the confirmed transaction through the public Base Sepolia connection and compared its data with the expected FaceProof marker and evidence fingerprint. Verification passed.

A second command loaded the saved evidence file, calculated its fingerprint again, and checked the public transaction independently. This verification also passed.

```bash
uv run faceproof verify-file evidence.json 0x7053f316d2955ce978245318450dcf2b94c30702a71bd7d7c966eb687a1d6975
```

Any change to a protected evidence field produces a different fingerprint and causes verification to fail.
