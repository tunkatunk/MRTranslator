from mrt.prompt import build_translation_prompt, format_tokens_table, Token


def test_format_tokens_table_empty():
    table = format_tokens_table([])
    assert "_no tokens provided_" in table
    assert table.count("\n") == 2


def test_build_translation_prompt_structure():
    tokens = [
        Token(surface="猫", lemma="猫", reading="ねこ", pos="noun"),
        {"surface": "です", "lemma": "です", "reading": "です", "pos": "copula"},
    ]
    prompt = build_translation_prompt("猫です", tokens, context="Casual intro")
    assert "## Original Text" in prompt
    assert "## Token Analysis" in prompt
    assert "## Desired Outputs" in prompt
    assert "### Additional Context" in prompt
    assert "猫です" in prompt
    assert "copula" in prompt
