# Security and responsible use

## Intended use

FaceProof is a hackathon demonstration for finding public social content and proving the integrity of collected evidence. Use an image only when you have permission or when the image clearly depicts a public figure in a public context.

Do not use this project for stalking, covert identification, employment decisions, credit decisions, housing decisions, law enforcement, access control, or any decision that affects a person's rights or safety.

## Biometric limits

Face comparison is probabilistic. A passing score is not proof of a legal name, intent, account ownership, or identity. Human review of the source and context is required. False matches and unequal model performance across demographic groups are known classes of risk.

## Data handling

- The input image is uploaded to SerpApi for Google Lens processing after the user confirms permission.
- The local SFace embedding stays in process memory and is not saved.
- Normalized local images and run files are stored under `.context/runs`, ignored by Git, and restricted to owner only directory access. The original upload is deleted after decoding so its EXIF metadata is not retained in the run.
- The SerpApi key is loaded from `.context/secrets.env`, which setup restricts to owner only access, and is not returned by the API.
- The Base Sepolia private key is stored in `.context/base-sepolia-wallet.json` with mode `0600`.
- Only the evidence schema marker and SHA-256 fingerprint are written to the public blockchain.

Delete `.context/runs` when the local evidence is no longer needed. Move the files to Trash if recovery may be needed. Never publish a raw face image or private profile data to a blockchain because public blockchain data cannot be removed.

## Wallet safety

The generated wallet is for Base Sepolia only.

- Use free Base Sepolia test ETH only.
- Never send mainnet ETH, tokens, or valuable assets to the address.
- Never import this private key into a wallet that contains real assets.
- Do not display the wallet file during the recording.
- If the key is exposed, stop using the wallet and create a new disposable file.

## Local service

The demo server binds to `127.0.0.1` by default. Do not bind it to a public interface without adding authentication, rate limits, encrypted storage, and a full deployment review.

Remote candidate downloads reject private and non-global IP addresses, URL credentials, and unsupported schemes. Redirect targets are checked again. Byte and pixel limits reduce resource exhaustion risk. Trusted host validation and same origin checks prevent another website from submitting browser mutations to the local service.

## Reporting a vulnerability

Open a private GitHub security advisory for the repository owner. Do not include a real face image, API key, private key, or other personal data in the report.
