from __future__ import annotations

import unittest

from nsealr_vault.seed_signer_hardware import (
    BOARD_MODE,
    GPIO_LOW,
    GPIO_PUD_UP,
    PiCameraJpegFrameSource,
    PillowSt7789DrawTarget,
    PythonQrcodeMatrixRenderer,
    PyzbarQrDecoder,
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


class ReleasingGpio(FakeGpio):
    def __init__(self, pressed_pin: int) -> None:
        super().__init__()
        self.pressed_pin = pressed_pin
        self.pressed_reads = 0

    def input(self, pin: int) -> int:
        if pin != self.pressed_pin:
            return self.HIGH
        self.pressed_reads += 1
        return self.LOW if self.pressed_reads == 1 else self.HIGH


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


class FakePillowImage:
    def __init__(self, mode: str, size: tuple[int, int], color: object) -> None:
        self.mode = mode
        self.size = size
        self.color = color
        self.operations: list[tuple[object, ...]] = []


class FakePillowImageModule:
    def new(self, mode: str, size: tuple[int, int], color: object) -> FakePillowImage:
        return FakePillowImage(mode, size, color)


class FakePillowDraw:
    def __init__(self, image: FakePillowImage) -> None:
        self.image = image

    def rectangle(self, box: tuple[int, int, int, int], fill: object) -> None:
        self.image.operations.append(("rectangle", box, fill))

    def text(self, position: tuple[int, int], text: str, fill: object, font: object) -> None:
        self.image.operations.append(("text", position, text, fill, font))


class FakePillowImageDrawModule:
    def Draw(self, image: FakePillowImage) -> FakePillowDraw:
        return FakePillowDraw(image)


class FakeQrMatrixRenderer:
    def __init__(self, matrix: list[list[bool]]) -> None:
        self.matrix = matrix
        self.payloads: list[str] = []

    def render_qr_matrix(self, payload: str) -> list[list[bool]]:
        self.payloads.append(payload)
        return self.matrix


class FakeQrCode:
    def __init__(self, matrix: list[list[bool]]) -> None:
        self.matrix = matrix
        self.data: list[str] = []
        self.made_fit: bool | None = None

    def add_data(self, payload: str) -> None:
        self.data.append(payload)

    def make(self, fit: bool) -> None:
        self.made_fit = fit

    def get_matrix(self) -> list[list[bool]]:
        return self.matrix


class FakeQrcodeModule:
    def __init__(self, qr: FakeQrCode) -> None:
        self.qr = qr
        self.kwargs: dict[str, object] | None = None

    def QRCode(self, **kwargs: object) -> FakeQrCode:
        self.kwargs = kwargs
        return self.qr


class FakePiCamera:
    def __init__(self) -> None:
        self.captures: list[str] = []
        self.closed = False

    def capture(self, stream: object, format: str) -> None:
        self.captures.append(format)
        stream.write(b"jpeg-frame")

    def close(self) -> None:
        self.closed = True


class FakeBarcode:
    def __init__(self, data: bytes | str) -> None:
        self.data = data


class FakePyzbarModule:
    def __init__(self, barcodes: list[FakeBarcode]) -> None:
        self.barcodes = barcodes
        self.calls: list[tuple[object, object]] = []

    def decode(self, image: object, symbols: object) -> list[FakeBarcode]:
        self.calls.append((image, symbols))
        return self.barcodes


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
                buttons = SeedSignerGpioButtonInput(
                    gpio=gpio,
                    sleep=lambda _seconds: None,
                    require_release=False,
                )

                self.assertEqual(buttons.read_review_button(max_polls=1), expected)

    def test_gpio_input_waits_for_button_release_before_returning_action(self) -> None:
        gpio = ReleasingGpio(SEEDSIGNER_40_PIN_BUTTON_PROFILE.key_right)
        buttons = SeedSignerGpioButtonInput(gpio=gpio, sleep=lambda _seconds: None)

        self.assertEqual(buttons.read_review_button(max_polls=1), "next")
        self.assertEqual(gpio.pressed_reads, 2)

    def test_gpio_input_times_out_when_button_release_is_not_observed(self) -> None:
        gpio = FakeGpio({SEEDSIGNER_40_PIN_BUTTON_PROFILE.key_right})
        buttons = SeedSignerGpioButtonInput(
            gpio=gpio,
            sleep=lambda _seconds: None,
            release_timeout_polls=2,
        )

        with self.assertRaisesRegex(TimeoutError, "button release not observed"):
            buttons.read_review_button(max_polls=1)

    def test_gpio_input_times_out_without_a_pressed_button(self) -> None:
        buttons = SeedSignerGpioButtonInput(gpio=FakeGpio(), sleep=lambda _seconds: None)

        with self.assertRaisesRegex(TimeoutError, "no SeedSigner-compatible button press"):
            buttons.read_review_button(max_polls=2)

    def test_camera_qr_scanner_polls_until_payload_is_decoded(self) -> None:
        frames = FakeFrameSource(["frame-a", "frame-b"])
        decoder = FakeQrDecoder([None, "  nsealr1:test-request  "])
        scanner = SeedSignerCameraQrScanner(frame_source=frames, qr_decoder=decoder, sleep=lambda _seconds: None)

        self.assertEqual(scanner.scan_request_qr(max_frames=2), "nsealr1:test-request")
        self.assertEqual(decoder.frames, ["frame-a", "frame-b"])

    def test_camera_qr_scanner_times_out_without_payload(self) -> None:
        scanner = SeedSignerCameraQrScanner(
            frame_source=FakeFrameSource(["frame-a", "frame-b"]),
            qr_decoder=FakeQrDecoder([None, None]),
            sleep=lambda _seconds: None,
        )

        with self.assertRaisesRegex(TimeoutError, "no nSealr request QR decoded"):
            scanner.scan_request_qr(max_frames=2)

    def test_picamera_frame_source_captures_jpeg_bytes(self) -> None:
        camera = FakePiCamera()
        source = PiCameraJpegFrameSource(camera=camera)

        self.assertEqual(source.capture_frame(), b"jpeg-frame")
        self.assertEqual(camera.captures, ["jpeg"])

        source.close()
        self.assertTrue(camera.closed)

    def test_pyzbar_decoder_returns_first_utf8_qr_payload(self) -> None:
        pyzbar = FakePyzbarModule([FakeBarcode(b"nsealr1:request")])
        decoder = PyzbarQrDecoder(pyzbar=pyzbar, qrcode_symbol="QRCODE")

        self.assertEqual(decoder.decode_qr("pil-image"), "nsealr1:request")
        self.assertEqual(pyzbar.calls, [("pil-image", ["QRCODE"])])

    def test_pyzbar_decoder_returns_none_when_no_qr_is_found(self) -> None:
        decoder = PyzbarQrDecoder(pyzbar=FakePyzbarModule([]), qrcode_symbol="QRCODE")

        self.assertIsNone(decoder.decode_qr("pil-image"))

    def test_pyzbar_decoder_rejects_non_utf8_payload(self) -> None:
        decoder = PyzbarQrDecoder(pyzbar=FakePyzbarModule([FakeBarcode(b"\xff")]), qrcode_symbol="QRCODE")

        with self.assertRaisesRegex(ValueError, "QR payload is not UTF-8"):
            decoder.decode_qr("pil-image")

    def test_pillow_st7789_draw_target_renders_to_presenter(self) -> None:
        presented: list[FakePillowImage] = []
        target = PillowSt7789DrawTarget(
            present_image=presented.append,
            image_module=FakePillowImageModule(),
            image_draw_module=FakePillowImageDrawModule(),
            font_factory=lambda scale: f"font-{scale}",
        )

        target.fill_rect(1, 2, 3, 4, "green")
        target.draw_text("Ready", 5, 6, 2, "white", max_width=100)
        target.present()

        self.assertEqual(len(presented), 1)
        self.assertEqual(presented[0].size, (240, 240))
        self.assertEqual(
            presented[0].operations,
            [
                ("rectangle", (1, 2, 3, 5), (0, 255, 0)),
                ("text", (5, 6), "Ready", (255, 255, 255), "font-2"),
            ],
        )

    def test_pillow_st7789_draw_target_clips_text_to_max_width(self) -> None:
        presented: list[FakePillowImage] = []
        target = PillowSt7789DrawTarget(
            present_image=presented.append,
            image_module=FakePillowImageModule(),
            image_draw_module=FakePillowImageDrawModule(),
            font_factory=lambda scale: f"font-{scale}",
        )

        target.draw_text("abcdef", 0, 0, 1, "yellow", max_width=12)
        target.present()

        self.assertEqual(presented[0].operations, [("text", (0, 0), "ab", (255, 255, 0), "font-1")])

    def test_python_qrcode_renderer_returns_boolean_matrix(self) -> None:
        qr = FakeQrCode([[True, False], [False, True]])
        qrcode_module = FakeQrcodeModule(qr)
        renderer = PythonQrcodeMatrixRenderer(qrcode_module=qrcode_module)

        self.assertEqual(renderer.render_qr_matrix("nsealr1:response"), [[True, False], [False, True]])
        self.assertEqual(qr.data, ["nsealr1:response"])
        self.assertTrue(qr.made_fit)
        self.assertEqual(qrcode_module.kwargs, {"border": 0})

    def test_python_qrcode_renderer_rejects_non_boolean_matrix(self) -> None:
        qr = FakeQrCode([[True, 1]])  # type: ignore[list-item]
        renderer = PythonQrcodeMatrixRenderer(qrcode_module=FakeQrcodeModule(qr))

        with self.assertRaisesRegex(ValueError, "QR matrix values must be booleans"):
            renderer.render_qr_matrix("nsealr1:response")

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

        display.emit_response_qr("nsealr1:response")

        self.assertEqual(renderer.payloads, ["nsealr1:response"])
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
            display.emit_response_qr("nsealr1:response")

    def test_st7789_response_qr_display_requires_square_qr_matrix(self) -> None:
        target = FakeDrawTarget()
        renderer = FakeQrMatrixRenderer([[True, False, True], [False, True, False]])
        display = SeedSignerSt7789ResponseQrDisplay(target=target, qr_renderer=renderer)

        with self.assertRaisesRegex(ValueError, "QR matrix must be square"):
            display.emit_response_qr("nsealr1:response")


if __name__ == "__main__":
    unittest.main()
