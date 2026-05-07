# Roadmap

## Foundation: Desktop QR Signer Simulation

- Python package and CLI.
- QR envelope encode/decode.
- NIP-01 event id computation.
- BIP-340 signing against shared fixtures.
- Explicit approval gate.
- Deterministic review model.
- Deterministic trusted-display page model.
- Request-bound approval digest.

Status: implemented as the first executable Raspberry QR vault foundation.

## M5: Raspberry Architecture

- Signing service.
- Raspberry Pi Zero build plan.
- Camera, display, and GPIO approval interface selection.

## M6: Raspberry Prototype

- Camera/display abstraction.
- Physical-button approval flow.
- Signed QR output.
- Companion verification loop.

Status: the first hardware-agnostic QR vault flow orchestrator is implemented
in `nostrseal_vault.hardware_flow`. Real camera, display, and GPIO adapters are
still pending. A file-backed `nseal-vault flow` harness now exercises the same
boundary from the CLI.

## Later

- Minimal OS image path.
- Reproducible build docs.
- Hardware acceptance matrix.

## Boundary

Shared QR vault contracts stay in `NostrSeal/specs`. ESP32-S3 QR vault firmware
is a separate target in `NostrSeal/esp32`; it should reuse the same vectors and
approval-digest semantics rather than depending on Raspberry implementation
code.
