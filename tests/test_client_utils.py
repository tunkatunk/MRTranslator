from mrt.client import parse_model_output


def test_parse_model_output_extracts_sections_and_json():
    text = """## Literal Translation\nHello\n## Notes\n- Point\n```json\n{\n  \"literal\": \"Hello\"\n}\n```"""
    result = parse_model_output(text)
    assert result["sections"]["Literal Translation"] == "Hello"
    assert result["sections"]["Notes"].startswith("- Point")
    assert result["json"]["literal"] == "Hello"
