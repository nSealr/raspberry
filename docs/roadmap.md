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
- Raspberry Pi Zero build plan centered on SeedSigner-compatible hardware.
- Camera, display, and GPIO approval interface selection mapped to the Pi
  CSI/OV5647 camera path, Waveshare-compatible ST7789 240x240 display HAT, and
  SeedSigner-style HAT joystick/buttons.

Status: the hardware direction is now fixed to SeedSigner-style compatibility,
with the available Raspberry Pi Zero as the first physical target. This does
not add a new solution family, persistent secret storage, or TROPIC01; it makes
the future Raspberry adapters target the same practical kit shape as
SeedSigner.

Status: `nsealr-vault hardware-probe` now produces a non-destructive
SeedSigner-compatible Pi Zero setup report. It gives the later physical smoke a
repeatable way to check board model, GPIO/SPI/camera Python modules,
camera/SPI boot config markers, swap state, wireless absence/blocking evidence,
and SSH/sshd service state before camera/display/GPIO adapters are treated as
accepted. The report now also returns deterministic acceptance blockers and
human-action prompts for anything that still needs physical setup or operator
verification.

## M6: Raspberry Prototype

- SeedSigner-compatible camera/display abstraction.
- SeedSigner-compatible physical-button approval flow.
- Signed QR output.
- Companion verification loop.
- Pre-signing hardening-vector rejection for unsafe signing requests and
  constrained-resource violations while preserving stateless RAM-only custody.

Status: the first hardware-agnostic QR vault flow orchestrator is implemented
in `nsealr_vault.hardware_flow`. Real camera, display, and GPIO adapters are
still pending. A file-backed `nsealr-vault flow` harness now exercises the same
boundary from the CLI.

Status note, 2026-05-10: Raspberry QR tooling now supports the shared
`nsealr1a:` animated QR frame set for larger valid request/response files.
`nsealr-vault sign` can read and write `qr-animated` frame files, and
`nsealr-vault flow --output-format qr-animated` can emit a multi-frame response
while preserving the existing review and approval digest semantics.

Status: the physical-button approval state machine is implemented in
`nsealr_vault.controls`. It is still hardware-neutral, but it pins the rule
that approval can only happen after every trusted-review page has been reached,
while rejection can happen at any point. The same package now generates
renderer-neutral review transcripts checked against shared
`nSealr/specs` vectors.

Status: `nsealr_vault.hardware_flow.run_button_qr_vault_flow` now connects
that state machine to the QR flow boundary. It displays one trusted page at a
time, reads physical-style `next`, `approve`, and `reject` actions, signs only
after a complete page traversal and approval, bounds non-terminal button
streams, and emits a QR response only after a terminal decision.

Status: `nsealr_vault.display.render_display_frame` now renders one bounded
trusted-display frame at a time, with deterministic title truncation, wrapped
body lines, page indicator, and action hint. `nsealr-vault review
--output-format display-frame-json` exposes the same frame contract for future
Raspberry display adapter tests. Real display drivers are still pending.

Status: `nsealr_vault.display.render_review_detail_pages` now renders the
complete constrained-display Event/Content/Tags/Decision page contract and
matches shared `nSealr/specs` review-detail-page vectors.
`nsealr-vault review --output-format detail-pages-json` exposes those pages for
future adapter harnesses. This gives future Raspberry display adapters the same
no-ellipsis, scroll-window review semantics as ESP32 while keeping
camera/display/GPIO drivers pending.

Status: the button-driven QR flow now renders bounded display frames before
each physical-style input and can write those frames through `nsealr-vault flow
--display-frame-log`. This turns the hardware-neutral flow into an acceptance
trace for future Pi display adapters while keeping real drivers pending.

Status: the button-driven QR flow result now records the exact displayed
frame/button/decision transcript. Tests cross-check that trace against shared
`nSealr/specs` review-transcript vectors under transcript-compatible display
limits, while real camera, display, and GPIO drivers remain pending.

Status: `nsealr-vault flow --review-transcript-log` now exports the same
frame/button/decision transcript from the file-backed button harness. This lets
`nSealr/lab` and future adapter tests verify full review-loop traces without
importing Raspberry implementation code.

Status: Raspberry now consumes shared detail-mode review-transcript vectors for
long tag scroll windows. The checked flow uses `next` for top-level
Event/Content/Tags/Decision navigation and `scroll` inside Tags while keeping
approval gated on the final Decision page.

Status: `nsealr-vault flow --review-mode detail` now lets the file-backed
button harness render complete Event/Content/Tags/Decision detail pages. The
flow uses top-level `next` navigation plus `scroll` within long logical pages,
so future Raspberry display adapters can inspect long content/tags without
forcing every scroll window before Decision. The shared `screen-pages`
`approval_digest` remains the signing binding.

Status: `nSealr/lab` integration now drives the file-backed
`nsealr-vault flow` path and verifies the signed response QR with
`nSealr/companion` `nsealr verify-response`. This closes the desktop
companion verification loop for the hardware-agnostic Raspberry QR vault path
without adding camera, display, or GPIO drivers.

Status: `run_button_qr_vault_flow_with_secret_provider` now gives future
stateless Pi adapters a RAM-only session secret boundary. The provider is
called after QR decode and before review so the trusted screen can display and
bind the signer-derived author pubkey into the `approval_digest`; rejection
still refuses to sign, and approval still requires complete review traversal
plus terminal physical approval. The existing CLI-compatible helper remains a
wrapper around this path.

Status: `nsealr-vault sign` and `nsealr-vault flow` can now read a session secret
or NIP-06 mnemonic from stdin through `--secret-key-stdin` and
`--mnemonic-stdin`. This keeps the desktop harness closer to the stateless
RAM-only target by avoiding required seed files or secret command-line
arguments, while real Pi seed-entry UX and hardware drivers remain pending.

Status: `nsealr_vault.seed_entry.MnemonicSessionSecretProvider` now gives
future Pi seed-entry adapters a package-owned word-by-word BIP-39 controller.
It validates English wordlist membership and checksum, derives the NIP-06
session key once, and plugs into the existing RAM-only secret-provider flow.
Real Pi keypad/display UX and production memory-hardening remain pending.

Status: `nsealr-vault sign --mnemonic-words-stdin` and `nsealr-vault flow
--mnemonic-words-stdin` now expose that controller through the desktop CLI by
reading one BIP-39 word per stdin line. This gives lab and adapter harnesses a
closer simulation of future Pi word entry while keeping real camera, display,
GPIO, and production memory-hardening work pending.

Status: the file-backed QR flow adapters now live in
`nsealr_vault.adapters` instead of private CLI classes. The CLI remains a
thin file/argument wrapper around package-owned scan, review, display-frame
log, button-sequence, and response-QR boundaries; real camera, display, and
GPIO drivers remain pending.

Status: `nsealr_vault.adapters.ComposedButtonQrVaultIO` now exposes the
next adapter boundary for real Raspberry drivers by composing scanner,
trusted-display, physical-button, and response-QR components behind the tested
button-driven QR flow. This is still hardware-neutral and does not add camera,
display, or GPIO drivers.

Status: `nsealr_vault.seed_signer_hardware` now pins the first
SeedSigner-compatible 40-pin HAT button profile in package code. It maps
right/down/center/KEY1 GPIO inputs to `next`/`scroll`/`approve`/`reject` and is
covered with injected-GPIO tests, while real Pi hardware acceptance remains
pending.

Status: `nsealr_vault.st7789_layout` now provides a SeedSigner-compatible
240x240 ST7789 trusted-review layout plan. It emits bounded draw commands for
title, page indicator, styled body lines, and action hint, giving the future
Pi display driver a tested pre-pixel layout contract.

Status: `nsealr_vault.seed_signer_hardware` now includes injected
driver-facing adapters for SeedSigner-compatible Pi bring-up: a camera QR
scanner boundary, an ST7789 trusted-review display boundary, and an ST7789
response-QR display boundary. These adapters are testable without Pi hardware
and do not claim physical camera/display acceptance until connected to real
frame sources, draw targets, QR rendering, and the available Pi Zero kit.

Status: the SeedSigner-compatible camera path now has optional concrete
`picamera` JPEG frame capture and `pyzbar`/zbar QR decoding adapters behind the
existing injected scanner boundary. These dependencies remain optional so CI
and desktop tests do not require Pi libraries. Physical OV5647/ZeroCam scan
quality on the available Pi Zero remains pending.

Status: the ST7789 review-display path now has an optional PIL framebuffer
draw target that maps bounded layout commands to rectangles/text and presents
the resulting image through an injected display presenter. This bridges the
tested layout contract toward Waveshare/SeedSigner-style display drivers
without making Pillow or Pi display libraries mandatory outside the Pi image.
Physical ST7789 display acceptance remains pending.

Status: the signed response QR path now has an optional `python-qrcode` matrix
renderer behind the existing ST7789 response display adapter. It validates the
generated square boolean matrix before drawing it and remains optional outside
the Pi image. Physical response-QR readability and scan-back acceptance remain
pending.

Status: `nsealr-vault flow --st7789-layout-log` now exports the ST7789 layout
commands generated from each button-driven review frame, so future display
driver tests can compare the physical adapter against a committed harness
trace.

Status: Raspberry now mirrors the shared nSealr v0 implementation-limit
profile and rejects applicable invalid signing-request and QR-envelope
hardening vectors before review or signing, while remaining stateless and
RAM-only.

Status: Raspberry now has an explicit shared identity/policy boundary through
the `nsealr-account-descriptor-v0` route `raspberry_qr_vault` and
`policy-manual-only-qr-vault`. The route stays `stateless_session`,
`manual_only`, and `persistent_grants: false`; this does not add policy
automation, persistent storage, or TROPIC01 to the Raspberry QR vault.

Status note, 2026-05-19: Raspberry now also consumes the shared
`raspberry-qr-sign-event-account-0` route-selection vector. The checked
selection remains QR transport, device-display reviewed, physically approved,
manual-only, `stateless_session`, `persistent_grants: false`, and
`contains_secret_material: false`.

Status note, 2026-05-11: the Raspberry product target explicitly includes
SeedSigner Standard SeedQR and CompactSeedQR import, plain BIP-39 mnemonic QR,
`nsec` QR, local mnemonic generation, and local standalone-key generation as
RAM-only session sources. The feature is BIP-39/NIP-06 Nostr account import,
not Bitcoin descriptor, xpub, PSBT, or wallet-policy import. MicroSD/file
secret transfer stays outside QR vault acceptance.

Status note, 2026-05-19: local generation now has a package-owned boundary for
12- and 24-word BIP-39 session sources plus standalone `nsec`-equivalent
private-key sources. Both use the same secret-hidden source review and
RAM-only keyring path as imported sources, and tests inject deterministic
entropy. The package also consumes shared danger-zone backup review vectors:
BIP-39 words/SeedQR or NIP-19 `nsec` recovery payloads are produced only after
the backup review reaches the final page and is approved. Final Pi physical
backup display/output acceptance and power-cycle evidence remain pending.

Status: `nsealr_vault.seed_entry` now implements SeedSigner-compatible
Standard SeedQR digit-stream parsing and CompactSeedQR entropy-byte parsing for
12- and 24-word English BIP-39 mnemonics. `nsealr-vault sign` and
`nsealr-vault flow` expose desktop stdin harnesses through `--seedqr-stdin` and
`--compact-seedqr-hex-stdin`, while real Pi camera adapters remain responsible
for delivering decoded QR text or bytes directly without seed files.

Status: `nsealr_vault.seed_entry` now implements NIP-19 `nsec` Bech32 decoding
as a one-shot RAM-only session secret provider checked against the shared
`nSealr/specs` NIP-19 vector. `nsealr-vault sign` and `nsealr-vault flow`
expose the desktop harness through `--nsec-stdin`; real Pi camera adapters
remain responsible for delivering decoded private-key QR text directly without
seed files, key slots, persistent storage, or account-index derivation.

Status: `nsealr_vault.seed_entry` now also builds shared secret-hidden session
import reviews for SeedQR/BIP-39 and NIP-19 `nsec` session sources. The review
contract exposes type, label, word count where applicable, fingerprint,
`review_id`, and import approval digest while hiding mnemonic words and raw
private-key bytes. This is a RAM-load review boundary, not NIP-06 derivation,
persistent storage, or signing approval.

Status note, 2026-05-19: the Raspberry QR account descriptor now carries the
same reviewed source fingerprint as the canonical NIP-06 account-0 import
review vector. This keeps account metadata bound to the RAM-only source review
without adding persistent policy, persistent secrets, or TROPIC01.

Status: `nsealr-vault review-import` now exposes that RAM-load review boundary
from the desktop CLI for stdin-fed BIP-39 mnemonic, word-by-word mnemonic,
Standard SeedQR, CompactSeedQR, and NIP-19 `nsec` sources. It is still a
hardware-agnostic harness for future Pi seed-entry screens: it writes no output
after invalid source input and does not sign, derive a NIP-06 account key,
persist source material, or approve later signing.

Status: `nsealr_vault.session_import_flow` now adds the package-owned local
import-approval loop for future Pi seed-entry screens. A parsed SeedQR/BIP-39
or NIP-19 `nsec` source is loaded into the stateless RAM-only keyring only
after the secret-hidden import review reaches the final decision page and is
approved. Rejection, early approval, and non-terminal button streams leave the
keyring unchanged. This still does not derive NIP-06 keys, sign events, persist
material, create policy state, or complete camera/display/GPIO import UX.

Status: `nsealr_vault.session_source_qr` now gives future Pi camera adapters
the same decoded source-QR boundary as ESP32. It parses decoded text as NIP-19
`nsec`, SeedSigner Standard SeedQR, or plain BIP-39 mnemonic text, parses
CompactSeedQR entropy bytes separately, and can compose those sources with the
local import-review flow before loading the RAM-only keyring. This still does
not add persistence, policy automation, or physical camera/display acceptance.

Status: approved RAM-only session sources can now feed the existing
button-driven signing flow through `StatelessSessionSecretProvider`. BIP-39
sources derive NIP-06 from explicit account/passphrase inputs and NIP-19 `nsec`
sources return the imported key, both as one-shot session providers. This still
does not add persistence, policy state, or final Pi import/sign UX.

Status: the stateless session keyring now stores its internal source copy in
mutable package-owned slots and wipes those slots on `clear()` and object
destruction. This is best-effort Python process hygiene; real Pi image
acceptance still needs power-cycle/session-loss evidence and must not claim
interpreter-wide secure memory erasure.

Status: `os/stateless-qr-vault-profile.md` now records the future Raspberry
image acceptance boundary aligned with `nSealr/hardware`: removable microSD
boot media, disabled or absent wireless, RAM-only session custody, no swap
during signing, no remote access during signing, disabled setup interfaces, and
no persistent signing-secret storage. It is planning and acceptance criteria,
not a downloadable OS image.

## Later

- Minimal OS image path.
- Reproducible build docs.
- Hardware acceptance matrix.

## Boundary

Shared QR vault contracts stay in `nSealr/specs`. ESP32-S3 QR vault firmware
is a separate target in `nSealr/esp32`; it should reuse the same vectors and
approval-digest semantics rather than depending on Raspberry implementation
code. Review-transcript vectors are part of that shared contract.

The Raspberry/Pi QR vault remains a stateless, air-gapped, RAM-only custody
line. The pre-signing hardening gate may add parser/rejection conformance, but
it must not add persistent secret storage, secure-element unlock, or TROPIC01
dependency to this line.
