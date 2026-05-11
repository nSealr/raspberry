# Testing

## Current Baseline

```sh
make ci
```

The baseline runs repository verification, Python unit tests, bytecode
compilation, and `pip check`.

`make setup` installs the local package with pip's in-tree build mode when the
local pip still exposes that feature flag, so lab integration logs do not
include the legacy out-of-tree build deprecation warning from older Python 3.9
virtual environments. Newer pip releases that already use in-tree builds by
default are left unchanged.

## Implemented Tests

- QR envelope round-trip tests.
- QR envelope encode-side limit tests proving static v0 QR writers reject
  payloads that would exceed `max_static_qr_decoded_json_bytes` before emitting
  an envelope.
- Animated QR frame-set tests against the shared specs vector, including
  reversed input order, missing-frame rejection, checksum rejection, and
  `nseal-vault` CLI `qr-animated` request/response output.
- NIP-06 derivation tests against the canonical account `0` shared vector.
- Signing tests against `NostrSeal/specs` fixtures.
- Review model tests against every shared review vector for raw event kind,
  created_at, signer author pubkey, complete content, and complete structured
  tags.
- Desktop CLI smoke test for QR request review output without a secret key.
- Trusted-display page tests for event, content, tag, and final
  approval-decision pages.
- Trusted-display screen review tests against every shared
  `NostrSeal/specs` review-screen vector.
- Bounded trusted-display frame tests for deterministic title truncation,
  body-line wrapping, page indicators, and action hints before real display
  drivers exist.
- Trusted-display frame conformance tests against shared `NostrSeal/specs`
  review-display-frame vectors.
- Trusted-display detail-page conformance tests against shared
  `NostrSeal/specs` review-detail-page vectors, covering complete physical
  Event/Content/Tags/Decision pages, scroll-window indicators, compact line
  styles, continuation indentation, explicit codepoint fallback, and unchanged
  approval digests.
- Physical-button approval session tests that require all trusted-review pages
  to be traversed before approval while allowing early rejection.
- Review transcript tests against shared `NostrSeal/specs` vectors, covering
  displayed frame, button sequence, terminal decision, and approval state.
- Detail-mode review transcript tests against shared `NostrSeal/specs` vectors,
  covering `Next/Scroll` traversal across long tag windows without changing the
  `screen-pages` approval digest.
- Approval-digest tests proving an approved signing request is rejected when
  the digest no longer matches the rendered review pages.
- Desktop CLI smoke test for QR request review output as `screen-json`.
- Desktop CLI smoke test for QR request review output as one bounded
  `display-frame-json` frame.
- Desktop CLI smoke test for QR request review output as complete
  `detail-pages-json` constrained-display pages.
- Negative CLI review test proving host-supplied `id` fields are rejected
  before review output is written.
- Approval rejection tests.
- Approved signing response tests.
- Hardware-agnostic QR vault flow test with in-memory camera, display/button,
  and response-QR I/O.
- Button-driven QR vault flow tests proving page-by-page traversal before
  approval, early rejection without signing, and bounded failure for
  non-terminal button streams.
- RAM-only secret-provider tests proving future stateless Pi adapters load
  session key material before review to derive the displayed author pubkey,
  while still refusing to sign unless complete review traversal and physical
  approval succeed.
- BIP-39 seed-entry boundary tests proving word-by-word mnemonic input is
  normalized, checked against the English wordlist/checksum, consumed once, and
  usable as the NIP-06 session secret provider for the button-driven flow.
- Button-driven display-frame log tests proving future display adapters receive
  bounded frames before physical-style input is consumed.
- Button-driven flow transcript tests proving the displayed frame/button/
  decision trace can match shared `NostrSeal/specs` review-transcript vectors
  under transcript-compatible display limits.
- CLI transcript-log tests proving the file-backed button harness can export
  that trace for cross-repo integration and future adapter acceptance tests.
- Detail button-flow tests proving complete Event/Content/Tags/Decision pages
  can use top-level `next` navigation, intra-page `scroll`, preserved
  detail-page indicators/body styles, and the CLI `--review-mode detail` path
  without changing the shared `screen-pages` approval digest.
- File-backed adapter tests proving request scanning, review JSON writes,
  display-frame log writes, button exhaustion, and response QR output are owned
  by package code rather than private CLI classes.
- Composed adapter tests proving future scanner, trusted-display,
  physical-button, and response-QR components can plug into the button-driven
  QR flow without bypassing review traversal or approval-digest binding.
- File-backed `nseal-vault flow` CLI test proving the hardware-style path writes
  screen-review JSON and a signed response QR.
- Cross-repo lab integration verifies the file-backed QR flow output through
  `NostrSeal/companion` `nseal verify-response`, proving the signed response QR
  can be checked by the host-side companion contract.
- Desktop CLI smoke test for QR request input and QR response output.
- Desktop CLI smoke test for QR request signing from a NIP-06 mnemonic file.
- Desktop CLI smoke tests for stdin-fed secret key and stdin-fed NIP-06
  mnemonic inputs on both `sign` and button-driven `flow`, keeping development
  harnesses closer to the stateless RAM-only target than shell-argument or
  seed-file-only paths.
- Desktop CLI smoke tests for word-by-word BIP-39 stdin input on both `sign`
  and button-driven `flow`, proving the package-owned seed-entry validator is
  reachable through the CLI without introducing seed files or persistent
  storage.
- Shared NostrSeal v0 implementation-limit conformance test against the
  `NostrSeal/specs` limits profile.
- Shared pre-signing invalid-vector rejection for unsafe event templates,
  resource-limit violations, and malformed QR requests where the Raspberry
  parser owns the boundary.
- Project tooling test requiring `make setup` to use pip in-tree builds for
  clean cross-repo integration logs.
- OS profile note test requiring future Raspberry image work to preserve the
  stateless QR vault operating boundary: removable microSD, no swap, no remote
  access, RAM-only custody, no persistent signing-secret storage, and no
  TROPIC01 requirement.

## Next Tests

- SeedSigner-compatible Pi Zero board/runtime smoke planning against the
  available Raspberry Pi Zero.
- Camera frame input through a Pi Zero-compatible OV5647/ZeroCam path, real
  display rendering on a Waveshare-compatible ST7789 240x240 display HAT, and
  GPIO approval/navigation tests before Raspberry Pi hardware acceptance
  testing.
- Real hardware adapter tests against the existing transcript oracle once
  camera, display, and GPIO drivers are selected.

Hardware tests must record board, camera, display, OS image, commit, and exact
procedure.

## Single-Repository CI

Unit tests prefer the sibling `NostrSeal/specs` repository when the full local
workspace is present. GitHub Actions checks out `NostrSeal/raspberry` by itself,
so tests fall back to fixture snapshots under `tests/fixtures/specs` in
single-repository CI. Cross-repository drift remains guarded by
`NostrSeal/lab` integration, which runs against the live sibling repositories.

The Raspberry QR vault must remain stateless and RAM-only while consuming those
hardening vectors. Rejection conformance must not introduce persistent secret
storage or TROPIC01 dependencies.
