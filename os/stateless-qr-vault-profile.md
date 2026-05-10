# Raspberry Stateless QR Vault OS Profile

This directory records the Raspberry/Pi operating-profile requirements for the
stateless QR vault line. The machine-checkable source of truth lives in
`NostrSeal/hardware` at
`kits/reference-raspberry-qr-vault/os-profile.json`; this file is the
Raspberry implementation note that future image work must follow.

This is not a downloadable OS image. It is a pre-image acceptance profile for
future Buildroot, Raspberry Pi OS Lite, or SeedSigner-OS-inspired work.

## Required Boundary

- Boot from removable microSD media.
- Keep signing key material RAM-only for each signing session.
- Require disabled or physically absent wireless before signing.
- Require no swap during signing, so session key material cannot be paged to
  boot media.
- Require no remote access during signing. SSH, remote login, serial consoles,
  and temporary setup interfaces must be disabled or removed before an
  acceptance run.
- Keep the QR vault stateless: no persistent signing-secret storage on boot
  media or attached storage.
- Preserve QR-only request input and QR-only signed-event output for the
  high-assurance flow.

## Acceptance Evidence

Future Raspberry hardware reports must record:

- board variant and wireless hardware status;
- Wi-Fi/Bluetooth blocked or absent evidence;
- swap status evidence;
- SSH and remote-login disabled evidence;
- no persistent signing secret after shutdown;
- power-cycle evidence showing an unfinished signing session is lost.

## Non-Goals

- This profile does not add camera, display, or GPIO drivers.
- This profile does not add persistent key storage.
- This profile does not add or require TROPIC01.
- This profile does not make a production security claim.
