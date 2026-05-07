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
- Trusted-display screen review tests against every shared
  `NostrSeal/specs` review-screen vector.
- Physical-button approval session tests that require all trusted-review pages
  to be traversed before approval while allowing early rejection.
- Review transcript tests against shared `NostrSeal/specs` vectors, covering
  displayed frame, button sequence, terminal decision, and approval state.
- Approval-digest tests proving an approved signing request is rejected when
  the digest no longer matches the rendered review pages.
- Desktop CLI smoke test for QR request review output as `screen-json`.
- Negative CLI review test proving host-supplied `id` fields are rejected
  before review output is written.
- Approval rejection tests.
- Approved signing response tests.
- Hardware-agnostic QR vault flow test with in-memory camera, display/button,
  and response-QR I/O.
- Button-driven QR vault flow tests proving page-by-page traversal before
  approval and early rejection without signing.
- File-backed `nseal-vault flow` CLI test proving the hardware-style path writes
  screen-review JSON and a signed response QR.
- Desktop CLI smoke test for QR request input and QR response output.
- Desktop CLI smoke test for QR request signing from a NIP-06 mnemonic file.

## Next Tests

- Companion verification of signed output through the file transport.
- Camera frame input, real display rendering, and GPIO approval tests before
  Raspberry Pi hardware acceptance testing.
- Cross-check the Raspberry QR vault flow against the shared `NostrSeal/specs`
  review-screen, review-transcript, and `approval_digest` vectors.

Hardware tests must record board, camera, display, OS image, commit, and exact
procedure.

## Single-Repository CI

Unit tests prefer the sibling `NostrSeal/specs` repository when the full local
workspace is present. GitHub Actions checks out `NostrSeal/raspberry` by itself,
so tests fall back to fixture snapshots under `tests/fixtures/specs` in
single-repository CI. Cross-repository drift remains guarded by
`NostrSeal/lab` integration, which runs against the live sibling repositories.
