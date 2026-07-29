from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parents[1]
HTML = ROOT / "docs" / "index.html"
CSS = ROOT / "docs" / "site.css"
JS = ROOT / "docs" / "site.js"
ASSETS = ROOT / "docs" / "assets"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.images: list[dict[str, str | None]] = []
        self.scripts: list[str | None] = []
        self.meta: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if element_id := values.get("id"):
            self.ids.add(element_id)
        if tag == "img":
            self.images.append(values)
        if tag == "script":
            self.scripts.append(values.get("src"))
        if tag == "meta":
            self.meta.append(values)


def test_flagship_site_has_complete_narrative_and_interactive_demo() -> None:
    parser = SiteParser()
    parser.feed(HTML.read_text(encoding="utf-8"))

    assert {"main", "top", "refinery", "case-study", "install"} <= parser.ids
    assert "site.js" in parser.scripts
    assert all(image.get("alt") for image in parser.images)
    assert {image["src"] for image in parser.images} == {
        "assets/trace-transformation.webp",
        "assets/incident-bundle.webp",
    }


def test_social_image_and_generated_asset_family_are_present() -> None:
    parser = SiteParser()
    parser.feed(HTML.read_text(encoding="utf-8"))
    social = next(meta["content"] for meta in parser.meta if meta.get("property") == "og:image")

    assert social.endswith("/assets/trace-transformation.webp")
    assert {path.name for path in ASSETS.glob("*.webp")} == {
        "trace-transformation.webp",
        "evidence-field.webp",
        "incident-bundle.webp",
    }
    assert all(path.stat().st_size > 40_000 for path in ASSETS.glob("*.webp"))


def test_styles_and_script_encode_distinct_trace_experience() -> None:
    css = CSS.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")

    assert len(css) > 10_000
    assert "prefers-reduced-motion" in css
    assert "evidence-field.webp" in css
    assert all(f"{stage}:" in javascript for stage in ("raw", "safe", "diagnosis"))
    assert "[REDACTED]" in javascript
    assert "rate_limit" in javascript
