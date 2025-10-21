import pytest

from mrtranslator.processing import (
    ProcessedText,
    SentenceTokens,
    TextProcessor,
    TokenData,
    normalize_punctuation,
)


def test_normalize_punctuation_converts_zenkaku_and_prolonged_sound_mark():
    text = "テスト―です！ こんにちは？"
    normalized = normalize_punctuation(text)
    assert normalized == "テストーです! こんにちは?"


@pytest.mark.integration
def test_text_processor_provides_tokens_and_sentences():
    text = "テスト―です！\n次の行？"
    processor = TextProcessor()
    processed = processor.process(text)

    assert isinstance(processed, ProcessedText)
    assert processed.original_text == text
    assert processed.normalized_text == "テストーです!\n次の行?"

    # Ensure we gathered token metadata.
    assert processed.tokens, "Token list should not be empty"
    for token in processed.tokens:
        assert isinstance(token, TokenData)
        assert token.lemma
        assert token.reading
        assert len(token.pos) == 6

    # Sentence grouping should respect newline and punctuation boundaries.
    assert len(processed.sentences) == 2
    first_sentence = processed.sentences[0]
    second_sentence = processed.sentences[1]

    assert isinstance(first_sentence, SentenceTokens)
    assert first_sentence.tokens[-1].surface == "!"
    assert second_sentence.tokens[-1].surface == "?"


def test_sentence_grouping_keeps_closing_quotes_with_sentence():
    processor = TextProcessor()
    text = "「これはテストです。」\n「はい。」"
    processed = processor.process(text)

    assert len(processed.sentences) == 2
    first_sentence_text = "".join(token.surface for token in processed.sentences[0].tokens)
    second_sentence_text = "".join(token.surface for token in processed.sentences[1].tokens)

    assert first_sentence_text.endswith("。」")
    assert second_sentence_text.endswith("。」")
