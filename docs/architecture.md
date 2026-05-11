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

`os/stateless-qr-vault-profile.md` is the implementation-side operating profile
for future Raspberry image work. It mirrors the checked `NostrSeal/hardware`
OS profile: removable microSD boot media, disabled or absent wireless,
RAM-only session custody, no swap during signing, no remote access during
signing, and no persistent signing-secret storage. It is not a downloadable OS
image or a production security claim.

## Implemented Foundation

- `nostrseal_vault.qr`: v0 `nseal1:` QR envelope helpers.
- `nostrseal_vault.limits`: NostrSeal v0 constrained-signer implementation
  limits mirrored from `NostrSeal/specs`.
- `nostrseal_vault.crypto`: NIP-01 canonical event serialization, event id
  computation, x-only public key derivation, and BIP-340 signing.
- `nostrseal_vault.nip06`: BIP-39 seed and BIP-32 path derivation for
  `m/44'/1237'/<account>'/0/0` NIP-06 keys.
- `nostrseal_vault.seed_entry`: hardware-neutral BIP-39 word-entry controller
  for future Pi display/button adapters. It validates English mnemonic words
  and checksum before deriving a one-shot NIP-06 session secret provider.
- `nostrseal_vault.review`: deterministic event review model checked against
  shared `NostrSeal/specs` review vectors.
- `nostrseal_vault.display`: deterministic trusted-display page model for raw
  event kind, signer author pubkey, complete content, complete tags, and final
  approval decisions.
- `nostrseal_vault.controls`: physical-button approval session model for
  future GPIO adapters. It requires every trusted-review page to be traversed
  before approval can succeed and keeps rejection available before the final
  page.
- `nostrseal_vault.hardware_flow`: hardware-agnostic QR signer orchestration
  with injected scan, display, button, and response-QR boundaries.
- `nostrseal_vault.adapters`: file-backed QR flow adapters used by the CLI and
  integration smoke tests, plus a composed button-flow adapter boundary that
  keeps scanner, trusted display, physical button input, and response QR output
  independently replaceable before real camera/display/GPIO drivers exist.
  These are development and driver-facing adapters, not production Pi drivers.
- `nostrseal_vault.signer`: request handling and explicit approval gate.
- `nostrseal_vault.cli`: desktop simulation CLI for JSON and QR file input and
  output.

QR decoding and signing-request validation apply the shared v0 hardening limits
before trusted review or signing. The Raspberry implementation rejects
malformed, padded, invalid UTF-8, or oversized QR envelopes and rejects unsafe
event templates, unknown signing-request fields, and resource-limit violations
using the shared invalid-vector expectations from `NostrSeal/specs`.

The current CLI is a development harness. It intentionally requires an explicit
`--approve` flag before producing a `sign_event` response so automated tests and
desktop experiments preserve the same approval boundary expected on real
hardware.

The `sign` and `flow` commands can use explicit development `--secret-key`,
stdin-fed `--secret-key-stdin`, NIP-06 `--mnemonic-file`, stdin-fed
`--mnemonic-stdin`, or word-by-word stdin `--mnemonic-words-stdin` plus account
index. The file and argument paths are desktop simulation compatibility paths.
The stdin paths better match the stateless target because session key material
can be supplied without a seed file or a process-list-visible secret argument,
but they are still development harness inputs rather than a final Pi
seed-entry UX. Real Pi adapters must keep seed material RAM-only for the
current signing session.

`MnemonicSessionSecretProvider` is the first package-owned boundary for that
future seed-entry UX. A display/button adapter supplies one BIP-39 word at a
time through `MnemonicWordInput`; package code normalizes case/whitespace,
checks the English BIP-39 wordlist and checksum, derives the NIP-06 account key,
and refuses reuse after one session. This still does not make Python strings
securely erasable memory, so it is an acceptance boundary for stateless flow
ordering rather than a production memory-hardening claim.

`--mnemonic-words-stdin` is the CLI harness for that same boundary. It reads
exactly the selected BIP-39 word count from stdin, one word per line, then
derives the same NIP-06 session key before review. It exists so desktop and lab
smokes can exercise the future display/button seed-entry contract without
introducing a seed file, persistent secret storage, or Pi-specific UI code.

The `review` command is intentionally separate from `sign`: it takes a request,
produces deterministic review JSON, and does not sign. In desktop-only mode it
uses the deterministic fixture author pubkey; the hardware flow derives the
author pubkey from the RAM-only session key before review so the displayed
author is signer-derived and bound into the `approval_digest`.

The review model is not a UI. It is the deterministic data contract that a Pi
Zero display flow must render before approval: raw event kind, created_at,
signer author pubkey, complete content, and complete structured tags. It does
not infer kind meanings, abbreviate tag values, or add heuristic warnings. The
shared vectors prevent the Pi display flow, companion harness, and future ESP32
display work from drifting on review semantics.

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

`render_review_detail_pages` is the complete constrained-display page contract
for future display adapters that need the same top-level Event/Content/Tags/
Decision model as ESP32 without forcing every wrapped line to become a top-level
approval page. It pins scroll-window indicators, compact body styles, long tag
continuation indentation, and explicit codepoint fallback while preserving the
existing `screen-pages` approval digest. The CLI exposes it through
`nseal-vault review --output-format detail-pages-json` for adapter harnesses
and manual review experiments.

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

For future Raspberry display adapters that need the complete no-ellipsis review
body, `run_detail_button_qr_vault_flow` and `nseal-vault flow --review-mode
detail` use the `review-detail-pages-v0` page model. `next` advances between
Event, Content, Tags, and Decision; `scroll` moves through additional windows
inside the current logical page. This mirrors the ESP32 T-Display S3 review UX
without changing the signing digest: approval is still bound to the shared
`screen-pages` `approval_digest`, and signing still requires terminal physical
approval on the Decision page.

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
The stricter `run_detail_button_qr_vault_flow` path also consumes detail-mode
review-transcript vectors, including `scroll` actions inside long Content or
Tags windows. This keeps the no-ellipsis constrained-display path aligned with
ESP32 without forcing every scroll window before the Decision page.

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
reached. The loop also bounds non-terminal button streams so an adapter cannot
hang forever by repeatedly returning `next` on the final page. Its result
includes the review transcript actually shown and acted on. Real GPIO/display
adapters should attach to this boundary first.

`run_button_qr_vault_flow_with_secret_provider` is the stateless hardware-facing
variant for future Pi flows. The secret provider is called after request QR
decode and before review so the signer-derived author pubkey can be displayed
and bound into the `approval_digest`. That key material must remain RAM-only for
the current signing session; early rejection still refuses to sign and emits a
rejection response, but it is not a no-key-loaded path. The older
`run_button_qr_vault_flow` helper stays as a compatibility wrapper for the
desktop harness.

The file-backed adapters live in package code rather than private CLI classes.
This keeps the CLI as a thin adapter and gives future Raspberry camera,
display, and GPIO drivers a concrete behavioral reference for when review JSON,
display-frame logs, button input, and response QR output are allowed to occur.

`ComposedButtonQrVaultIO` is the first non-file adapter boundary for that same
flow. It delegates request scanning, frame display, button reads, and response
QR output to four small interfaces, so a future Pi camera, display library,
GPIO button module, and QR response renderer can be swapped independently while
the review/signing state machine stays unchanged.
