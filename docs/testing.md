# Testing

## Current Baseline

```sh
make ci
```

## Required Tests

- QR request parser tests.
- Review model tests for event kind, content, and tags.
- Signing tests against `NostrSeal/specs` fixtures.
- Companion verification of signed output.
- Desktop simulation smoke test before Raspberry Pi hardware testing.

Hardware tests must record board, camera, display, OS image, commit, and exact
procedure.

