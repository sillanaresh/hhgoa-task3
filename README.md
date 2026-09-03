# FaceProof

FaceProof takes a face image, performs a fresh search for public social content, checks candidate faces locally, and records a fingerprint of the selected evidence on Base Sepolia.

It is the complete submission project for HH Goa 2026 Shortlisting Task 3.

> FaceProof shows that a face in two images is similar enough under a stated model and threshold. It does not prove a person's legal identity.

## What the judges can verify

| Task requirement | FaceProof implementation | Visible proof |
|---|---|---|
| Detect and encode a face | OpenCV YuNet detects faces. OpenCV SFace aligns the selected face and creates a 128 value embedding. | The detected face, model names, face count, and completed stage appear in the run. |
| Find a real social post | The detected face crop and full input image each start a new SerpApi Google Lens request with cache disabled. Results are filtered to public social domains. | The original post link, two search traces, and all evaluated candidates remain in the run record. |
| Confirm the match | Every downloadable candidate image is encoded locally and compared with cosine similarity. Results below the configured threshold are rejected. | The selected images, exact score, threshold, and candidate list are shown together. |
| Upload to a blockchain | A SHA-256 fingerprint of canonical evidence JSON is placed in the data field of a zero value Base Sepolia transaction. | The transaction hash, block number, confirmations, and public Basescan link are shown. |
| Verify the blockchain record | FaceProof recomputes the fingerprint, reads the transaction through a public RPC endpoint, and compares the exact payload. | The final stage passes only when the local evidence and public transaction agree. |

## Pipeline

```mermaid
flowchart LR
    A[Face image] --> B[YuNet detection]
    B --> C[SFace embedding]
    C --> D[Two fresh Google Lens searches]
    D --> E[Public social candidates]
    E --> F[Local face comparison]
    F --> G[Canonical evidence JSON]
    G --> H[SHA-256 fingerprint]
    H --> I[Approval]
    I --> J[Base Sepolia transaction]
    J --> K[Read back and verify]
```

The first four stages prepare evidence. Publication is a separate approval step. Only the schema marker and the 32 byte fingerprint are public. Images, face embeddings, the wallet key, and the search key remain offchain.

The default SFace cosine threshold is `0.363`, taken from the [official OpenCV Zoo implementation](https://github.com/opencv/opencv_zoo/blob/main/models/face_recognition_sface/sface.py). It is a configurable model boundary, not an identity probability.

## Cost and accounts

The project can run without spending real money.

- SerpApi currently offers a free plan with 250 searches each month. One FaceProof run normally uses two searches. See the [official pricing page](https://serpapi.com/pricing).
- Base Sepolia is a public test network. Its test ETH is free and has no real monetary value.
- FaceProof creates a disposable wallet file inside `.context`, which Git ignores. It does not install a browser wallet and it does not run a blockchain on your computer.
- A faucet can require an account or sign in. Start from the [official Base faucet list](https://docs.base.org/base-chain/tools/network-faucets) or the [Coinbase Developer Platform faucet](https://portal.cdp.coinbase.com/products/faucet).

Do not send real ETH or any other real asset to the FaceProof wallet.

## Quick start

### Requirements

- macOS or Linux
- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- A SerpApi key
- A small amount of free Base Sepolia test ETH

### 1. Install the project

```bash
git clone https://github.com/sillanaresh/hhgoa-task3.git
cd hhgoa-task3
./scripts/setup.sh
```

The setup script installs locked dependencies, downloads the pinned face models, verifies their SHA-256 values, and creates `.context/secrets.env` when needed.

### 2. Add the live search key

Create a free SerpApi account, then copy the key from the [official key page](https://serpapi.com/manage-api-key). Open `.context/secrets.env` and set:

```dotenv
SERPAPI_API_KEY=your_key_here
```

The file is ignored by Git. Do not put the real key in `.env.example`, a command, a screenshot, an issue, or a commit.

### 3. Create and fund the test wallet

```bash
uv run faceproof wallet-create
```

Copy the printed public address into a Base Sepolia faucet. Request test ETH for that address. The private key stays in `.context/base-sepolia-wallet.json` with owner only file permissions.

Check every dependency:

```bash
uv run faceproof doctor
```

All five checks should say `Ready` or `Reachable` before recording the demo.

For the final recording, run the strict readiness and repository gate together:

```bash
./scripts/preflight.sh
```

### 4. Start the workbench

```bash
./scripts/demo.sh
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765) if it does not open automatically.

Use a clear image of a public figure whose exact or similar photo is present in a public social post. Confirm the permission statement, run the live search, inspect the selected result, approve publication, and verify the public transaction.

## Command line use

Run the full preparation pipeline without publishing:

```bash
uv run faceproof run path/to/face.jpg
```

Run it and publish after preparation:

```bash
uv run faceproof run path/to/face.jpg --publish
```

Verify a saved run again:

```bash
uv run faceproof verify RUN_ID
```

Verify any exported evidence file directly against a public transaction:

```bash
uv run faceproof verify-file evidence.json 0xTRANSACTION_HASH
```

Print the deterministic fingerprint without using the blockchain:

```bash
uv run faceproof hash-evidence evidence.json
```

## What is stored on Base Sepolia

FaceProof uses a normal EVM transaction instead of deploying a smart contract. The wallet sends a zero value transaction to its own address. The transaction data is:

```text
UTF-8 bytes for FACEPROOF + version byte 0x01 + 32 byte SHA-256 fingerprint
```

This design creates a public, timestamped, tamper evident record with less code and less gas than a contract deployment. Verification checks all of these facts:

1. The RPC endpoint reports Base Sepolia chain ID `84532`.
2. The transaction succeeded.
3. The sender and receiver are the same disposable wallet.
4. The transaction data equals the schema marker and recomputed evidence fingerprint.
5. The transaction exists in a confirmed block.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and threat model.

## Evidence format

Each run writes its files to `.context/runs/<run-id>/`. The important files are:

- `evidence.json`: readable evidence with the input fingerprint, live search traces, selected public source, retrieved media fingerprint, face score, threshold, and privacy declaration.
- `evidence.canonical.json`: the same covered data encoded as sorted UTF-8 JSON with Unicode normalization and no insignificant spaces.
- `state.json`: the resumable local run record and blockchain receipt.
- `input.jpg`, `face.jpg`, `annotated.jpg`, and candidate images: local review copies.

The SHA-256 value is calculated from `evidence.canonical.json`. Changing any covered value changes the fingerprint and makes verification fail.

See [docs/EVIDENCE_SCHEMA.md](docs/EVIDENCE_SCHEMA.md) for the field level contract.

## Testing and security checks

```bash
./scripts/check.sh
```

The check runs formatting, lint, strict type checking, unit and integration tests with coverage, a Bandit source scan, a dependency vulnerability audit, a scan for common secret shapes, and a release package asset check. CI runs the same checks on every pull request.

The test suite covers canonical fingerprints, tamper detection, social URL filtering, fresh search parameters, model file integrity, image limits, wallet permissions, the complete pipeline with deterministic service doubles, blockchain payload verification, and API security headers.

## Privacy and responsible use

- Search begins only after the user confirms permission to use the image.
- The image is sent to SerpApi and Google Lens because that is required for visual search. The interface says this before submission.
- Face embeddings exist in memory only. They are not written to disk or sent to the blockchain.
- Raw images, social content, API keys, and wallet keys are never placed onchain.
- Remote images have strict byte limits. Private network addresses and unsafe URL schemes are blocked.
- Browser responses include a restrictive Content Security Policy and other security headers.
- The system reports a similarity score and threshold. It never labels the score as certainty or legal identity.

Read [SECURITY.md](SECURITY.md) before using the project with any image that is not already public.

## Known limitations

- Google Lens results depend on region, indexing, account quota, and the public web at the time of the run.
- Some social sites block automated image downloads. FaceProof tries the returned media and thumbnail URLs, but a candidate can remain unevaluated.
- Face recognition can be wrong. Lighting, age, pose, occlusion, image quality, demographic bias, and model limitations affect the score.
- The largest detected face is selected when several faces appear.
- A public post can later change or disappear. The evidence keeps its URL, title, search provenance, and retrieved image fingerprint, but this project does not publish a permanent media archive.
- Base Sepolia is a test network. It demonstrates public verification but is not intended as a permanent production ledger.
- The local run store is designed for one reviewer on one computer. It is not a shared, authenticated production service.

## Repository map

```text
src/faceproof/
  api.py          Local FastAPI interface and security headers
  face.py         YuNet detection and SFace comparison
  search.py       Fresh SerpApi Google Lens searches
  evidence.py     Canonical evidence and SHA-256 fingerprint
  blockchain.py   Base Sepolia publication and verification
  pipeline.py     State machine and failure handling
  static/         Judge-facing workbench
tests/            Unit and deterministic integration tests
docs/             Evidence, testing, and recording guides
scripts/          Setup, checks, and demo entry points
```

## Submission recording

Follow [docs/RECORDING.md](docs/RECORDING.md). It gives a short recording order that proves the live search, local comparison, public transaction, and repeat verification without exposing any secret.

## License

This project is released under the [MIT License](LICENSE).
