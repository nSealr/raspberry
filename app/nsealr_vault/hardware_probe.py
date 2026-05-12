from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable


ReadText = Callable[[Path], str]
FindModule = Callable[[str], bool]


BOOT_CONFIG_PATHS = (
    Path("/boot/config.txt"),
    Path("/boot/firmware/config.txt"),
)


def _default_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _default_find_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _check(check_id: str, status: str, expected: str, observed: str) -> dict[str, str | bool]:
    return {
        "id": check_id,
        "required": True,
        "status": status,
        "expected": expected,
        "observed": observed,
    }


def _clean_model(value: str) -> str:
    return value.replace("\x00", "").strip()


def _read_first(paths: tuple[Path, ...], read_text: ReadText) -> tuple[Path | None, str | None]:
    for path in paths:
        try:
            return path, read_text(path)
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            continue
    return None, None


def _module_check(check_id: str, module_names: tuple[str, ...], find_module: FindModule) -> dict[str, str | bool]:
    available = [name for name in module_names if find_module(name)]
    status = "pass" if available else "blocked"
    return _check(
        check_id,
        status,
        "Python module available: " + " or ".join(module_names),
        ", ".join(available) if available else "module not found",
    )


def _boot_config_check(check_id: str, marker_options: tuple[str, ...], read_text: ReadText) -> dict[str, str | bool]:
    path, value = _read_first(BOOT_CONFIG_PATHS, read_text)
    if value is None or path is None:
        return _check(check_id, "blocked", "boot config readable", "no supported boot config path found")
    normalized = value.replace(" ", "").lower()
    matched = [marker for marker in marker_options if marker.replace(" ", "").lower() in normalized]
    return _check(
        check_id,
        "pass" if matched else "fail",
        "boot config contains " + " or ".join(marker_options),
        f"{path}: " + (", ".join(matched) if matched else "required marker missing"),
    )


def run_seed_signer_compatibility_probe(
    *,
    read_text: ReadText = _default_read_text,
    find_module: FindModule = _default_find_module,
) -> dict[str, object]:
    """Build a non-destructive SeedSigner-compatible Raspberry probe report."""

    checks: list[dict[str, str | bool]] = []

    try:
        model = _clean_model(read_text(Path("/proc/device-tree/model")))
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        model = ""
    model_lower = model.lower()
    if not model:
        checks.append(
            _check("board_model", "blocked", "Raspberry Pi Zero-class board model", "board model not readable")
        )
    elif "raspberry pi zero" in model_lower:
        checks.append(_check("board_model", "pass", "Raspberry Pi Zero-class board model", model))
    else:
        checks.append(_check("board_model", "fail", "Raspberry Pi Zero-class board model", model))

    checks.append(_module_check("gpio_python_module", ("RPi.GPIO",), find_module))
    checks.append(_module_check("spi_python_module", ("spidev",), find_module))
    checks.append(_module_check("camera_python_module", ("picamera", "picamera2"), find_module))
    checks.append(_boot_config_check("boot_camera_enabled", ("start_x=1", "camera_auto_detect=1"), read_text))
    checks.append(_boot_config_check("boot_spi_enabled", ("dtparam=spi=on",), read_text))

    try:
        swaps = read_text(Path("/proc/swaps")).strip().splitlines()
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        checks.append(_check("swap_disabled", "blocked", "no active swap entries", "/proc/swaps not readable"))
    else:
        active_swaps = [line for line in swaps[1:] if line.strip()]
        checks.append(
            _check(
                "swap_disabled",
                "pass" if not active_swaps else "fail",
                "no active swap entries",
                "no active swap entries" if not active_swaps else "; ".join(active_swaps),
            )
        )

    if "raspberry pi zero" in model_lower and "zero w" not in model_lower and "zero 2" not in model_lower:
        wireless_status = "pass"
        wireless_observed = "Pi Zero non-wireless target model"
    elif model:
        wireless_status = "blocked"
        wireless_observed = "wireless mitigation evidence required for this board model"
    else:
        wireless_status = "blocked"
        wireless_observed = "board model not readable"
    checks.append(
        _check(
            "wireless_absent_or_blocked",
            wireless_status,
            "wireless absent or blocked before signing",
            wireless_observed,
        )
    )

    ready = all(check["status"] == "pass" for check in checks)
    return {
        "format": "nsealr-raspberry-seedsigner-compatibility-probe-v0",
        "target": "raspberry-pi-zero-seedsigner-compatible-qr-vault",
        "ready_for_hardware_acceptance": ready,
        "production_signing_enabled": False,
        "persistent_secret_present": False,
        "tropic01_used": False,
        "checks": checks,
        "limitations": [
            "This is a non-destructive development probe, not a completed hardware acceptance report.",
            "A passing probe does not prove QR scan quality, trusted display readability, GPIO approval UX, or production security.",
            "The Raspberry/Pi stateless QR vault remains RAM-only and must not add persistent secret storage or TROPIC01.",
        ],
    }
