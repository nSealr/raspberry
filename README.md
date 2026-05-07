# NostrSeal Vault

Pi Zero / SeedSigner-style QR vault for Nostr signing.

This repository will adapt the SeedSigner-style air-gapped workflow to Nostr:
scan an unsigned event request, review on a trusted display, approve with
physical controls, sign BIP-340, and return a signed-event QR.

## Current Capabilities

- Python package and CLI foundation for one-request signing flows.
- v0 `nseal1:` QR envelope encode/decode.
- NIP-01 event id computation and BIP-340 signing against shared
  `NostrSeal/specs` fixtures.
- Explicit approval gate: `sign_event` requests return `user_rejected` unless
  approval is provided to the CLI or signer API.
- Deterministic event review model for kind, content preview, tag summary, and
  warnings before approval, checked against every shared `NostrSeal/specs`
  review vector.
- `nseal-vault review` renders deterministic review JSON from a request without
  requiring a secret key or producing a signature. It uses the same request
  validation as the signing path for host-supplied event fields.
- JSON and QR file input/output for desktop simulation before camera/display
  integration.

## Planned Capabilities

- QR-only signing flow.
- Stateless key/session mode.
- NIP-06 mnemonic support.
- Display review for event kind, content, tags, and risk warnings.
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
python3 -m nostrseal_vault sign --secret-key <hex> --request request.qr --response response.qr --input-format qr --output-format qr --approve
```

## License

Vault software and tooling are released under the MIT License unless a file says
otherwise. SeedSigner is a design reference, not a license source for copied
code.
