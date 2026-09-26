from explanations import HELP

REQUIRED = ["cash", "holding", "action", "quantity", "note",
            "followed_plan", "emotion", "execute", "stop"]


def test_all_required_keys_exist():
    assert set(REQUIRED) <= set(HELP)


def test_every_text_is_non_empty_string():
    for k, v in HELP.items():
        assert isinstance(v, str) and v.strip(), k


def test_texts_are_short_enough_for_a_tooltip():
    for k, v in HELP.items():
        assert len(v) <= 260, k


def test_stop_text_mentions_atr_and_gap_risk():
    assert "ATR" in HELP["stop"] and "קפיצת מחיר" in HELP["stop"]
