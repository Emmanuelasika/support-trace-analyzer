from html.parser import HTMLParser
from pathlib import Path


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag in {"a", "link"}:
            self.links.append(attributes.get("href", ""))


def test_pages_site_has_complete_navigation_and_assets():
    root = Path(__file__).parents[1]
    parser = PageParser()
    parser.feed((root / "docs/index.html").read_text(encoding="utf-8"))
    assert {
        "top", "what-it-does", "use-cases", "how-it-works", "example",
        "case-story", "quick-start", "architecture", "limitations",
    } <= parser.ids
    assert "site.css" in parser.links
    assert (root / "docs/site.css").stat().st_size > 5_000


def test_pages_case_study_uses_real_fixture_and_honest_product_language():
    root = Path(__file__).parents[1]
    page = (root / "docs/index.html").read_text(encoding="utf-8")
    fixture = (root / "fixtures/rate-limit.json").read_text(encoding="utf-8")
    assert "req_demo_123" in fixture and "req_demo_123" in page
    assert "7b4755b5ccd192b9" in page
    assert "does not claim" in page
    assert "4 sensitive values redacted" not in page


def test_pages_uses_public_product_name_and_future_repository_slug():
    root = Path(__file__).parents[1]
    page = (root / "docs/index.html").read_text(encoding="utf-8")
    assert "Support Trace Analyzer" in page
    assert "Emmanuelasika/support-trace-analyzer" in page
    assert "Emmanuelasika/TraceKit" not in page


def test_pages_avoids_rejected_case_file_framing():
    root = Path(__file__).parents[1]
    page = (root / "docs/index.html").read_text(encoding="utf-8")
    assert "EVIDENCE ROOM" not in page
    assert "CASE TK" not in page
    assert "INVESTIGATION LOG" not in page


def test_pages_uses_accessible_semantic_states_for_real_evidence():
    root = Path(__file__).parents[1]
    page = (root / "docs/index.html").read_text(encoding="utf-8")
    css = (root / "docs/site.css").read_text(encoding="utf-8")
    for state in ("semantic-info", "semantic-safe", "semantic-warning", "semantic-unsafe"):
        assert state in page
        assert f".{state}" in css
    for token in ("--info:#225c9f", "--safe:#237346", "--warning:#956200", "--unsafe:#b42318"):
        assert token in css
    assert 'class="code-file unsafe-file"' in page
    assert 'class="code-file safe-file"' in page


def test_pages_has_product_specific_transformation_and_code_tokens():
    root = Path(__file__).parents[1]
    page = (root / "docs/index.html").read_text(encoding="utf-8")
    assert 'class="transformation"' in page
    assert "customer-evidence.json" in page
    assert "safe-evidence.json" in page
    assert "Classification report" in page
    for token_class in ("key", "string", "number", "unsafe-token", "safe-token", "prompt", "flag"):
        assert f'class="{token_class}"' in page
