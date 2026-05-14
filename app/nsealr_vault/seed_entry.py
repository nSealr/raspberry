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
