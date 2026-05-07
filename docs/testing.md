# Testing

## Current Baseline

```sh
make ci
```

The baseline runs repository verification, Python unit tests, bytecode
compilation, and `pip check`.

## Implemented Tests

- QR envelope round-trip tests.
- NIP-06 derivation tests against the canonical account `0` shared vector.
- Signing tests against `NostrSeal/specs` fixtures.
- Review model tests against every shared review vector for event kind,
  content preview, tag summary, and warnings.
- Desktop CLI smoke test for QR request review output without a secret key.
- Trusted-display page tests for event, content, tag, warning, and final
  approval-decision pages.
- Approval-digest tests proving an approved signing request is rejected when
  the digest no longer matches the rendered review pages.
- Desktop CLI smoke test for QR request review output as `screen-json`.
- Negative CLI review test proving host-supplied `id` fields are rejected
  before review output is written.
- Approval rejection tests.
- Approved signing response tests.
- Desktop CLI smoke test for QR request input and QR response output.
- Desktop CLI smoke test for QR request signing from a NIP-06 mnemonic file.

## Next Tests

- Companion verification of signed output through the file transport.
- Camera frame input and real display rendering tests before Raspberry Pi
  hardware testing.

Hardware tests must record board, camera, display, OS image, commit, and exact
procedure.
