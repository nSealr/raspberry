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
- Approval rejection tests.
- Approved signing response tests.
- Desktop CLI smoke test for QR request input and QR response output.

## Next Tests

- Review model tests for event kind, content, tags, and warning policy.
- Companion verification of signed output through the file transport.
- Camera/display simulation tests before Raspberry Pi hardware testing.

Hardware tests must record board, camera, display, OS image, commit, and exact
procedure.
