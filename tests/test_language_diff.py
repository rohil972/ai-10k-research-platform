from src.analysis import _basic_language_diff

def test_language_diff_returns_added_and_removed():
    result = _basic_language_diff("risk alpha beta gamma", "risk delta beta gamma")
    assert "top_added_phrases" in result
    assert "top_removed_phrases" in result
    assert result["methodology"]
