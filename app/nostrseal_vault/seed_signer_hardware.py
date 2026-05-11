from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Callable, Protocol


BOARD_MODE = "BOARD"
GPIO_INPUT = "IN"
GPIO_LOW = 0
GPIO_PUD_UP = "PUD_UP"
REVIEW_ACTIONS = ("reject", "approve", "next", "scroll")


class GpioLike(Protocol):
    def setmode(self, mode: object) -> None:
        ...

    def setup(self, pin: int, mode: object, pull_up_down: object) -> None:
        ...

    def input(self, pin: int) -> object:
        ...


@dataclass(frozen=True)
class SeedSignerButtonProfile:
    numbering: str
    key_up: int
    key_down: int
    key_left: int
    key_right: int
    key_press: int
    key1: int
    key2: int
    key3: int

    @property
    def all_pins(self) -> tuple[int, ...]:
        return (
            self.key_up,
            self.key_down,
            self.key_left,
            self.key_right,
            self.key_press,
            self.key1,
            self.key2,
            self.key3,
        )

    @property
    def action_pins(self) -> dict[str, tuple[int, ...]]:
        return {
            "next": (self.key_right,),
            "scroll": (self.key_down,),
            "approve": (self.key_press,),
            "reject": (self.key1,),
        }


SEEDSIGNER_40_PIN_BUTTON_PROFILE = SeedSignerButtonProfile(
    numbering=BOARD_MODE,
    key_up=31,
    key_down=35,
    key_left=29,
    key_right=37,
    key_press=33,
    key1=40,
    key2=38,
    key3=36,
)


class SeedSignerGpioButtonInput:
    """GPIO button adapter for the 40-pin SeedSigner/Waveshare LCD HAT layout."""

    def __init__(
        self,
        *,
        gpio: GpioLike,
        profile: SeedSignerButtonProfile = SEEDSIGNER_40_PIN_BUTTON_PROFILE,
        sleep: Callable[[float], None] | None = None,
        poll_delay_s: float = 0.01,
    ) -> None:
        self.gpio = gpio
        self.profile = profile
        self.sleep = sleep or _default_sleep
        self.poll_delay_s = poll_delay_s
        self._configure_gpio()

    def _configure_gpio(self) -> None:
        self.gpio.setmode(getattr(self.gpio, "BOARD", BOARD_MODE))
        input_mode = getattr(self.gpio, "IN", GPIO_INPUT)
        pull_up = getattr(self.gpio, "PUD_UP", GPIO_PUD_UP)
        for pin in self.profile.all_pins:
            self.gpio.setup(pin, input_mode, pull_up_down=pull_up)

    def read_review_button(self, max_polls: int | None = None) -> str:
        polls = 0
        while max_polls is None or polls < max_polls:
            for action in REVIEW_ACTIONS:
                for pin in self.profile.action_pins[action]:
                    if self.gpio.input(pin) == getattr(self.gpio, "LOW", GPIO_LOW):
                        return action
            polls += 1
            self.sleep(self.poll_delay_s)
        raise TimeoutError("no SeedSigner-compatible button press observed")


def create_seed_signer_gpio_button_input() -> SeedSignerGpioButtonInput:
    try:
        gpio = importlib.import_module("RPi.GPIO")
    except ModuleNotFoundError as exc:
        raise RuntimeError("RPi.GPIO is required for SeedSigner-compatible GPIO input") from exc
    return SeedSignerGpioButtonInput(gpio=gpio)


def _default_sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)
