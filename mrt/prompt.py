"""Prompt building utilities for MRTranslator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence


@dataclass(frozen=True)
class Token:
    """Represents a morphological token.

    Attributes
    ----------
    surface:
        The original surface form as it appears in the source text.
    lemma:
        The dictionary form of the token.
    reading:
        Phonetic reading (kana/romaji) for the token.
    pos:
        Part-of-speech tag for the token.
    gloss:
        Optional short gloss or translation that can be included in the
        vocabulary table. Defaults to an empty string when omitted.
    """

    surface: str
    lemma: str
    reading: str
    pos: str
    gloss: str | None = ""


TokenLike = Mapping[str, str]


def _normalize_tokens(tokens: Iterable[Token | TokenLike]) -> List[Token]:
    """Ensure a sequence of :class:`Token` instances.

    Parameters
    ----------
    tokens:
        Iterable of :class:`Token` objects or mapping-like objects containing
        the keys ``surface``, ``lemma``, ``reading``, ``pos`` and optionally
        ``gloss``.

    Returns
    -------
    list[Token]
        Normalized token instances ready for formatting.
    """

    normalized: List[Token] = []
    for token in tokens:
        if isinstance(token, Token):
            normalized.append(token)
            continue

        missing_keys = {"surface", "lemma", "reading", "pos"} - token.keys()
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise KeyError(f"Token mapping missing required keys: {missing}")

        normalized.append(
            Token(
                surface=str(token["surface"]),
                lemma=str(token["lemma"]),
                reading=str(token["reading"]),
                pos=str(token["pos"]),
                gloss=str(token.get("gloss", "")),
            )
        )
    return normalized


def format_tokens_table(tokens: Iterable[Token | TokenLike]) -> str:
    """Format tokens as a Markdown table.

    Parameters
    ----------
    tokens:
        Iterable of tokens to format. Accepts both :class:`Token` objects and
        mapping-like dictionaries with the required token keys.

    Returns
    -------
    str
        Markdown table listing the surface form, lemma, reading, part of
        speech, and optional gloss for each token. If *tokens* is empty an
        explanatory placeholder table is returned so that the model still sees
        the expected section structure.
    """

    normalized = _normalize_tokens(tokens)

    if not normalized:
        return "\n".join(
            [
                "| Surface | Lemma | Reading | Part of Speech | Gloss |",
                "| --- | --- | --- | --- | --- |",
                "| _no tokens provided_ |  |  |  |  |",
            ]
        )

    header = "| Surface | Lemma | Reading | Part of Speech | Gloss |"
    separator = "| --- | --- | --- | --- | --- |"
    rows = [
        f"| {token.surface} | {token.lemma} | {token.reading} | {token.pos} | {token.gloss or ''} |"
        for token in normalized
    ]
    return "\n".join([header, separator, *rows])


def build_translation_prompt(
    original_text: str,
    tokens: Iterable[Token | TokenLike],
    *,
    context: str | None = None,
    instructions: Sequence[str] | None = None,
) -> str:
    """Create a structured translation prompt for the LLM.

    The prompt is intentionally verbose so that downstream models reliably
    separate the different translation deliverables. It includes sections for
    the raw text, morphological tokens, and a clearly enumerated checklist of
    deliverables.

    Parameters
    ----------
    original_text:
        Source text to translate.
    tokens:
        Token information used for the "Tokens" section of the prompt.
    context:
        Optional situational or cultural context that should be considered by
        the model.
    instructions:
        Additional bullet-pointed instructions shown beneath the desired
        outputs checklist.

    Returns
    -------
    str
        A fully formatted prompt string ready to send to the OpenAI API.
    """

    sections: List[str] = [
        "## Original Text",
        original_text.strip() or "_no text provided_",
        "",
        "## Token Analysis",
        "Each row lists the surface form, lemma, reading, part of speech, and optional gloss.",
        format_tokens_table(tokens),
        "",
        "## Desired Outputs",
        "1. Literal translation that follows the source sentence structure closely.",
        "2. Natural translation that reads fluently for the intended audience.",
        "3. Grammar notes highlighting constructions, conjugations, and nuances.",
        "4. Vocabulary table summarising key words with readings, meanings, and usage notes.",
    ]

    if context:
        sections.extend(["", "### Additional Context", context.strip()])

    if instructions:
        sections.append("")
        sections.append("### Additional Instructions")
        sections.extend(f"- {line}" for line in instructions if line.strip())

    return "\n".join(sections).strip() + "\n"


__all__ = ["Token", "format_tokens_table", "build_translation_prompt"]
