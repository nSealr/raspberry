# NostrSeal Vault

Pi Zero / SeedSigner-style QR vault for Nostr signing.

This repository will adapt the SeedSigner-style air-gapped workflow to Nostr:
scan an unsigned event request, review on a trusted display, approve with
physical controls, sign BIP-340, and return a signed-event QR.

## Planned Capabilities

- QR-only signing flow.
- Stateless key/session mode.
- NIP-06 mnemonic support.
- NIP-01 event id computation and BIP-340 signing.
- Display review for event kind, content, tags, and risk warnings.
- Verifiable minimal OS image path.

## Initial Layout

- `app/`: signer application code.
- `os/`: image/buildroot or OS integration notes.
- `docs/`: build, hardware, QR, and security documentation.

## License Plan

Vault software should use GPL-3.0 or another strong copyleft license compatible
with reused SeedSigner concepts and dependencies.

