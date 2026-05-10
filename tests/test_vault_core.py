import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from nostrseal_vault.crypto import sign_event, verify_schnorr_signature
from nostrseal_vault.adapters import ComposedButtonQrVaultIO, FileButtonQrVaultIO, FileQrVaultIO
from nostrseal_vault.controls import ReviewControlSession, review_transcript_for_screen_review
from nostrseal_vault.display import (
    DisplayFrameLimits,
    ReviewDetailPageLimits,
    approval_digest_for_request,
    render_display_frame,
    render_review_detail_pages,
    render_review_pages,
    screen_review_for_request,
)
from nostrseal_vault.hardware_flow import (
    run_button_qr_vault_flow,
    run_button_qr_vault_flow_with_secret_provider,
    run_qr_vault_flow,
)
from nostrseal_vault.nip06 import derive_nip06_secret
from nostrseal_vault.qr import decode_qr_envelope, encode_qr_envelope
from nostrseal_vault.review import review_event_template
from nostrseal_vault.signer import sign_request


ROOT = Path(__file__).resolve().parents[1]


def specs_dir() -> Path:
    sibling = ROOT.parent / "specs"
    if sibling.exists():
        return sibling
    return ROOT / "tests/fixtures/specs"


SPECS = specs_dir()
KEY = json.loads((SPECS / "vectors/keys/test-key-1.json").read_text(encoding="utf-8"))
NIP06_KEY = json.loads((SPECS / "vectors/keys/nip06-account-0-leader.json").read_text(encoding="utf-8"))
BASIC_VECTOR = json.loads((SPECS / "vectors/events/kind-1-basic.json").read_text(encoding="utf-8"))
BASIC_REQUEST = json.loads((SPECS / "examples/request-kind-1-basic.json").read_text(encoding="utf-8"))
TAGGED_REQUEST = json.loads((SPECS / "examples/request-kind-1-tags.json").read_text(encoding="utf-8"))
REVIEW_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/review").glob("*.json"))
]
SCREEN_REVIEW_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/review-screens").glob("*.json"))
]
REVIEW_TRANSCRIPT_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/review-transcripts").glob("*.json"))
]
DISPLAY_FRAME_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/review-display-frames").glob("*.json"))
]
REVIEW_DETAIL_PAGE_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/review-detail-pages").glob("*.json"))
]
TAGGED_REVIEW_VECTOR = json.loads((SPECS / "vectors/review/kind-1-tags.json").read_text(encoding="utf-8"))
LIMIT_PROFILE = json.loads((SPECS / "vectors/limits/nseal-v0.json").read_text(encoding="utf-8"))
INVALID_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/invalid").glob("*.json"))
]


class MemoryQrVaultIO:
    def __init__(self, request_qr: str, approved: bool) -> None:
        self.request_qr = request_qr
        self.approved = approved
        self.screen_review: dict | None = None
        self.response_qr: str | None = None

    def scan_request_qr(self) -> str:
        return self.request_qr

    def show_review(self, screen_review: dict) -> bool:
        self.screen_review = screen_review
        return self.approved

    def emit_response_qr(self, response_qr: str) -> None:
        self.response_qr = response_qr


class MemoryButtonQrVaultIO:
    def __init__(self, request_qr: str, buttons: list[str]) -> None:
        self.request_qr = request_qr
        self.buttons = list(buttons)
        self.displayed_pages: list[tuple[int, str]] = []
        self.response_qr: str | None = None

    def scan_request_qr(self) -> str:
        return self.request_qr

    def display_review_frame(self, screen_review: dict, page_index: int, frame: dict) -> None:
        self.displayed_pages.append((page_index, frame["title"]))

    def read_review_button(self) -> str:
        if not self.buttons:
            raise RuntimeError("no more buttons")
        return self.buttons.pop(0)

    def emit_response_qr(self, response_qr: str) -> None:
        self.response_qr = response_qr


class NextOnlyButtonQrVaultIO:
    def __init__(self, request_qr: str) -> None:
        self.request_qr = request_qr
        self.displayed_pages: list[tuple[int, str]] = []
        self.response_qr: str | None = None

    def scan_request_qr(self) -> str:
        return self.request_qr

    def display_review_frame(self, screen_review: dict, page_index: int, frame: dict) -> None:
        self.displayed_pages.append((page_index, frame["title"]))

    def read_review_button(self) -> str:
        return "next"

    def emit_response_qr(self, response_qr: str) -> None:
        self.response_qr = response_qr


class FakeQrScanner:
    def __init__(self, request_qr: str) -> None:
        self.request_qr = request_qr
        self.calls = 0

    def scan_request_qr(self) -> str:
        self.calls += 1
        return self.request_qr


class FakeReviewDisplay:
    def __init__(self) -> None:
        self.frames: list[tuple[int, str]] = []

    def display_review_frame(self, screen_review: dict, page_index: int, frame: dict) -> None:
        self.frames.append((page_index, frame["title"]))


class FakeButtonInput:
    def __init__(self, buttons: list[str]) -> None:
        self.buttons = list(buttons)

    def read_review_button(self) -> str:
        if not self.buttons:
            raise RuntimeError("no more fake buttons")
        return self.buttons.pop(0)


class FakeResponseQrDisplay:
    def __init__(self) -> None:
        self.response_qr: str | None = None

    def emit_response_qr(self, response_qr: str) -> None:
        self.response_qr = response_qr


class ProjectToolingTests(unittest.TestCase):
    def test_setup_uses_in_tree_build_to_keep_pip_logs_clean(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn("install --use-feature=in-tree-build --help", makefile)
        self.assertIn("--use-feature=in-tree-build", makefile)
        self.assertIn("$$PIP_IN_TREE_BUILD", makefile)


class VaultCoreTests(unittest.TestCase):
    def assert_valid_signed_event(self, signed: dict) -> None:
        expected = dict(BASIC_VECTOR["signed_event"])
        expected.pop("sig")
        actual = dict(signed)
        signature = actual.pop("sig")

        self.assertEqual(actual, expected)
        self.assertTrue(verify_schnorr_signature(signed["pubkey"], signed["id"], signature))

    def assert_valid_signed_event_for_pubkey(self, signed: dict, public_key: str) -> None:
        self.assertEqual(signed["pubkey"], public_key)
        self.assertTrue(verify_schnorr_signature(signed["pubkey"], signed["id"], signed["sig"]))

    def test_qr_envelope_round_trip_uses_shared_prefix(self) -> None:
        envelope = encode_qr_envelope(BASIC_REQUEST)

        self.assertTrue(envelope.startswith("nseal1:"))
        self.assertNotIn("=", envelope)
        self.assertEqual(decode_qr_envelope(envelope), BASIC_REQUEST)

    def test_limits_match_shared_v0_profile(self) -> None:
        from nostrseal_vault.limits import NOSTRSEAL_V0_LIMITS

        self.assertEqual(LIMIT_PROFILE["name"], "nostrseal-v0")
        self.assertEqual(NOSTRSEAL_V0_LIMITS, LIMIT_PROFILE["limits"])

    def test_qr_decoder_rejects_shared_invalid_qr_vectors(self) -> None:
        vectors = [vector for vector in INVALID_VECTORS if vector["category"] == "qr-envelope"]
        self.assertGreater(len(vectors), 0)

        for vector in vectors:
            with self.subTest(vector=vector["name"]):
                with self.assertRaisesRegex(ValueError, vector["expected_error"]):
                    decode_qr_envelope(vector["envelope"])

    def test_signer_rejects_shared_invalid_signing_request_vectors(self) -> None:
        vectors = [vector for vector in INVALID_VECTORS if vector["category"] == "signing-request"]
        self.assertGreater(len(vectors), 0)

        for vector in vectors:
            with self.subTest(vector=vector["name"]):
                response = sign_request(vector["request"], KEY["secret_key"], approved=True)

                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "invalid_request")
                self.assertIn(vector["expected_error"], response["error"]["message"])

    def test_sign_event_matches_shared_vector(self) -> None:
        signed = sign_event(BASIC_REQUEST["params"]["event_template"], KEY["secret_key"])

        self.assert_valid_signed_event(signed)

    def test_nip06_derivation_matches_shared_account_zero_vector(self) -> None:
        derived = derive_nip06_secret(
            NIP06_KEY["mnemonic"],
            passphrase=NIP06_KEY["passphrase"],
            account=NIP06_KEY["account"],
        )

        self.assertEqual(derived, NIP06_KEY["secret_key"])

    def test_review_model_preserves_raw_event_fields_and_author(self) -> None:
        review = review_event_template(TAGGED_REQUEST["params"]["event_template"])

        self.assertEqual(review["kind"], 1)
        self.assertEqual(review["created_at"], 1710000060)
        self.assertEqual(review["author_pubkey"], KEY["public_key"])
        self.assertEqual(review["content"], "NostrSeal fixture: tagged kind 1 event.")
        self.assertEqual(review["content_utf8_bytes"], 39)
        self.assertEqual(review["tag_count"], 2)
        self.assertEqual(review["tags"], TAGGED_REQUEST["params"]["event_template"]["tags"])

    def test_review_model_matches_shared_review_vectors(self) -> None:
        for vector in REVIEW_VECTORS:
            self.assertEqual(
                review_event_template(vector["request"]["params"]["event_template"]),
                vector["review"],
            )

    def test_review_pages_prioritize_raw_event_content_tags_and_decision(self) -> None:
        review = review_event_template(TAGGED_REQUEST["params"]["event_template"])

        pages = render_review_pages(review)

        self.assertEqual(
            pages,
            [
                {
                    "title": "Event",
                    "lines": ["Kind 1", "Created 1710000060", "Author", KEY["public_key"]],
                    "action": "next",
                },
                {
                    "title": "Content",
                    "lines": ["NostrSeal fixture: tagged kind 1 event."],
                    "action": "next",
                },
                {
                    "title": "Tags",
                    "lines": [
                        "Tag 1/2",
                        "p",
                        KEY["public_key"],
                        "",
                        "mention",
                        "Tag 2/2",
                        "t",
                        "nostrseal",
                    ],
                    "action": "next",
                },
                {
                    "title": "Decision",
                    "lines": ["Approve signing only if all pages match."],
                    "action": "approve_or_reject",
                },
            ],
        )

    def test_review_pages_always_end_with_approval_decision(self) -> None:
        review = review_event_template(BASIC_REQUEST["params"]["event_template"])

        pages = render_review_pages(review)

        self.assertEqual(pages[-1]["title"], "Decision")
        self.assertEqual(pages[-1]["lines"], ["Approve signing only if all pages match."])
        self.assertEqual(pages[-1]["action"], "approve_or_reject")

    def test_screen_review_binds_digest_to_request_and_pages(self) -> None:
        screen_review = screen_review_for_request(TAGGED_REVIEW_VECTOR["request"])

        self.assertEqual(screen_review["format"], "screen-pages")
        self.assertEqual(screen_review["request_id"], TAGGED_REVIEW_VECTOR["request"]["request_id"])
        self.assertRegex(screen_review["approval_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            screen_review["approval_digest"],
            approval_digest_for_request(TAGGED_REVIEW_VECTOR["request"]),
        )
        self.assertEqual(screen_review["pages"], render_review_pages(TAGGED_REVIEW_VECTOR["review"]))

    def test_screen_review_matches_shared_review_screen_vectors(self) -> None:
        for vector in SCREEN_REVIEW_VECTORS:
            self.assertEqual(screen_review_for_request(vector["request"]), vector["screen_review"])

    def test_review_transcripts_match_shared_vectors(self) -> None:
        self.assertEqual(
            [vector["name"] for vector in REVIEW_TRANSCRIPT_VECTORS],
            ["kind-1-basic-approve", "kind-1-basic-reject"],
        )
        for vector in REVIEW_TRANSCRIPT_VECTORS:
            request = decode_qr_envelope(vector["qr_envelope"])
            screen_review = screen_review_for_request(request)

            self.assertEqual(screen_review["approval_digest"], vector["approval_digest"])
            self.assertEqual(
                review_transcript_for_screen_review(screen_review, vector["buttons"]),
                vector["transcript"],
            )

    def test_display_frame_wraps_and_bounds_long_review_lines(self) -> None:
        vector = next(item for item in REVIEW_VECTORS if item["name"] == "kind-1-long-events-many-tags")
        screen_review = screen_review_for_request(vector["request"])

        frame = render_display_frame(
            screen_review,
            page_index=1,
            limits=DisplayFrameLimits(max_title_chars=12, max_body_lines=3, max_line_chars=20),
        )

        self.assertEqual(frame["title"], "Content")
        self.assertEqual(frame["page_indicator"], f"Page 2/{len(screen_review['pages'])}")
        self.assertEqual(frame["action_hint"], "Next")
        self.assertLessEqual(len(frame["body_lines"]), 3)
        self.assertTrue(all(len(line) <= 20 for line in frame["body_lines"]))
        self.assertTrue(frame["body_lines"][-1].endswith("..."))

    def test_display_frame_rejects_invalid_display_limits(self) -> None:
        screen_review = screen_review_for_request(BASIC_REQUEST)

        with self.assertRaisesRegex(ValueError, "display limits must be positive"):
            render_display_frame(screen_review, page_index=0, limits=DisplayFrameLimits(max_line_chars=0))

    def test_display_frames_match_shared_vectors(self) -> None:
        self.assertCountEqual(
            [vector["name"] for vector in DISPLAY_FRAME_VECTORS],
            [
                "kind-1-long-content-page-1-20x3",
                "kind-1-unicode-boundary-content-4x3",
            ],
        )
        for vector in DISPLAY_FRAME_VECTORS:
            source = json.loads(
                (SPECS / f"vectors/review/{vector['source_review_vector']}.json").read_text(encoding="utf-8")
            )

            frame = render_display_frame(
                screen_review_for_request(source["request"]),
                page_index=vector["page_index"],
                limits=DisplayFrameLimits(**vector["limits"]),
            )

            self.assertEqual(frame, vector["frame"])

    def test_review_detail_pages_match_shared_vectors(self) -> None:
        self.assertCountEqual(
            [vector["name"] for vector in REVIEW_DETAIL_PAGE_VECTORS],
            [
                "kind-1-long-events-many-tags-t-display-s3",
                "kind-1-tags-t-display-s3",
                "kind-1-unicode-boundary-t-display-s3",
            ],
        )
        for vector in REVIEW_DETAIL_PAGE_VECTORS:
            source = json.loads(
                (SPECS / f"vectors/review/{vector['source_review_vector']}.json").read_text(encoding="utf-8")
            )
            review = review_event_template(source["request"]["params"]["event_template"])

            self.assertEqual(
                render_review_detail_pages(review, limits=ReviewDetailPageLimits(**vector["limits"])),
                vector["pages"],
            )
            self.assertEqual(approval_digest_for_request(source["request"]), vector["approval_digest"])

    def test_physical_approval_requires_viewing_all_review_pages(self) -> None:
        session = ReviewControlSession(screen_review_for_request(TAGGED_REQUEST))

        self.assertEqual(session.current_page["title"], "Event")
        self.assertFalse(session.can_approve)
        with self.assertRaises(ValueError):
            session.approve()

        while session.current_page["action"] != "approve_or_reject":
            self.assertIsNone(session.handle_button("next"))

        self.assertEqual(session.current_page["title"], "Decision")
        self.assertTrue(session.can_approve)
        self.assertTrue(session.handle_button("approve"))

    def test_physical_rejection_is_available_before_final_page(self) -> None:
        session = ReviewControlSession(screen_review_for_request(TAGGED_REQUEST))

        self.assertFalse(session.handle_button("reject"))
        self.assertTrue(session.rejected)
        self.assertFalse(session.approved)

    def test_physical_approval_rejects_invalid_review_page_order(self) -> None:
        screen_review = screen_review_for_request(BASIC_REQUEST)
        screen_review["pages"][0] = dict(screen_review["pages"][0], action="approve_or_reject")

        with self.assertRaises(ValueError):
            ReviewControlSession(screen_review)

    def test_review_model_does_not_infer_unknown_kind_or_long_content_warnings(self) -> None:
        review = review_event_template(
            {
                "created_at": 1710000000,
                "kind": 30078,
                "tags": [],
                "content": "x" * 420,
            }
        )

        self.assertEqual(review["kind"], 30078)
        self.assertEqual(review["content"], "x" * 420)
        self.assertEqual(review["content_utf8_bytes"], 420)
        self.assertNotIn("kind_name", review)
        self.assertNotIn("warnings", review)

    def test_sign_request_requires_explicit_approval(self) -> None:
        response = sign_request(BASIC_REQUEST, KEY["secret_key"], approved=False)

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["request_id"], BASIC_REQUEST["request_id"])
        self.assertEqual(response["error"]["code"], "user_rejected")

    def test_sign_request_returns_signed_event_when_approved(self) -> None:
        response = sign_request(BASIC_REQUEST, KEY["secret_key"], approved=True)

        self.assertEqual(response["ok"], True)
        self.assert_valid_signed_event(response["result"]["event"])

    def test_sign_request_rejects_mismatched_approval_digest(self) -> None:
        response = sign_request(BASIC_REQUEST, KEY["secret_key"], approved=True, approval_digest="00" * 32)

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["request_id"], BASIC_REQUEST["request_id"])
        self.assertEqual(response["error"]["code"], "approval_digest_mismatch")

        signed = sign_request(
            BASIC_REQUEST,
            KEY["secret_key"],
            approved=True,
            approval_digest=approval_digest_for_request(BASIC_REQUEST),
        )
        self.assertEqual(signed["ok"], True)
        self.assert_valid_signed_event(signed["result"]["event"])

    def test_qr_vault_flow_binds_display_digest_before_signing(self) -> None:
        hardware = MemoryQrVaultIO(encode_qr_envelope(BASIC_REQUEST), approved=True)

        result = run_qr_vault_flow(hardware, KEY["secret_key"])

        self.assertEqual(hardware.screen_review, screen_review_for_request(BASIC_REQUEST))
        self.assertEqual(result.approval_digest, hardware.screen_review["approval_digest"])
        self.assertTrue(result.approved)
        self.assertIsNotNone(hardware.response_qr)
        response = decode_qr_envelope(hardware.response_qr)
        self.assert_valid_signed_event(response["result"]["event"])

    def test_file_qr_vault_io_writes_review_and_response_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review.json"
            response_path = Path(temp_root) / "response.qr"
            response_qr = encode_qr_envelope({"version": 1, "request_id": "req-file-io", "ok": False})
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST) + "\n", encoding="utf-8")

            adapter = FileQrVaultIO(request_path, review_path, response_path, approved=True)

            self.assertEqual(adapter.scan_request_qr(), encode_qr_envelope(BASIC_REQUEST))
            self.assertTrue(adapter.show_review(screen_review_for_request(BASIC_REQUEST)))
            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), screen_review_for_request(BASIC_REQUEST))
            adapter.emit_response_qr(response_qr)
            self.assertEqual(response_path.read_text(encoding="utf-8"), response_qr + "\n")

    def test_file_button_qr_vault_io_records_display_frames_and_buttons(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review.json"
            response_path = Path(temp_root) / "response.qr"
            frame_log_path = Path(temp_root) / "display-frames.json"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST) + "\n", encoding="utf-8")
            screen_review = screen_review_for_request(BASIC_REQUEST)
            frame = render_display_frame(screen_review, 0)

            adapter = FileButtonQrVaultIO(
                request_path,
                review_path,
                response_path,
                ["next", "reject"],
                display_frame_log=frame_log_path,
            )

            self.assertEqual(adapter.scan_request_qr(), encode_qr_envelope(BASIC_REQUEST))
            adapter.display_review_frame(screen_review, 0, frame)
            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), screen_review)
            self.assertEqual(json.loads(frame_log_path.read_text(encoding="utf-8")), [frame])
            self.assertEqual(adapter.read_review_button(), "next")
            self.assertEqual(adapter.read_review_button(), "reject")
            with self.assertRaisesRegex(RuntimeError, "button sequence ended before approval or rejection"):
                adapter.read_review_button()

    def test_composed_button_qr_vault_io_delegates_to_adapter_boundaries(self) -> None:
        scanner = FakeQrScanner(encode_qr_envelope(BASIC_REQUEST))
        display = FakeReviewDisplay()
        buttons = FakeButtonInput(["next", "next", "next", "approve"])
        response_display = FakeResponseQrDisplay()
        adapter = ComposedButtonQrVaultIO(
            scanner=scanner,
            review_display=display,
            button_input=buttons,
            response_display=response_display,
        )

        result = run_button_qr_vault_flow(adapter, KEY["secret_key"])

        self.assertEqual(scanner.calls, 1)
        self.assertEqual(display.frames, [(0, "Event"), (1, "Content"), (2, "Tags"), (3, "Decision")])
        self.assertTrue(result.approved)
        self.assertIsNotNone(response_display.response_qr)
        response = decode_qr_envelope(response_display.response_qr)
        self.assert_valid_signed_event(response["result"]["event"])

    def test_button_qr_vault_flow_requires_page_traversal_before_approval(self) -> None:
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(TAGGED_REQUEST), ["next", "next", "next", "approve"])

        result = run_button_qr_vault_flow(hardware, KEY["secret_key"])

        self.assertEqual(hardware.displayed_pages, [(0, "Event"), (1, "Content"), (2, "Tags"), (3, "Decision")])
        self.assertEqual(result.approval_digest, screen_review_for_request(TAGGED_REQUEST)["approval_digest"])
        self.assertTrue(result.approved)
        self.assertIsNotNone(hardware.response_qr)
        response = decode_qr_envelope(hardware.response_qr)
        self.assert_valid_signed_event_for_pubkey(response["result"]["event"], KEY["public_key"])

    def test_button_qr_vault_flow_allows_early_rejection(self) -> None:
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(BASIC_REQUEST), ["reject"])

        result = run_button_qr_vault_flow(hardware, KEY["secret_key"])

        self.assertEqual(hardware.displayed_pages, [(0, "Event")])
        self.assertFalse(result.approved)
        response = decode_qr_envelope(hardware.response_qr)
        self.assertEqual(response["ok"], False)
        self.assertEqual(response["error"]["code"], "user_rejected")

    def test_button_qr_vault_flow_uses_secret_provider_for_approved_session_author(self) -> None:
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(TAGGED_REQUEST), ["next", "next", "next", "approve"])
        provider_calls: list[str] = []

        def secret_provider() -> str:
            provider_calls.append("loaded")
            return KEY["secret_key"]

        result = run_button_qr_vault_flow_with_secret_provider(hardware, secret_provider)

        self.assertEqual(provider_calls, ["loaded"])
        self.assertTrue(result.approved)
        response = decode_qr_envelope(hardware.response_qr)
        self.assert_valid_signed_event_for_pubkey(response["result"]["event"], KEY["public_key"])

    def test_button_qr_vault_flow_loads_key_before_rejection_to_bind_author(self) -> None:
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(BASIC_REQUEST), ["reject"])
        provider_calls: list[str] = []

        def secret_provider() -> str:
            provider_calls.append("loaded")
            return KEY["secret_key"]

        result = run_button_qr_vault_flow_with_secret_provider(hardware, secret_provider)

        self.assertEqual(provider_calls, ["loaded"])
        self.assertFalse(result.approved)
        response = decode_qr_envelope(hardware.response_qr)
        self.assertEqual(response["ok"], False)
        self.assertEqual(response["error"]["code"], "user_rejected")

    def test_button_qr_vault_flow_rejects_non_terminal_button_stream(self) -> None:
        hardware = NextOnlyButtonQrVaultIO(encode_qr_envelope(BASIC_REQUEST))

        with self.assertRaisesRegex(RuntimeError, "button review flow did not reach approval or rejection"):
            run_button_qr_vault_flow(hardware, KEY["secret_key"], max_button_steps=5)

        self.assertEqual(len(hardware.displayed_pages), 5)
        self.assertEqual(hardware.displayed_pages[-1], (3, "Decision"))
        self.assertIsNone(hardware.response_qr)

    def test_button_qr_vault_flow_requires_positive_step_limit(self) -> None:
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(BASIC_REQUEST), ["reject"])

        with self.assertRaisesRegex(ValueError, "button review flow max steps must be positive"):
            run_button_qr_vault_flow(hardware, KEY["secret_key"], max_button_steps=0)

        self.assertEqual(hardware.displayed_pages, [])
        self.assertIsNone(hardware.response_qr)

    def test_button_qr_vault_flow_matches_shared_review_transcript_vectors(self) -> None:
        for vector in REVIEW_TRANSCRIPT_VECTORS:
            hardware = MemoryButtonQrVaultIO(vector["qr_envelope"], list(vector["buttons"]))

            result = run_button_qr_vault_flow(
                hardware,
                KEY["secret_key"],
                display_limits=DisplayFrameLimits(max_line_chars=64),
            )

            self.assertEqual(result.review_transcript, vector["transcript"])
            self.assertEqual(result.approval_digest, vector["approval_digest"])
            self.assertEqual(result.approved, vector["transcript"][-1]["approved_for_signing"])

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

    def test_cli_signs_qr_request_from_nip06_mnemonic_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            mnemonic_path = Path(temp_root) / "mnemonic.txt"
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            mnemonic_path.write_text(NIP06_KEY["mnemonic"] + "\n", encoding="utf-8")
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "sign",
                    "--mnemonic-file",
                    str(mnemonic_path),
                    "--account",
                    str(NIP06_KEY["account"]),
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
            self.assert_valid_signed_event_for_pubkey(response["result"]["event"], NIP06_KEY["public_key"])

    def test_cli_reviews_qr_request_without_secret_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review.json"
            request_path.write_text(encode_qr_envelope(TAGGED_REVIEW_VECTOR["request"]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--input-format",
                    "qr",
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), TAGGED_REVIEW_VECTOR["review"])

    def test_cli_review_can_write_screen_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            request_path.write_text(encode_qr_envelope(TAGGED_REVIEW_VECTOR["request"]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "screen-json",
                ],
                cwd=ROOT,
                check=True,
            )

            review_output = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review_output["format"], "screen-pages")
            self.assertEqual(review_output["request_id"], TAGGED_REVIEW_VECTOR["request"]["request_id"])
            self.assertRegex(review_output["approval_digest"], r"^[0-9a-f]{64}$")
            self.assertEqual(review_output["pages"][-1]["action"], "approve_or_reject")

    def test_cli_review_can_bind_explicit_author_pubkey(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "screen-json",
                    "--author-pubkey",
                    NIP06_KEY["public_key"],
                ],
                cwd=ROOT,
                check=True,
            )

            review_output = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review_output["pages"][0]["lines"], ["Kind 1", "Created 1710000000", "Author", NIP06_KEY["public_key"]])

    def test_cli_review_can_write_bounded_display_frame_json(self) -> None:
        vector = next(item for item in REVIEW_VECTORS if item["name"] == "kind-1-long-events-many-tags")
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            frame_path = Path(temp_root) / "display-frame.json"
            request_path.write_text(encode_qr_envelope(vector["request"]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(frame_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "display-frame-json",
                    "--display-page",
                    "1",
                    "--max-line-chars",
                    "20",
                    "--max-body-lines",
                    "3",
                ],
                cwd=ROOT,
                check=True,
            )

            frame = json.loads(frame_path.read_text(encoding="utf-8"))
            self.assertEqual(frame["title"], "Content")
            self.assertLessEqual(len(frame["body_lines"]), 3)
            self.assertTrue(all(len(line) <= 20 for line in frame["body_lines"]))
            self.assertTrue(frame["body_lines"][-1].endswith("..."))

    def test_cli_review_can_write_detail_pages_json(self) -> None:
        vector = next(item for item in REVIEW_DETAIL_PAGE_VECTORS if item["name"] == "kind-1-tags-t-display-s3")
        source = json.loads((SPECS / f"vectors/review/{vector['source_review_vector']}.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            detail_pages_path = Path(temp_root) / "review-detail-pages.json"
            request_path.write_text(encode_qr_envelope(source["request"]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(detail_pages_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "detail-pages-json",
                    "--max-title-chars",
                    str(vector["limits"]["max_title_chars"]),
                    "--max-line-chars",
                    str(vector["limits"]["max_line_chars"]),
                    "--max-body-lines",
                    str(vector["limits"]["max_body_lines"]),
                    "--max-compact-line-chars",
                    str(vector["limits"]["max_compact_line_chars"]),
                    "--max-compact-body-lines",
                    str(vector["limits"]["max_compact_body_lines"]),
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertEqual(json.loads(detail_pages_path.read_text(encoding="utf-8")), vector["pages"])

    def test_cli_flow_writes_review_screen_and_signed_response_qr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--approve",
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), screen_review_for_request(BASIC_REQUEST))
            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_flow_accepts_button_sequence_for_physical_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,next,next,approve",
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), screen_review_for_request(BASIC_REQUEST))
            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_flow_rejects_early_button_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "approve",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("approval requires viewing every review page", result.stderr)
            self.assertFalse(response_path.exists())

    def test_cli_flow_can_write_display_frame_log_for_button_sequence(self) -> None:
        vector = next(item for item in REVIEW_VECTORS if item["name"] == "kind-1-long-events-many-tags")
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            frame_log_path = Path(temp_root) / "display-frames.json"
            request_path.write_text(encode_qr_envelope(vector["request"]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,reject",
                    "--display-frame-log",
                    str(frame_log_path),
                    "--max-line-chars",
                    "20",
                    "--max-body-lines",
                    "3",
                ],
                cwd=ROOT,
                check=True,
            )

            frames = json.loads(frame_log_path.read_text(encoding="utf-8"))
            self.assertEqual([frame["title"] for frame in frames], ["Event", "Content"])
            self.assertLessEqual(len(frames[1]["body_lines"]), 3)
            self.assertTrue(all(len(line) <= 20 for line in frames[1]["body_lines"]))
            self.assertTrue(frames[1]["body_lines"][-1].endswith("..."))

    def test_cli_flow_can_write_review_transcript_log_for_button_sequence(self) -> None:
        vector = next(item for item in REVIEW_TRANSCRIPT_VECTORS if item["name"] == "kind-1-basic-approve")
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            transcript_log_path = Path(temp_root) / "review-transcript.json"
            request_path.write_text(vector["qr_envelope"], encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    ",".join(vector["buttons"]),
                    "--review-transcript-log",
                    str(transcript_log_path),
                    "--max-line-chars",
                    "64",
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertEqual(json.loads(transcript_log_path.read_text(encoding="utf-8")), vector["transcript"])

    def test_cli_review_rejects_host_supplied_event_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.json"
            review_path = Path(temp_root) / "review.json"
            request = json.loads(json.dumps(TAGGED_REVIEW_VECTOR["request"]))
            request["params"]["event_template"]["id"] = "00" * 32
            request_path.write_text(json.dumps(request), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nostrseal_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("event_template contains forbidden fields", result.stderr)
            self.assertFalse(review_path.exists())


if __name__ == "__main__":
    unittest.main()
