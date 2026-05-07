# Testing

## Current Baseline

```sh
make ci
```

The baseline runs repository verification, Python unit tests, bytecode
compilation, and `pip check`.

## Implemented Tests

- QR envelope round-trip tests.
- Signing tests against `NostrSeal/specs` fixtures.
- Review model tests against every shared review vector for event kind,
  content preview, tag summary, and warnings.
- Desktop CLI smoke test for QR request review output without a secret key.
- Negative CLI review test proving host-supplied `id` fields are rejected
  before review output is written.
- Approval rejection tests.
- Approved signing response tests.
- Desktop CLI smoke test for QR request input and QR response output.

## Next Tests

- Companion verification of signed output through the file transport.
- Camera/display simulation tests before Raspberry Pi hardware testing.

Hardware tests must record board, camera, display, OS image, commit, and exact
procedure.
