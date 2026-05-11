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
- Pre-signing hardening-vector rejection for unsafe signing requests and
  constrained-resource violations while preserving stateless RAM-only custody.

Status: the first hardware-agnostic QR vault flow orchestrator is implemented
in `nostrseal_vault.hardware_flow`. Real camera, display, and GPIO adapters are
still pending. A file-backed `nseal-vault flow` harness now exercises the same
boundary from the CLI.

Status note, 2026-05-10: Raspberry QR tooling now supports the shared
`nseal1a:` animated QR frame set for larger valid request/response files.
`nseal-vault sign` can read and write `qr-animated` frame files, and
`nseal-vault flow --output-format qr-animated` can emit a multi-frame response
while preserving the existing review and approval digest semantics.

Status: the physical-button approval state machine is implemented in
`nostrseal_vault.controls`. It is still hardware-neutral, but it pins the rule
that approval can only happen after every trusted-review page has been reached,
while rejection can happen at any point. The same package now generates
renderer-neutral review transcripts checked against shared
`NostrSeal/specs` vectors.

Status: `nostrseal_vault.hardware_flow.run_button_qr_vault_flow` now connects
that state machine to the QR flow boundary. It displays one trusted page at a
time, reads physical-style `next`, `approve`, and `reject` actions, signs only
after a complete page traversal and approval, bounds non-terminal button
streams, and emits a QR response only after a terminal decision.

Status: `nostrseal_vault.display.render_display_frame` now renders one bounded
trusted-display frame at a time, with deterministic title truncation, wrapped
body lines, page indicator, and action hint. `nseal-vault review
--output-format display-frame-json` exposes the same frame contract for future
Raspberry display adapter tests. Real display drivers are still pending.

Status: `nostrseal_vault.display.render_review_detail_pages` now renders the
complete constrained-display Event/Content/Tags/Decision page contract and
matches shared `NostrSeal/specs` review-detail-page vectors.
`nseal-vault review --output-format detail-pages-json` exposes those pages for
future adapter harnesses. This gives future Raspberry display adapters the same
no-ellipsis, scroll-window review semantics as ESP32 while keeping
camera/display/GPIO drivers pending.

Status: the button-driven QR flow now renders bounded display frames before
each physical-style input and can write those frames through `nseal-vault flow
--display-frame-log`. This turns the hardware-neutral flow into an acceptance
trace for future Pi display adapters while keeping real drivers pending.

Status: the button-driven QR flow result now records the exact displayed
frame/button/decision transcript. Tests cross-check that trace against shared
`NostrSeal/specs` review-transcript vectors under transcript-compatible display
limits, while real camera, display, and GPIO drivers remain pending.

Status: `nseal-vault flow --review-transcript-log` now exports the same
frame/button/decision transcript from the file-backed button harness. This lets
`NostrSeal/lab` and future adapter tests verify full review-loop traces without
importing Raspberry implementation code.

Status: `nseal-vault flow --review-mode detail` now lets the file-backed
button harness render complete Event/Content/Tags/Decision detail pages. The
flow uses top-level `next` navigation plus `scroll` within long logical pages,
so future Raspberry display adapters can inspect long content/tags without
forcing every scroll window before Decision. The shared `screen-pages`
`approval_digest` remains the signing binding.

Status: `NostrSeal/lab` integration now drives the file-backed
`nseal-vault flow` path and verifies the signed response QR with
`NostrSeal/companion` `nseal verify-response`. This closes the desktop
companion verification loop for the hardware-agnostic Raspberry QR vault path
without adding camera, display, or GPIO drivers.

Status: `run_button_qr_vault_flow_with_secret_provider` now gives future
stateless Pi adapters a RAM-only session secret boundary. The provider is
called after QR decode and before review so the trusted screen can display and
bind the signer-derived author pubkey into the `approval_digest`; rejection
still refuses to sign, and approval still requires complete review traversal
plus terminal physical approval. The existing CLI-compatible helper remains a
wrapper around this path.

Status: `nseal-vault sign` and `nseal-vault flow` can now read a session secret
or NIP-06 mnemonic from stdin through `--secret-key-stdin` and
`--mnemonic-stdin`. This keeps the desktop harness closer to the stateless
RAM-only target by avoiding required seed files or secret command-line
arguments, while real Pi seed-entry UX and hardware drivers remain pending.

Status: the file-backed QR flow adapters now live in
`nostrseal_vault.adapters` instead of private CLI classes. The CLI remains a
thin file/argument wrapper around package-owned scan, review, display-frame
log, button-sequence, and response-QR boundaries; real camera, display, and
GPIO drivers remain pending.

Status: `nostrseal_vault.adapters.ComposedButtonQrVaultIO` now exposes the
next adapter boundary for real Raspberry drivers by composing scanner,
trusted-display, physical-button, and response-QR components behind the tested
button-driven QR flow. This is still hardware-neutral and does not add camera,
display, or GPIO drivers.

Status: Raspberry now mirrors the shared NostrSeal v0 implementation-limit
profile and rejects applicable invalid signing-request and QR-envelope
hardening vectors before review or signing, while remaining stateless and
RAM-only.

Status: `os/stateless-qr-vault-profile.md` now records the future Raspberry
image acceptance boundary aligned with `NostrSeal/hardware`: removable microSD
boot media, disabled or absent wireless, RAM-only session custody, no swap
during signing, no remote access during signing, disabled setup interfaces, and
no persistent signing-secret storage. It is planning and acceptance criteria,
not a downloadable OS image.

## Later

- Minimal OS image path.
- Reproducible build docs.
- Hardware acceptance matrix.

## Boundary

Shared QR vault contracts stay in `NostrSeal/specs`. ESP32-S3 QR vault firmware
is a separate target in `NostrSeal/esp32`; it should reuse the same vectors and
approval-digest semantics rather than depending on Raspberry implementation
code. Review-transcript vectors are part of that shared contract.

The Raspberry/Pi QR vault remains a stateless, air-gapped, RAM-only custody
line. The pre-signing hardening gate may add parser/rejection conformance, but
it must not add persistent secret storage, secure-element unlock, or TROPIC01
dependency to this line.
