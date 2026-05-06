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

## Implemented Foundation

- `nostrseal_vault.qr`: v0 `nseal1:` QR envelope helpers.
- `nostrseal_vault.crypto`: NIP-01 canonical event serialization, event id
  computation, x-only public key derivation, and BIP-340 signing.
- `nostrseal_vault.signer`: request handling and explicit approval gate.
- `nostrseal_vault.cli`: desktop simulation CLI for JSON and QR file input and
  output.

The current CLI is a development harness. It intentionally requires an explicit
`--approve` flag before producing a `sign_event` response so automated tests and
desktop experiments preserve the same approval boundary expected on real
hardware.
