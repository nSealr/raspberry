from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mnemonic import Mnemonic

from .nip06 import derive_nip06_secret


VALID_MNEMONIC_WORD_COUNTS = (12, 15, 18, 21, 24)
_ENGLISH_MNEMONIC = Mnemonic("english")
_ENGLISH_WORDLIST = frozenset(_ENGLISH_MNEMONIC.wordlist)
_ENGLISH_WORDS = tuple(_ENGLISH_MNEMONIC.wordlist)
SEEDQR_WORD_COUNTS = (12, 24)
COMPACT_SEEDQR_BYTE_LENGTHS = {
    16: 12,
    32: 24,
}
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_CHARSET_REV = {char: index for index, char in enumerate(BECH32_CHARSET)}


class MnemonicWordInput(Protocol):
    def read_mnemonic_word(self, word_index: int, word_count: int) -> str:
        """Return one user-entered BIP-39 word for a RAM-only signing session."""


def normalize_mnemonic_words(words: list[str] | tuple[str, ...]) -> str:
    normalized = [word.strip().lower() for word in words]
    if any(not word for word in normalized):
        raise ValueError("mnemonic words must not be empty")
    if len(normalized) not in VALID_MNEMONIC_WORD_COUNTS:
        counts = ", ".join(str(count) for count in VALID_MNEMONIC_WORD_COUNTS)
        raise ValueError(f"mnemonic word count must be one of {counts}")

    unknown = [word for word in normalized if word not in _ENGLISH_WORDLIST]
    if unknown:
        raise ValueError(f"mnemonic word is not in the BIP-39 English wordlist: {unknown[0]}")

    mnemonic = " ".join(normalized)
    if not _ENGLISH_MNEMONIC.check(mnemonic):
        raise ValueError("mnemonic failed BIP-39 checksum validation")
    return mnemonic


def mnemonic_from_standard_seedqr(value: str) -> str:
    seedqr = "".join(value.split())
    if not seedqr:
        raise ValueError("SeedQR digit stream must not be empty")
    if not seedqr.isdigit():
        raise ValueError("SeedQR digit stream must contain only digits")
    if len(seedqr) % 4 != 0:
        raise ValueError("SeedQR digit stream length must be divisible by four")
    word_count = len(seedqr) // 4
    if word_count not in SEEDQR_WORD_COUNTS:
        counts = ", ".join(str(count) for count in SEEDQR_WORD_COUNTS)
        raise ValueError(f"SeedQR word count must be one of {counts}")

    words: list[str] = []
    for offset in range(0, len(seedqr), 4):
        index = int(seedqr[offset:offset + 4])
        if index >= len(_ENGLISH_WORDS):
            raise ValueError("SeedQR word index is outside the BIP-39 English wordlist")
        words.append(_ENGLISH_WORDS[index])
    return normalize_mnemonic_words(words)


def mnemonic_from_compact_seedqr(value: bytes) -> str:
    if len(value) not in COMPACT_SEEDQR_BYTE_LENGTHS:
        allowed = ", ".join(str(length) for length in sorted(COMPACT_SEEDQR_BYTE_LENGTHS))
        raise ValueError(f"CompactSeedQR byte length must be one of {allowed}")
    return normalize_mnemonic_words(_ENGLISH_MNEMONIC.to_mnemonic(value).split())


def _bech32_polymod(values: list[int]) -> int:
    generators = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index, generator in enumerate(generators):
            if (top >> index) & 1:
                checksum ^= generator
    return checksum


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(char) >> 5 for char in hrp] + [0] + [ord(char) & 31 for char in hrp]


def _bech32_decode(value: str) -> tuple[str, list[int]]:
    candidate = value.strip()
    if candidate != candidate.lower():
        raise ValueError("nsec must be lowercase bech32")
    separator = candidate.rfind("1")
    if separator <= 0 or separator + 7 > len(candidate):
        raise ValueError("nsec bech32 payload is malformed")
    hrp = candidate[:separator]
    payload = candidate[separator + 1:]
    if any(char not in BECH32_CHARSET_REV for char in payload):
        raise ValueError("nsec bech32 payload contains unsupported characters")
    data = [BECH32_CHARSET_REV[char] for char in payload]
    if _bech32_polymod(_bech32_hrp_expand(hrp) + data) != 1:
        raise ValueError("nsec bech32 checksum is invalid")
    return hrp, data[:-6]


def _convert_5bit_words_to_bytes(words: list[int]) -> bytes:
    accumulator = 0
    bit_count = 0
    out = bytearray()
    for word in words:
        if word < 0 or word > 31:
            raise ValueError("nsec bech32 word is out of range")
        accumulator = (accumulator << 5) | word
        bit_count += 5
        while bit_count >= 8:
            bit_count -= 8
            out.append((accumulator >> bit_count) & 0xFF)
    if bit_count >= 5 or ((accumulator << (8 - bit_count)) & 0xFF) != 0:
        raise ValueError("nsec bech32 payload has invalid padding")
    return bytes(out)


def secret_key_from_nsec(value: str) -> str:
    hrp, words = _bech32_decode(value)
    if hrp != "nsec":
        raise ValueError("nsec bech32 prefix must be nsec")
    secret = _convert_5bit_words_to_bytes(words)
    if len(secret) != 32:
        raise ValueError("nsec payload must decode to a 32-byte secret key")
    return secret.hex()


def collect_mnemonic_words(word_input: MnemonicWordInput, word_count: int) -> str:
    if word_count not in VALID_MNEMONIC_WORD_COUNTS:
        counts = ", ".join(str(count) for count in VALID_MNEMONIC_WORD_COUNTS)
        raise ValueError(f"mnemonic word count must be one of {counts}")
    return normalize_mnemonic_words(
        [word_input.read_mnemonic_word(index, word_count) for index in range(1, word_count + 1)]
    )


@dataclass
class MnemonicSessionSecretProvider:
    word_input: MnemonicWordInput
    word_count: int = 12
    account: int = 0
    passphrase: str = ""
    _consumed: bool = False

    def __call__(self) -> str:
        if self._consumed:
            raise RuntimeError("session mnemonic has already been consumed")
        self._consumed = True
        mnemonic = collect_mnemonic_words(self.word_input, self.word_count)
        return derive_nip06_secret(mnemonic, passphrase=self.passphrase, account=self.account)


@dataclass
class SeedQrSessionSecretProvider:
    seedqr: str | bytes
    qr_format: str = "standard"
    account: int = 0
    passphrase: str = ""
    _consumed: bool = False

    def __call__(self) -> str:
        if self._consumed:
            raise RuntimeError("session SeedQR has already been consumed")
        self._consumed = True
        if self.qr_format == "standard":
            if not isinstance(self.seedqr, str):
                raise ValueError("standard SeedQR input must be text")
            mnemonic = mnemonic_from_standard_seedqr(self.seedqr)
        elif self.qr_format == "compact":
            if not isinstance(self.seedqr, bytes):
                raise ValueError("CompactSeedQR input must be bytes")
            mnemonic = mnemonic_from_compact_seedqr(self.seedqr)
        else:
            raise ValueError("SeedQR format must be standard or compact")
        return derive_nip06_secret(mnemonic, passphrase=self.passphrase, account=self.account)


@dataclass
class NsecSessionSecretProvider:
    nsec: str
    _consumed: bool = False

    def __call__(self) -> str:
        if self._consumed:
            raise RuntimeError("session nsec has already been consumed")
        self._consumed = True
        return secret_key_from_nsec(self.nsec)
