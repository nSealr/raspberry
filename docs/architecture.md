# Architecture

`NostrSeal/raspberry` is the Raspberry/Pi signer implementation family. Its
first line is the Pi Zero / SeedSigner-style QR vault flow.

## Responsibilities

- Implement Raspberry/Pi signer software and OS integration.
- Receive signing requests through QR for the QR vault flow.
- Render trusted event review on a Raspberry-connected display.
- Require physical approval or rejection.
- Sign NIP-01 event ids with BIP-340 after approval.
- Return signed events through QR.
- Preserve an air-gapped, minimal-runtime security model where the hardware
  profile supports it.

## Reference Strategy

SeedSigner is a conceptual reference for QR flow, stateless operation, display
review, and minimal OS philosophy. Bitcoin/PSBT assumptions must not leak into
Nostr event signing.

## Implemented Foundation

- `nostrseal_vault.qr`: v0 `nseal1:` QR envelope helpers.
- `nostrseal_vault.crypto`: NIP-01 canonical event serialization, event id
  computation, x-only public key derivation, and BIP-340 signing.
- `nostrseal_vault.nip06`: BIP-39 seed and BIP-32 path derivation for
  `m/44'/1237'/<account>'/0/0` NIP-06 keys.
- `nostrseal_vault.review`: deterministic event review model checked against
  shared `NostrSeal/specs` review vectors.
- `nostrseal_vault.display`: deterministic trusted-display page model for
  event, content, tags, warnings, and final approval decisions.
- `nostrseal_vault.signer`: request handling and explicit approval gate.
- `nostrseal_vault.cli`: desktop simulation CLI for JSON and QR file input and
  output.

The current CLI is a development harness. It intentionally requires an explicit
`--approve` flag before producing a `sign_event` response so automated tests and
desktop experiments preserve the same approval boundary expected on real
hardware.

The sign command can use either an explicit development `--secret-key` or a
NIP-06 `--mnemonic-file` plus account index. The mnemonic-file path is still a
desktop simulation path; the Pi hardware flow should keep seed material in RAM
and avoid shell arguments for production use.

The `review` command is intentionally separate from `sign`: it takes a request,
produces deterministic review JSON, and never needs key material. This mirrors
the future display flow where review must happen before approval and signing.

The review model is not a UI. It is the deterministic data contract that a Pi
Zero display flow must render before approval: event kind, content preview, tag
summary, and warnings. The shared vectors prevent the Pi display flow,
companion harness, and future ESP32 display work from drifting on review
semantics.

The display page model is the next contract above the raw review data. It
orders the pages that a small trusted screen must show and marks the final page
as `approve_or_reject`. It is still renderer-neutral: real Pi code can map the
same page objects onto GPIO buttons, a camera loop, and the selected display
library without changing the signing contract.

The `screen-json` output also includes an `approval_digest`. The digest is a
SHA-256 hash of canonical request metadata, the exact event template, the
review model, and the rendered page model. It is not a secret and is not shown
as a user-authentication primitive. It gives the CLI and future device state
machine a deterministic way to reject an approved signing step if it is no
longer bound to the request that was reviewed.

The screen page model and digest calculation are checked against shared
`NostrSeal/specs` review-screen vectors so Raspberry and ESP32 QR vault targets
can implement the same review-to-approval contract without copying platform
code.

## Hardware Flow Boundary

`nostrseal_vault.hardware_flow` defines the first Raspberry QR vault flow
orchestrator. It is intentionally pure Python and hardware-agnostic:

- camera drivers provide `scan_request_qr`;
- display/button drivers provide `show_review`;
- QR output drivers provide `emit_response_qr`.

The flow decodes one request QR, renders trusted screen pages, obtains physical
approval through the injected I/O boundary, signs with the displayed
`approval_digest`, and emits one response QR. Real camera, display, and GPIO
drivers must attach to this boundary rather than bypassing the review model.
