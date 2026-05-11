from __future__ import annotations

import unittest

from nostrseal_vault.seed_signer_hardware import (
    BOARD_MODE,
    GPIO_LOW,
    GPIO_PUD_UP,
    SEEDSIGNER_40_PIN_BUTTON_PROFILE,
    SeedSignerGpioButtonInput,
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


if __name__ == "__main__":
    unittest.main()
