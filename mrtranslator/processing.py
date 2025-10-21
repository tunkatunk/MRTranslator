"""Core text processing pipeline for MRTranslator.

This module provides utilities to normalise Japanese text, run SudachiPy tokenisation,
and organise the resulting tokens into sentences. The goal is to retain the original
text, the normalised representation, and rich token metadata for later prompt
construction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

try:
    from sudachipy import dictionary, tokenizer
except ImportError as exc:  # pragma: no cover - executed only when dependency missing.
    raise ImportError(
        "SudachiPy is required to use mrtranslator.processing. "
        "Install sudachipy and a Sudachi dictionary (e.g. sudachidict_core)."
    ) from exc

# Mapping of zenkaku punctuation to their hankaku equivalents.
_ZENKAKU_PUNCT_TRANSLATION = {
    ord("！"): "!",
    ord("？"): "?",
    ord("＂"): '"',
    ord("＇"): "'",
    ord("＃"): "#",
    ord("＄"): "$",
    ord("％"): "%",
    ord("＆"): "&",
    ord("（"): "(",
    ord("）"): ")",
    ord("＊"): "*",
    ord("＋"): "+",
    ord("，"): ",",
    ord("－"): "-",
    ord("．"): ".",
    ord("／"): "/",
    ord("："): ":",
    ord("；"): ";",
    ord("＜"): "<",
    ord("＝"): "=",
    ord("＞"): ">",
    ord("＠"): "@",
    ord("［"): "[",
    ord("＼"): "\\",
    ord("］"): "]",
    ord("＾"): "^",
    ord("＿"): "_",
    ord("｀"): "`",
    ord("｛"): "{",
    ord("｜"): "|",
    ord("｝"): "}",
    ord("～"): "~",
}

# Map various hyphen/dash characters that are often used as prolonged sound marks to the
# canonical choonpu (ー).
_PROLONGED_SOUND_MAP = {
    ord("―"): "ー",
    ord("—"): "ー",
    ord("−"): "ー",
    ord("ｰ"): "ー",
    ord("─"): "ー",
    ord("━"): "ー",
    ord("‐"): "ー",
    ord("－"): "ー",
}

_SENTENCE_TERMINATORS = {"。", ".", "!", "！", "?", "？"}
_CLOSING_PUNCTUATION = {
    "」",
    "』",
    "】",
    "〕",
    "）",
    ")",
    "]",
    "〉",
    "》",
    "〗",
}
_LINE_BREAK_SURFACES = {"\n", "\r", "\r\n"}


def normalize_punctuation(text: str) -> str:
    """Normalise punctuation in *text*.

    The transformation converts zenkaku punctuation to their hankaku counterparts
    and consolidates various dash-like characters into the standard prolonged sound
    mark (ー).
    """

    converted = text.translate(_ZENKAKU_PUNCT_TRANSLATION)
    return converted.translate(_PROLONGED_SOUND_MAP)


@dataclass(frozen=True)
class TokenData:
    """Represents a single Sudachi token with useful metadata."""

    surface: str
    lemma: str
    reading: str
    pos: Tuple[str, str, str, str, str, str]


@dataclass(frozen=True)
class SentenceTokens:
    """A collection of tokens that form a sentence."""

    tokens: Tuple[TokenData, ...]

    def surfaces(self) -> List[str]:
        """Return the token surfaces for convenience."""

        return [token.surface for token in self.tokens]


@dataclass(frozen=True)
class ProcessedText:
    """Container for the processed representation of an input string."""

    original_text: str
    normalized_text: str
    tokens: Tuple[TokenData, ...]
    sentences: Tuple[SentenceTokens, ...]


class TextProcessor:
    """Pipeline that prepares text for prompt construction."""

    def __init__(self, split_mode: tokenizer.Tokenizer.SplitMode | None = None) -> None:
        self._tokenizer = dictionary.Dictionary().create()
        self._split_mode = split_mode or tokenizer.Tokenizer.SplitMode.B

    def __call__(self, text: str) -> ProcessedText:
        return self.process(text)

    def process(self, text: str) -> ProcessedText:
        """Process *text* and return the structured representation."""

        normalized = normalize_punctuation(text)
        morphemes = self._tokenizer.tokenize(normalized, self._split_mode)
        tokens = tuple(
            TokenData(
                surface=m.surface(),
                lemma=m.dictionary_form(),
                reading=m.reading_form(),
                pos=m.part_of_speech(),
            )
            for m in morphemes
        )

        sentences = tuple(group_tokens_into_sentences(tokens))
        return ProcessedText(
            original_text=text,
            normalized_text=normalized,
            tokens=tokens,
            sentences=sentences,
        )


def group_tokens_into_sentences(tokens: Sequence[TokenData]) -> Iterable[SentenceTokens]:
    """Yield :class:`SentenceTokens` by grouping *tokens* using heuristics.

    Sentence boundaries are detected using a small set of punctuation marks commonly
    used in Japanese and English. Consecutive closing punctuation immediately after a
    terminator (e.g. 「。」」) is retained within the same sentence.
    """

    sentences: List[SentenceTokens] = []
    i = 0
    n = len(tokens)
    while i < n:
        current: List[TokenData] = []
        while i < n:
            token = tokens[i]
            surface = token.surface

            if surface in _LINE_BREAK_SURFACES:
                if current:
                    sentences.append(SentenceTokens(tuple(current)))
                    current = []
                i += 1
                # Skip consecutive line breaks without yielding empty sentences.
                while i < n and tokens[i].surface in _LINE_BREAK_SURFACES:
                    i += 1
                break

            current.append(token)
            i += 1

            if surface in _SENTENCE_TERMINATORS:
                while i < n and tokens[i].surface in _CLOSING_PUNCTUATION:
                    current.append(tokens[i])
                    i += 1
                break
        if current:
            sentences.append(SentenceTokens(tuple(current)))
    return sentences
