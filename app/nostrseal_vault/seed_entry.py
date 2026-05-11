from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mnemonic import Mnemonic

from .nip06 import derive_nip06_secret


VALID_MNEMONIC_WORD_COUNTS = (12, 15, 18, 21, 24)
_ENGLISH_MNEMONIC = Mnemonic("english")


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

    wordlist = set(_ENGLISH_MNEMONIC.wordlist)
    unknown = [word for word in normalized if word not in wordlist]
    if unknown:
        raise ValueError(f"mnemonic word is not in the BIP-39 English wordlist: {unknown[0]}")

    mnemonic = " ".join(normalized)
    if not _ENGLISH_MNEMONIC.check(mnemonic):
        raise ValueError("mnemonic failed BIP-39 checksum validation")
    return mnemonic


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
