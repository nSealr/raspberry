# Architecture

`NostrSeal/vault` is the Pi Zero / SeedSigner-style QR vault line.

## Responsibilities

- Receive signing requests through QR.
- Render trusted event review.
- Require physical approval or rejection.
- Sign NIP-01 event ids with BIP-340.
- Return signed events through QR.
- Preserve an air-gapped, minimal-runtime security model.

## Reference Strategy

SeedSigner is a conceptual reference for QR flow, stateless operation, display
review, and minimal OS philosophy. Bitcoin/PSBT assumptions must not leak into
Nostr event signing.

