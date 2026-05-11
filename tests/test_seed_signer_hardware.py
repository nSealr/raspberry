from __future__ import annotations

import unittest

from nostrseal_vault.seed_signer_hardware import (
    BOARD_MODE,
    GPIO_LOW,
    GPIO_PUD_UP,
    SEEDSIGNER_40_PIN_BUTTON_PROFILE,
    SeedSignerCameraQrScanner,
    SeedSignerGpioButtonInput,
    SeedSignerSt7789ResponseQrDisplay,
    SeedSignerSt7789ReviewDisplay,
)


class FakeGpio:
    BOARD = "BOARD"
    IN = "IN"
    PUD_UP = "PUD_UP"
    LOW = 0
    HIGH = 1

    def __init__(self, low_pins: set[int] | None = None) -> None:
        self.low_pins = low_pins or set()
        self.mode: str | None = None
        self.setups: list[tuple[int, str, str]] = []

    def setmode(self, mode: str) -> None:
        self.mode = mode

    def setup(self, pin: int, mode: str, pull_up_down: str) -> None:
        self.setups.append((pin, mode, pull_up_down))

    def input(self, pin: int) -> int:
        return self.LOW if pin in self.low_pins else self.HIGH


class FakeFrameSource:
    def __init__(self, frames: list[object]) -> None:
        self.frames = list(frames)

    def capture_frame(self) -> object:
        if not self.frames:
            raise RuntimeError("no more camera frames")
        return self.frames.pop(0)


class FakeQrDecoder:
    def __init__(self, payloads: list[str | None]) -> None:
        self.payloads = list(payloads)
        self.frames: list[object] = []

    def decode_qr(self, frame: object) -> str | None:
        self.frames.append(frame)
        if not self.payloads:
            return None
        return self.payloads.pop(0)


class FakeDrawTarget:
    def __init__(self) -> None:
        self.operations: list[tuple[object, ...]] = []

    def fill_rect(self, x: int, y: int, width: int, height: int, color: str) -> None:
        self.operations.append(("fill_rect", x, y, width, height, color))

    def draw_text(self, text: str, x: int, y: int, scale: int, color: str, max_width: int | None = None) -> None:
        self.operations.append(("draw_text", text, x, y, scale, color, max_width))

    def present(self) -> None:
        self.operations.append(("present",))


class FakeQrMatrixRenderer:
    def __init__(self, matrix: list[list[bool]]) -> None:
        self.matrix = matrix
        self.payloads: list[str] = []

    def render_qr_matrix(self, payload: str) -> list[list[bool]]:
        self.payloads.append(payload)
        return self.matrix


class SeedSignerHardwareTests(unittest.TestCase):
    def test_profile_matches_seedsigner_40_pin_hat_pins(self) -> None:
        profile = SEEDSIGNER_40_PIN_BUTTON_PROFILE

        self.assertEqual(profile.numbering, BOARD_MODE)
        self.assertEqual(profile.key_up, 31)
        self.assertEqual(profile.key_down, 35)
        self.assertEqual(profile.key_left, 29)
        self.assertEqual(profile.key_right, 37)
        self.assertEqual(profile.key_press, 33)
        self.assertEqual(profile.key1, 40)
        self.assertEqual(profile.key2, 38)
        self.assertEqual(profile.key3, 36)
        self.assertEqual(profile.action_pins["next"], (profile.key_right,))
        self.assertEqual(profile.action_pins["scroll"], (profile.key_down,))
        self.assertEqual(profile.action_pins["approve"], (profile.key_press,))
        self.assertEqual(profile.action_pins["reject"], (profile.key1,))

    def test_gpio_input_configures_all_hat_buttons_as_pullups(self) -> None:
        gpio = FakeGpio()

        SeedSignerGpioButtonInput(gpio=gpio, sleep=lambda _seconds: None)

        self.assertEqual(gpio.mode, BOARD_MODE)
        configured = {pin for pin, _mode, _pull in gpio.setups}
        self.assertEqual(configured, set(SEEDSIGNER_40_PIN_BUTTON_PROFILE.all_pins))
        self.assertTrue(all(mode == "IN" and pull == GPIO_PUD_UP for _pin, mode, pull in gpio.setups))

    def test_gpio_input_maps_right_down_press_key1_to_review_actions(self) -> None:
        cases = {
            SEEDSIGNER_40_PIN_BUTTON_PROFILE.key_right: "next",
            SEEDSIGNER_40_PIN_BUTTON_PROFILE.key_down: "scroll",
            SEEDSIGNER_40_PIN_BUTTON_PROFILE.key_press: "approve",
            SEEDSIGNER_40_PIN_BUTTON_PROFILE.key1: "reject",
        }
        for pin, expected in cases.items():
            with self.subTest(pin=pin):
                gpio = FakeGpio({pin})
                buttons = SeedSignerGpioButtonInput(gpio=gpio, sleep=lambda _seconds: None)

                self.assertEqual(buttons.read_review_button(max_polls=1), expected)

    def test_gpio_input_times_out_without_a_pressed_button(self) -> None:
        buttons = SeedSignerGpioButtonInput(gpio=FakeGpio(), sleep=lambda _seconds: None)

        with self.assertRaisesRegex(TimeoutError, "no SeedSigner-compatible button press"):
            buttons.read_review_button(max_polls=2)

    def test_camera_qr_scanner_polls_until_payload_is_decoded(self) -> None:
        frames = FakeFrameSource(["frame-a", "frame-b"])
        decoder = FakeQrDecoder([None, "  nseal1:test-request  "])
        scanner = SeedSignerCameraQrScanner(frame_source=frames, qr_decoder=decoder, sleep=lambda _seconds: None)

        self.assertEqual(scanner.scan_request_qr(max_frames=2), "nseal1:test-request")
        self.assertEqual(decoder.frames, ["frame-a", "frame-b"])

    def test_camera_qr_scanner_times_out_without_payload(self) -> None:
        scanner = SeedSignerCameraQrScanner(
            frame_source=FakeFrameSource(["frame-a", "frame-b"]),
            qr_decoder=FakeQrDecoder([None, None]),
            sleep=lambda _seconds: None,
        )

        with self.assertRaisesRegex(TimeoutError, "no NostrSeal request QR decoded"):
            scanner.scan_request_qr(max_frames=2)

    def test_st7789_review_display_renders_layout_commands_to_target(self) -> None:
        target = FakeDrawTarget()
        display = SeedSignerSt7789ReviewDisplay(target=target)

        display.display_review_frame(
            {"format": "screen-review-v0"},
            0,
            {
                "title": "Event",
                "page_indicator": "Page 1/4",
                "body_lines": ["Kind 1", "Created 1710000000", "Author", "abcdef"],
                "body_line_styles": ["meta", "meta", "meta", "value"],
                "action_hint": "Next",
            },
        )

        self.assertEqual(target.operations[0], ("fill_rect", 0, 0, 240, 240, "black"))
        self.assertIn(("draw_text", "Event", 8, 8, 2, "white", 60), target.operations)
        self.assertIn(("draw_text", "Kind 1", 8, 44, 1, "green", 36), target.operations)
        self.assertEqual(target.operations[-1], ("present",))

    def test_st7789_response_qr_display_renders_centered_matrix(self) -> None:
        target = FakeDrawTarget()
        renderer = FakeQrMatrixRenderer([[True, False], [False, True]])
        display = SeedSignerSt7789ResponseQrDisplay(target=target, qr_renderer=renderer, quiet_zone_modules=1)

        display.emit_response_qr("nseal1:response")

        self.assertEqual(renderer.payloads, ["nseal1:response"])
        self.assertEqual(target.operations[0], ("fill_rect", 0, 0, 240, 240, "black"))
        self.assertEqual(target.operations[1], ("fill_rect", 0, 0, 240, 240, "white"))
        self.assertIn(("fill_rect", 60, 60, 60, 60, "black"), target.operations)
        self.assertIn(("fill_rect", 120, 120, 60, 60, "black"), target.operations)
        self.assertEqual(target.operations[-1], ("present",))

    def test_st7789_response_qr_display_rejects_invalid_matrix(self) -> None:
        target = FakeDrawTarget()
        renderer = FakeQrMatrixRenderer([[True], [False, True]])
        display = SeedSignerSt7789ResponseQrDisplay(target=target, qr_renderer=renderer)

        with self.assertRaisesRegex(ValueError, "QR matrix must be rectangular"):
            display.emit_response_qr("nseal1:response")

    def test_st7789_response_qr_display_requires_square_qr_matrix(self) -> None:
        target = FakeDrawTarget()
        renderer = FakeQrMatrixRenderer([[True, False, True], [False, True, False]])
        display = SeedSignerSt7789ResponseQrDisplay(target=target, qr_renderer=renderer)

        with self.assertRaisesRegex(ValueError, "QR matrix must be square"):
            display.emit_response_qr("nseal1:response")


if __name__ == "__main__":
    unittest.main()
