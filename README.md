# NostrSeal Raspberry

Raspberry/Pi software for NostrSeal signing devices.

This repository owns the Raspberry/Pi implementation family. The first line is
the SeedSigner-style QR vault flow for Nostr: scan an unsigned event request,
review on a trusted display, approve with physical controls, sign BIP-340, and
return a signed-event QR.

The QR vault pattern is shared across signer families. Its common contracts live
in `NostrSeal/specs`: QR envelope, review model, review-screen vectors,
`approval_digest`, and signing vectors. This repository implements the
Raspberry/Pi side of that pattern; future ESP32 QR vault firmware belongs in
`NostrSeal/esp32`.

## Current Capabilities

- Python package and CLI foundation for one-request signing flows.
- v0 `nseal1:` QR envelope encode/decode.
- NIP-01 event id computation and BIP-340 signing against shared
  `NostrSeal/specs` fixtures.
- NIP-06 mnemonic derivation for account `0` and account-indexed key recovery,
  checked against the canonical NIP-06 test vector in `NostrSeal/specs`.
- Explicit approval gate: `sign_event` requests return `user_rejected` unless
  approval is provided to the CLI or signer API.
- Deterministic event review model for raw kind, created_at, signer author
  pubkey, complete content, and complete structured tags before approval,
  checked against every shared `NostrSeal/specs` review vector.
- `nseal-vault review` renders deterministic review JSON from a request without
  requiring a secret key or producing a signature. It uses the same request
  validation as the signing path for host-supplied event fields.
- `nseal-vault review --output-format screen-json` renders deterministic
  trusted-display page data plus an `approval_digest` for desktop and future
  Pi display simulations.
- `nseal-vault review --output-format display-frame-json` renders one bounded
  display frame with deterministic line wrapping/truncation for future LCD
  adapter tests, checked against shared `NostrSeal/specs`
  review-display-frame vectors.
- The core display package can also render complete constrained-display
  detail pages for Event/Content/Tags/Decision, including scroll-window
  indicators, compact line styles, long-value continuation indentation, and
  explicit `U+XXXX` fallback for unsupported glyphs. These are checked against
  shared `NostrSeal/specs` review-detail-page vectors without changing the
  `approval_digest` contract.
- `nseal-vault sign --approval-digest <hex>` can require the signing request to
  match the previously rendered review-page digest before an approved signature
  is produced.
- Pure-Python physical approval controller for future GPIO adapters. Approval
  is only accepted after the trusted review pages have been traversed to the
  final approve/reject page; rejection remains available before the final page.
- Deterministic review transcript generation for future display/GPIO adapter
  tests, checked against shared `NostrSeal/specs` review-transcript vectors.
- Hardware-neutral button-driven QR flow boundary for future camera, display,
  and GPIO adapters.
- RAM-only secret-provider boundary for the button-driven flow. The key is
  loaded for the signing session before review so the trusted screen can bind
  the displayed author pubkey into the `approval_digest`; signing still only
  occurs after complete review traversal and physical approval.
- Shared NostrSeal v0 implementation limits for constrained signers, with
  deterministic rejection of applicable invalid signing-request and QR-envelope
  hardening vectors before trusted review or signing.
- `nseal-vault flow --button-sequence ...` file-backed physical-button harness
  that refuses approval until every trusted review page has been traversed and
  bounds non-terminal button streams before future GPIO adapters exist.
- `nseal-vault flow --display-frame-log ...` records the bounded trusted
  display frames shown during a button-driven flow for future display adapter
  acceptance tests.
- The button-driven flow result carries the displayed frame/button/decision
  transcript, so adapter harnesses can compare a whole review loop with shared
  `NostrSeal/specs` review-transcript vectors before real GPIO/display drivers.
- `nseal-vault flow --review-transcript-log ...` writes that same transcript
  from the file-backed button harness for cross-repo and adapter acceptance
  tests.
- JSON and QR file input/output for desktop simulation before camera/display
  integration.

## Planned Capabilities

- Raspberry/Pi QR-only signing flow.
- Stateless key/session mode.
- Display review for raw event kind, signer author, full content, full tags,
  and final approve/reject decision.
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
python3 -m nostrseal_vault review --request request.qr --review review.json --input-format qr
python3 -m nostrseal_vault review --request request.qr --review review-screen.json --input-format qr --output-format screen-json
python3 -m nostrseal_vault review --request request.qr --review display-frame.json --input-format qr --output-format display-frame-json --display-page 0
python3 -m nostrseal_vault flow --secret-key <hex> --request request.qr --review review-screen.json --response response.qr --approve
python3 -m nostrseal_vault flow --secret-key <hex> --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve
python3 -m nostrseal_vault flow --secret-key <hex> --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve --display-frame-log display-frames.json
python3 -m nostrseal_vault flow --secret-key <hex> --request request.qr --review review-screen.json --response response.qr --button-sequence next,next,next,approve --review-transcript-log review-transcript.json
python3 -m nostrseal_vault sign --secret-key <hex> --request request.qr --response response.qr --input-format qr --output-format qr --approve
python3 -m nostrseal_vault sign --secret-key <hex> --request request.qr --response response.qr --input-format qr --output-format qr --approve --approval-digest <hex>
python3 -m nostrseal_vault sign --mnemonic-file mnemonic.txt --account 0 --request request.qr --response response.qr --input-format qr --output-format qr --approve
```

## License

Raspberry software and tooling are released under the MIT License unless a file
says otherwise. SeedSigner is a design reference, not a license source for
copied code.
