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
- Shared review-transcript vector consumption for display/GPIO adapter tests.

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

Status: the physical-button approval state machine is implemented in
`nostrseal_vault.controls`. It is still hardware-neutral, but it pins the rule
that approval can only happen after every trusted-review page has been reached,
while rejection can happen at any point. The same package now generates
renderer-neutral review transcripts checked against shared
`NostrSeal/specs` vectors.

Status: `nostrseal_vault.hardware_flow.run_button_qr_vault_flow` now connects
that state machine to the QR flow boundary. It displays one trusted page at a
time, reads physical-style `next`, `approve`, and `reject` actions, signs only
after a complete page traversal and approval, and emits a QR response.

Status: `nostrseal_vault.display.render_display_frame` now renders one bounded
trusted-display frame at a time, with deterministic title truncation, wrapped
body lines, page indicator, and action hint. `nseal-vault review
--output-format display-frame-json` exposes the same frame contract for future
Raspberry display adapter tests. Real display drivers are still pending.

## Later

- Minimal OS image path.
- Reproducible build docs.
- Hardware acceptance matrix.

## Boundary

Shared QR vault contracts stay in `NostrSeal/specs`. ESP32-S3 QR vault firmware
is a separate target in `NostrSeal/esp32`; it should reuse the same vectors and
approval-digest semantics rather than depending on Raspberry implementation
code. Review-transcript vectors are part of that shared contract.
