# nSealr Raspberry

Raspberry/Pi software for nSealr signing devices.

This repository owns the Raspberry/Pi implementation family. The first line is
the SeedSigner-style QR vault flow for Nostr: scan an unsigned event request,
review on a trusted display, approve with physical controls, sign BIP-340, and
return a signed-event QR.

The primary hardware compatibility target is the SeedSigner-style Raspberry Pi
Zero kit: Pi Zero-class board, Pi/ZeroCam OV5647 camera, Waveshare-compatible
ST7789 240x240 LCD HAT, GPIO joystick/buttons, removable microSD boot media,
and a SeedSigner-OS-inspired minimal runtime. Pi 3/4/5 variants can be
development or accessibility targets later only if they preserve the same
offline QR, local review, physical approval, and RAM-only custody boundary.

The QR vault pattern is shared across signer families. Its common contracts live
in `nSealr/specs`: QR envelope, review model, review-screen vectors,
`approval_digest`, identity/policy descriptors, signing vectors, and the
feature conformance matrix at
`vectors/features/signer-feature-matrix-v0.json`. This repository implements
the Raspberry/Pi side of that pattern; future ESP32 QR vault firmware belongs
in `nSealr/esp32`. When the Raspberry QR vault and ESP32 QR vault both
support a feature, their final behavior must match the shared `contract_id`
even if current hardware readiness differs.

## Current Capabilities

- Python package and CLI foundation for one-request signing flows.
- v0 `nsealr1:` QR envelope encode/decode.
- NIP-01 event id computation and BIP-340 signing against shared
  `nSealr/specs` fixtures.
- NIP-06 mnemonic derivation for account `0` and account-indexed key recovery,
  checked against the canonical NIP-06 test vector in `nSealr/specs`.
- RAM-only session keyring inputs for the current foundation include manual
  BIP-39 word entry, SeedSigner Standard SeedQR digit streams, SeedSigner
  CompactSeedQR entropy bytes, plain BIP-39 mnemonic text, and Nostr NIP-19
  `nsec` private keys checked against shared `nSealr/specs` vectors. Package
  code now also generates 12- or 24-word BIP-39 sources and standalone
  `nsec`-equivalent private-key sources into the same RAM-only session-source
  boundary, with injected entropy for deterministic tests. Final Pi
  backup/export UI remains pending.
  SeedSigner-compatible import is BIP-39 seed import for NIP-06 Nostr
  derivation; it does not import Bitcoin descriptors, xpubs, PSBTs, or wallet
  policy.
- Secret-hidden session import review for SeedQR/BIP-39 and NIP-19 `nsec`
  sources, checked against shared `nSealr/specs` session-import-review vectors.
  It shows type, label, word count where applicable, and a deterministic
  fingerprint while hiding mnemonic words and raw private-key bytes; it is a
  RAM-load review only, not signing approval.
- The shared `nsealr-account-descriptor-v0` route
  `raspberry_qr_vault` is treated as a stateless-session, manual-only route
  bound to `policy-manual-only-qr-vault` with `persistent_grants: false`.
  The shared `raspberry-qr-sign-event-account-0` route-selection vector keeps
  request routing aligned with that same QR transport and secretless metadata
  contract. This repository must not add policy automation, persistent grants,
  or TROPIC01 to that route.
- Explicit approval gate: `sign_event` requests return `user_rejected` unless
  approval is provided to the CLI or signer API.
- Deterministic event review model for raw kind, created_at, signer author
  pubkey, complete content, and complete structured tags before approval,
  checked against every shared `nSealr/specs` review vector.
- `nsealr-vault review` renders deterministic review JSON from a request without
  requiring a secret key or producing a signature. It uses the same request
  validation as the signing path for host-supplied event fields.
- `nsealr-vault review --output-format screen-json` renders deterministic
  trusted-display page data plus an `approval_digest` for desktop and future
  Pi display simulations.
- `nsealr-vault review --output-format display-frame-json` renders one bounded
  display frame with deterministic line wrapping/truncation for future LCD
  adapter tests, checked against shared `nSealr/specs`
  review-display-frame vectors.
- The core display package can also render complete constrained-display
  detail pages for Event/Content/Tags/Decision, including scroll-window
  indicators, compact line styles, long-value continuation indentation, and
  visible JSON-style escapes for decoded control characters. Unsupported
  glyphs still use explicit `U+XXXX` fallback. These are checked against shared
  `nSealr/specs` review-detail-page vectors and exposed by
  `nsealr-vault review --output-format detail-pages-json` without changing the
  `approval_digest` contract.
- `nsealr-vault sign --approval-digest <hex>` can require the signing request to
  match the previously rendered review-page digest before an approved signature
  is produced.
- Pure-Python physical approval controller for future GPIO adapters. Approval
  is only accepted after the trusted review pages have been traversed to the
  final approve/reject page; rejection remains available before the final page.
- Deterministic review transcript generation for future display/GPIO adapter
  tests, checked against shared `nSealr/specs` review-transcript vectors,
  including detail-mode `Next/Scroll` traversal for long tag windows.
- Hardware-neutral button-driven QR flow boundary for future camera, display,
  and GPIO adapters.
- Composable hardware adapter boundary that keeps QR scanning, trusted display,
  physical button input, and response QR output as separate attach points before
  real Pi drivers are selected.
- SeedSigner-compatible 40-pin GPIO button profile for the Waveshare-style HAT:
  right advances top-level review pages, down scrolls inside long Content/Tags
  pages, center press approves on the Decision page, and KEY1 rejects from any
  page. The profile is testable with injected GPIO and does not claim physical
  acceptance until run on the Pi kit.
- SeedSigner-compatible ST7789 240x240 layout planner for trusted-review
  frames. It produces bounded draw commands for title, page indicator, styled
  body lines, and action hint before a real PIL/spidev display driver exists.
- SeedSigner-compatible driver-facing adapter boundaries for the Pi QR vault:
  an injected camera-frame QR scanner, an ST7789 review display adapter that
  applies the bounded layout commands to an injected draw target, and an ST7789
  response-QR display adapter that renders an injected QR matrix with a quiet
  zone. These are hardware-facing boundaries for Pi bring-up, not completed
  physical acceptance.
- RAM-only secret-provider boundary for the button-driven flow. The key is
  loaded for the signing session before review so the trusted screen can bind
  the displayed author pubkey into the `approval_digest`; signing still only
  occurs after complete review traversal and physical approval.
- CLI `--secret-key-stdin`, `--mnemonic-stdin`, `--mnemonic-words-stdin`,
  `--seedqr-stdin`, `--compact-seedqr-hex-stdin`, and `--nsec-stdin` inputs
  for `sign` and `flow` keep desktop simulations closer to the stateless model
  by avoiding shell arguments and seed files when a caller can provide session
  key material over stdin. The word-by-word, SeedQR, and NIP-19 `nsec` paths
  reuse package-owned seed-entry validators for future camera/display/button
  adapters. These are still development harness inputs, not production
  seed-entry UX.
- Package-owned session import review helpers pin the same secret-hidden
  review pages, source fingerprint, `review_id`, and import approval digest as
  ESP32 for the shared QR-vault RAM-load ceremony.
- `nsealr-vault review-import` exposes that RAM-load ceremony as a desktop
  harness for stdin-fed BIP-39 mnemonic, word-by-word mnemonic, Standard
  SeedQR, CompactSeedQR, and NIP-19 `nsec` sources. It validates the source
  and writes the secret-hidden review only after success; it does not sign,
  derive a NIP-06 key, persist material, or approve later signing.
- Package-owned session import flow for future Pi seed-entry screens. It
  requires local traversal of the secret-hidden import review before loading a
  parsed source into the RAM-only session keyring; rejection and incomplete
  button streams leave the keyring empty. The keyring uses mutable internal
  source slots and wipes them on `clear()` as best-effort Python process
  hygiene.
- Package-owned local session-source generation for future Pi source-creation
  screens. Generated BIP-39 and standalone `nsec`-equivalent sources are
  represented as the same secret-hidden RAM-only session sources as imports;
  the visible backup/export ceremony and physical hardware acceptance remain
  future work.
- RAM-only imported-source secret provider for the existing button-driven
  signing flow. It derives NIP-06 from approved BIP-39/SeedQR sources with an
  explicit account/passphrase or uses an approved NIP-19 `nsec` source, then
  consumes the selected source once without persisting material.
- Hardware-neutral mnemonic seed-entry controller for future Pi display/button
  adapters. It reads BIP-39 words one by one, normalizes and validates the
  English wordlist/checksum, derives the NIP-06 session key as a one-shot
  secret provider, and does not persist the mnemonic.
- Shared nSealr v0 implementation limits for constrained signers, with
  deterministic rejection of applicable invalid signing-request and QR-envelope
  hardening vectors before trusted review or signing.
- QR envelope encoding now enforces the same static decoded-JSON byte limit as
  decoding, so the Raspberry flow does not emit response QR payloads that v0
  readers would immediately reject. It also supports the shared `nsealr1a:`
  animated QR frame set for larger valid responses, with digest, checksum,
  ordering, and frame-count checks before JSON parsing.
- `nsealr-vault flow --button-sequence ...` file-backed physical-button harness
  that refuses approval until every trusted review page has been traversed and
  bounds non-terminal button streams before future GPIO adapters exist.
- `nsealr-vault flow --display-frame-log ...` records the bounded trusted
  display frames shown during a button-driven flow for future display adapter
  acceptance tests.
- `nsealr-vault flow --st7789-layout-log ...` records the SeedSigner-compatible
  240x240 draw commands derived from each displayed frame for future
  Waveshare/ST7789 driver acceptance.
- The button-driven flow result carries the displayed frame/button/decision
  transcript, so adapter harnesses can compare a whole review loop with shared
  `nSealr/specs` review-transcript vectors before real GPIO/display drivers.
- `nsealr-vault flow --review-transcript-log ...` writes that same transcript
  from the file-backed button harness for cross-repo and adapter acceptance
  tests.
- `nsealr-vault flow --review-mode detail` lets the button-driven harness use
  complete Event/Content/Tags/Decision detail pages. `next` advances between
  top-level logical pages, `scroll` moves within long Content or Tags windows,
  and approval is accepted only on the Decision page. The signing
  `approval_digest` remains the shared `screen-pages` digest.
- JSON and QR file input/output for desktop simulation before camera/display
  integration.
- `os/stateless-qr-vault-profile.md` records the future Raspberry image
  acceptance boundary aligned with `nSealr/hardware`: removable microSD,
  wireless disabled or absent, RAM-only custody, no swap during signing, no
  remote access during signing, and no persistent signing-secret storage.
- The hardware target is now explicitly SeedSigner-compatible. The first
  physical target is the available Raspberry Pi Zero; full hardware acceptance
  still requires the SeedSigner-style camera, ST7789 240x240 display HAT, GPIO
  controls, and OS profile smoke evidence.
- `nsealr-vault hardware-probe --out <report.json>` writes a non-destructive
  SeedSigner-compatible Pi Zero probe report for future hardware smoke runs.
  It checks board model, GPIO/SPI/camera Python modules, camera/SPI boot config
  markers, swap state, wireless absence/blocking evidence, and SSH/sshd service
  state without claiming production readiness. The report includes
  `acceptance_blockers` and `human_actions_required` so a later physical Pi run
  can be fixed without guessing what evidence is missing.

## Planned Capabilities

- Raspberry/Pi QR-only signing flow.
- Stateless key/session mode.
- Display review for raw event kind, signer author, full content, full tags,
  and final approve/reject decision.
- SeedSigner-compatible Pi Zero camera/display draw-target integrations and
  physical GPIO/display acceptance runs.
- Verifiable minimal OS image path.

## Initial Layout

- `app/`: signer application code.
- `os/`: image/buildroot or OS integration notes.
- `docs/`: build, hardware, QR, and security documentation.

## Quality Baseline

Run the repository verification loop with:

```sh
make ci
```

Run the desktop CLI simulation with:

```sh
python3 -m nsealr_vault review --request request.qr --review review.json --input-format qr
python3 -m nsealr_vault review --request request.qr --review review-screen.json --input-format qr --output-format screen-json
python3 -m nsealr_vault review --request request.qr --review display-frame.json --input-format qr --output-format display-frame-json --display-page 0
python3 -m nsealr_vault review --request request.qr --review review-detail-pages.json --input-format qr --output-format detail-pages-json
printf '%s\n' '<standard-seedqr-digits>' | python3 -m nsealr_vault review-import --seedqr-stdin --label 'SeedQR session' --out import-review.json
printf '%s\n' '<nsec1...>' | python3 -m nsealr_vault review-import --nsec-stdin --label 'nsec session' --out import-review.json
python3 -m nsealr_vault flow --secret-key <hex> --request request.qr --review review-screen.json --response response.qr --approve
python3 -m nsealr_vault flow --secret-key <hex> --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve
python3 -m nsealr_vault flow --secret-key <hex> --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve --display-frame-log display-frames.json
python3 -m nsealr_vault flow --secret-key <hex> --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve --st7789-layout-log display-layout.json
python3 -m nsealr_vault flow --secret-key <hex> --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve --review-transcript-log review-transcript.json
python3 -m nsealr_vault flow --secret-key <hex> --request request.qr --review review-detail.json --response response.qr --button-sequence next,next,scroll,next,approve --review-mode detail
python3 -m nsealr_vault flow --secret-key <hex> --request request.qr --review review-detail.json --response response.qra --button-sequence next,next,scroll,next,approve --review-mode detail --output-format qr-animated
printf '%s\n' '<hex>' | python3 -m nsealr_vault flow --secret-key-stdin --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve
printf '%s\n' '<mnemonic words>' | python3 -m nsealr_vault flow --mnemonic-stdin --account 0 --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve
printf '%s\n' word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 | python3 -m nsealr_vault flow --mnemonic-words-stdin --mnemonic-word-count 12 --account 0 --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve
printf '%s\n' '<standard-seedqr-digits>' | python3 -m nsealr_vault flow --seedqr-stdin --account 0 --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve
printf '%s\n' '<nsec1...>' | python3 -m nsealr_vault flow --nsec-stdin --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve
python3 -m nsealr_vault sign --secret-key <hex> --request request.qr --response response.qr --input-format qr --output-format qr --approve
printf '%s\n' '<hex>' | python3 -m nsealr_vault sign --secret-key-stdin --request request.qr --response response.qr --input-format qr --output-format qr --approve
python3 -m nsealr_vault sign --secret-key <hex> --request request.qra --response response.qra --input-format qr-animated --output-format qr-animated --approve
python3 -m nsealr_vault sign --secret-key <hex> --request request.qr --response response.qr --input-format qr --output-format qr --approve --approval-digest <hex>
python3 -m nsealr_vault sign --mnemonic-file mnemonic.txt --account 0 --request request.qr --response response.qr --input-format qr --output-format qr --approve
printf '%s\n' '<mnemonic words>' | python3 -m nsealr_vault sign --mnemonic-stdin --account 0 --request request.qr --response response.qr --input-format qr --output-format qr --approve
printf '%s\n' word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 | python3 -m nsealr_vault sign --mnemonic-words-stdin --mnemonic-word-count 12 --account 0 --request request.qr --response response.qr --input-format qr --output-format qr --approve
printf '%s\n' '<standard-seedqr-digits>' | python3 -m nsealr_vault sign --seedqr-stdin --account 0 --request request.qr --response response.qr --input-format qr --output-format qr --approve
printf '%s\n' '<compact-seedqr-hex-bytes>' | python3 -m nsealr_vault sign --compact-seedqr-hex-stdin --account 0 --request request.qr --response response.qr --input-format qr --output-format qr --approve
printf '%s\n' '<nsec1...>' | python3 -m nsealr_vault sign --nsec-stdin --request request.qr --response response.qr --input-format qr --output-format qr --approve
python3 -m nsealr_vault hardware-probe --out hardware-probe.json
```

## License

Raspberry software and tooling are released under the MIT License unless a file
says otherwise. SeedSigner is a design reference, not a license source for
copied code.
