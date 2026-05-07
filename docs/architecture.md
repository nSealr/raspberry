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
- `nostrseal_vault.controls`: physical-button approval session model for
  future GPIO adapters. It requires every trusted-review page to be traversed
  before approval can succeed and keeps rejection available before the final
  page.
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

`render_display_frame` is the bounded frame contract above the page model. It
turns one trusted page into a title, page indicator, wrapped body lines, and an
action hint while enforcing maximum title, body-line, and line-width limits.
This gives future ST7789/Waveshare/OLED adapters a deterministic pre-driver
oracle for text fitting before graphical rendering is implemented.

`nostrseal_vault.controls` is the first renderer-neutral model for that button
loop. A session starts on the first page, records which pages have been shown,
maps `next`, `approve`, and `reject` button actions, and refuses approval until
the final `approve_or_reject` page has been reached after all pages were seen.
This gives the future GPIO implementation a tested approval state machine
before any Raspberry-specific display or button driver is selected.

The button-driven hardware flow now renders those page states through
`render_display_frame` before each physical-style input. The file-backed CLI can
record the displayed frames with `--display-frame-log`, giving display adapters
a deterministic acceptance trace before real Pi display drivers are wired in.
The in-process flow result also carries the exact frame/button/decision
transcript produced during the review loop, which lets tests compare future
adapter harnesses with shared `NostrSeal/specs` review-transcript vectors.
The file-backed CLI can write this trace with `--review-transcript-log`, giving
cross-repo smoke tests the same oracle without importing Raspberry internals.

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

`review_transcript_for_screen_review` records the renderer-neutral frame shown
before each physical-style button input, the terminal decision, and the
approval state. It is checked against shared `NostrSeal/specs`
review-transcript vectors so Raspberry display/GPIO adapters and ESP32 firmware
adapter tests can use the same frame/button/decision oracle.

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

The `nseal-vault flow` command is the current file-backed harness for this
boundary. It reads a QR request from a file, writes the exact screen-review JSON
that a trusted display must render, requires explicit `--approve`, and writes a
QR response. It is for desktop integration and hardware-adapter development,
not for production key custody.

`run_button_qr_vault_flow` is the stricter hardware-facing boundary. Instead of
accepting one boolean from `show_review`, it renders one page at a time through
`display_review_frame`, reads `next`, `approve`, or `reject` through
`read_review_button`, and delegates the state machine to
`ReviewControlSession`. This keeps physical approval impossible until every
trusted page has been displayed and the final approve/reject page has been
reached. Its result includes the review transcript actually shown and acted on.
Real GPIO/display adapters should attach to this boundary first.
