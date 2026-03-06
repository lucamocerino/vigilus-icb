"""Tests for engine/trending.py — keyword spike detection."""
from sentinella.engine.trending import extract_keywords, update_trending, _current_window


class TestExtractKeywords:
    def test_basic_extraction(self):
        kws = extract_keywords("Attacco terroristico a Roma, emergenza sicurezza")
        assert "attacco" in kws
        assert "roma" in kws
        assert "emergenza" in kws
        assert "sicurezza" in kws

    def test_stops_removed(self):
        kws = extract_keywords("il gatto è sul tavolo con la sedia")
        assert "il" not in kws
        assert "con" not in kws
        assert "gatto" in kws
        assert "tavolo" in kws

    def test_short_words_excluded(self):
        kws = extract_keywords("a è no si ok")
        assert len(kws) == 0

    def test_empty_string(self):
        assert extract_keywords("") == []

    def test_english_stops(self):
        kws = extract_keywords("the attack was not new but has been")
        assert "the" not in kws
        assert "attack" in kws


class TestUpdateTrending:
    def test_empty_headlines(self):
        result = update_trending([])
        assert isinstance(result, list)

    def test_with_headlines(self):
        headlines = [
            {"title": "Attacco cyber a Roma"},
            {"title": "Attacco hacker alla pubblica amministrazione"},
            {"title": "Roma sotto attacco ransomware"},
            {"title": "Emergenza cyber in Italia"},
            {"title": "Nuovo attacco informatico a Milano"},
        ]
        result = update_trending(headlines)
        assert isinstance(result, list)
        # "attacco" should appear multiple times
        keywords = [r["keyword"] for r in result]
        assert "attacco" in keywords

    def test_security_keywords_boosted(self):
        headlines = [{"title": f"terrorismo allerta {i}"} for i in range(10)]
        result = update_trending(headlines)
        terror = next((r for r in result if r["keyword"] == "terrorismo"), None)
        if terror:
            assert terror["is_security"] is True

    def test_result_structure(self):
        headlines = [{"title": "test keyword ripetuto keyword keyword"}]
        result = update_trending(headlines)
        for item in result:
            assert "keyword" in item
            assert "count" in item
            assert "z_score" in item
            assert "direction" in item
            assert "dimension" in item
