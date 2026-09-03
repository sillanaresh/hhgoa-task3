# Product

## Register

product

## Users

The primary users are hackathon judges who have only a few minutes to decide whether the submission works and can be trusted. A second group is developers who want to reproduce the pipeline from the repository.

Judges need to follow one complete run without prior knowledge of face recognition or blockchain systems. Developers need clear setup instructions, inspectable evidence, and failure messages that explain what to fix.

## Product purpose

This product accepts a face image, performs a live visual search for public social content, confirms a candidate with a local face comparison, and records a fingerprint of the evidence on the Base Sepolia public test network.

A successful run must prove where the result came from, why the faces were considered a match, what data was fingerprinted, and where that fingerprint can be checked on the public blockchain. A verification run must pass for unchanged evidence and fail after any covered evidence field changes.

## Brand personality

Precise, calm, and accountable.

The product should feel suitable for reviewing evidence. It should explain uncertainty and keep sources visible. It should avoid marketing claims and unexplained technical language.

## Anti-references

The product must not resemble a cryptocurrency trading screen, a neon cyber security dashboard, or a generic grid of statistic cards. It must not hide live work behind a spinner or present a weak face match as certain. It must not use decorative blockchain imagery, invented metrics, or fake progress.

## Design principles

1. Show the evidence next to every conclusion.
2. Make the live search easy to distinguish from saved test data.
3. Explain each pipeline stage in terms a first time user can understand.
4. Treat uncertain, partial, and failed results as normal product states.
5. Keep private images, face embeddings, and secret keys off the blockchain and out of Git.

## Accessibility and inclusion

The interface should meet WCAG 2.2 AA contrast and interaction requirements. It must support keyboard navigation, visible focus, reduced motion, browser zoom, clear status text, and layouts from 320 pixels wide through desktop screens. Color must not be the only way that the interface communicates status.
