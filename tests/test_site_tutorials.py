"""The website presents notebooks as faithful views, never as another evidence source."""
import base64
import hashlib
import html
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_site


def _notebook(spec):
    path = ROOT / "tutorials" / spec["source"]
    return path, json.loads(path.read_text(encoding="utf-8"))


def _text(value):
    return value if isinstance(value, str) else "".join(value or [])


def test_each_notebook_has_a_current_readable_page():
    for spec in build_site.TUTORIALS:
        source, notebook = _notebook(spec)
        page_path = ROOT / "docs" / "tutorials" / f"{spec['slug']}.md"
        assert page_path.exists(), f"no website page for {source.name}"
        page = page_path.read_text(encoding="utf-8")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert f"sha256={digest}" in page, f"{page_path.name} was rendered from another revision"
        assert "Readable notebook view" in page
        assert "Open the original notebook" in page
        n_code = sum(c.get("cell_type") == "code" for c in notebook["cells"])
        assert page.count('<details class="tutorial-code"') == n_code


def test_committed_stream_outputs_are_visible_on_the_site():
    """A page containing the prose but dropping numerical output would defeat the request."""
    for spec in build_site.TUTORIALS:
        _, notebook = _notebook(spec)
        page = (ROOT / "docs" / "tutorials" / f"{spec['slug']}.md").read_text(encoding="utf-8")
        streams = [
            _text(output.get("text")).rstrip()
            for cell in notebook["cells"]
            for output in cell.get("outputs", [])
            if output.get("output_type") == "stream"
        ]
        assert streams, f"{spec['source']} has no stream output; this check would be vacuous"
        for stream in streams:
            assert html.escape(stream) in page, (
                f"website page for {spec['source']} dropped or changed a committed output")


def test_every_committed_notebook_figure_is_extracted_byte_for_byte():
    expected = {}
    for spec in build_site.TUTORIALS:
        _, notebook = _notebook(spec)
        for cell_index, cell in enumerate(notebook["cells"]):
            for output_index, output in enumerate(cell.get("outputs", [])):
                data = output.get("data") or {}
                if "image/png" not in data:
                    continue
                name = (f"{spec['slug']}-cell-{cell_index:02d}-"
                        f"output-{output_index:02d}.png")
                expected[name] = base64.b64decode(_text(data["image/png"]))
    assert expected, "the notebooks contain no figures; this check would be vacuous"
    asset_dir = ROOT / "docs" / "assets" / "tutorials"
    actual = {p.name for p in asset_dir.glob("*.png")}
    assert actual == set(expected), "the website has missing or orphaned tutorial figures"
    for name, binary in expected.items():
        assert (asset_dir / name).read_bytes() == binary, f"{name} differs from notebook output"


def test_tutorial_landing_page_routes_to_readable_pages_and_shows_previews():
    page = (ROOT / "docs" / "tutorials" / "index.md").read_text(encoding="utf-8")
    for spec in build_site.TUTORIALS:
        assert f"/tutorials/{spec['slug']}.html" in page
        assert spec["question"] in page
    assert page.count('class="tutorial-card"') == len(build_site.TUTORIALS)
    assert page.count('class="tutorial-card-image"') == len(build_site.TUTORIALS)


def test_plain_language_status_cards_match_the_ledger():
    claims = build_site.load_yaml_list(ROOT / "ledgers" / "status.yaml")
    counts = {status: sum(c["status"] == status for c in claims)
              for status in build_site.STATUSES}
    for name in ("index.md", "where-we-are.md"):
        page = (ROOT / "docs" / name).read_text(encoding="utf-8")
        found = dict(re.findall(r'data-status-count="(\w+)">(\d+)<', page))
        assert set(found) == build_site.STATUSES, f"{name} omits a claim status"
        assert {status: int(value) for status, value in found.items()} == counts, (
            f"{name}'s plain-language snapshot is stale: {found} vs {counts}")


def test_site_support_files_are_present():
    config = (ROOT / "docs" / "_config.yml").read_text(encoding="utf-8")
    css = (ROOT / "docs" / "assets" / "css" / "style.scss").read_text(encoding="utf-8")
    head = (ROOT / "docs" / "_includes" / "head-custom.html").read_text(encoding="utf-8")
    assert "jekyll-theme-primer" in config
    for selector in (".status-grid", ".tutorial-grid", ".tutorial-output", ".tutorial-code"):
        assert selector in css
    assert "mathjax@3.2.2" in head.lower(), "tutorial equations have no browser renderer"
