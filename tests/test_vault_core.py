import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from nostrseal_vault.crypto import sign_event, verify_schnorr_signature
from nostrseal_vault.qr import decode_qr_envelope, encode_qr_envelope
from nostrseal_vault.signer import sign_request


ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT.parent / "specs"
KEY = json.loads((SPECS / "vectors/keys/test-key-1.json").read_text(encoding="utf-8"))
BASIC_VECTOR = json.loads((SPECS / "vectors/events/kind-1-basic.json").read_text(encoding="utf-8"))
BASIC_REQUEST = json.loads((SPECS / "examples/request-kind-1-basic.json").read_text(encoding="utf-8"))


class VaultCoreTests(unittest.TestCase):
    def assert_valid_signed_event(self, signed: dict) -> None:
        expected = dict(BASIC_VECTOR["signed_event"])
        expected.pop("sig")
        actual = dict(signed)
        signature = actual.pop("sig")

        self.assertEqual(actual, expected)
        self.assertTrue(verify_schnorr_signature(signed["pubkey"], signed["id"], signature))

    def test_qr_envelope_round_trip_uses_shared_prefix(self) -> None:
        envelope = encode_qr_envelope(BASIC_REQUEST)

        self.assertTrue(envelope.startswith("nseal1:"))
        self.assertNotIn("=", envelope)
        self.assertEqual(decode_qr_envelope(envelope), BASIC_REQUEST)

    def test_sign_event_matches_shared_vector(self) -> None:
        signed = sign_event(BASIC_REQUEST["params"]["event_template"], KEY["secret_key"])

        self.assert_valid_signed_event(signed)

    def test_sign_request_requires_explicit_approval(self) -> None:
        response = sign_request(BASIC_REQUEST, KEY["secret_key"], approved=False)

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["request_id"], BASIC_REQUEST["request_id"])
        self.assertEqual(response["error"]["code"], "user_rejected")

    def test_sign_request_returns_signed_event_when_approved(self) -> None:
        response = sign_request(BASIC_REQUEST, KEY["secret_key"], approved=True)

        self.assertEqual(response["ok"], True)
        self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_signs_qr_request_and_outputs_qr_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "sign",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event(response["result"]["event"])


if __name__ == "__main__":
    unittest.main()
