"""Shared fixtures for the test suite.

Builds tests/fixture_site/ (a minimal Material for MkDocs project configured with this
plugin — 3 modes, headings, a wrapper div, and a card grid, exercising every marking
method the README documents) once per session and serves it over local HTTP, so
Playwright can drive a real browser against the actual generated HTML/CSS/JS rather than
a hand-assembled fragment.

test_behavior.py covers the plugin's own mechanics (hiding, persistence, hash recovery).
test_accessibility.py and test_keyboard.py cover axe-core violations and keyboard/focus
behavior on top of that same fixture.
"""

import functools
import http.server
import subprocess
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixture_site"


@pytest.fixture(scope="session")
def built_site(tmp_path_factory):
    site_dir = tmp_path_factory.mktemp("site")
    proc = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--site-dir", str(site_dir), "--clean"],
        cwd=FIXTURE_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, (
        f"fixture site failed to build:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "WARNING" not in proc.stdout and "WARNING" not in proc.stderr, (
        f"fixture site build produced warnings:\n{proc.stdout}\n{proc.stderr}"
    )
    return {"site_dir": site_dir}


@pytest.fixture(scope="session")
def site_url(built_site):
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(built_site["site_dir"])
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


# --- shared axe-core plumbing ---

# Vendored rather than fetched from a CDN at test time, so a run doesn't depend on
# network access to a third party. Pinned to axe-core 4.10.2 — to update, download a
# newer axe.min.js from https://github.com/dequelabs/axe-core/releases over this file.
VENDOR_AXE_JS = Path(__file__).parent / "vendor" / "axe.min.js"

# Rules that fire on Material for MkDocs' own theme templates, not this plugin's code —
# same rationale as python-field-guide's tests/conftest.py, which this mirrors.
KNOWN_UPSTREAM_RULES = {
    "aria-dialog-name",  # Material's search dialog (.md-search) has no accessible name
}

# Confirmed (by checking the flagged nodes) to come from Material's own default, unthemed
# palette (.md-tabs__link, .md-copyright) or this fixture's own throwaway prose link — not
# from anything the plugin renders. Disabled only for the full-page scan, not the
# #fcm-toggle-scoped one, so a real contrast bug inside the toggle itself still fails.
FULL_PAGE_ONLY_DISABLED_RULES = {
    "color-contrast",
    "link-in-text-block",
}

DISABLED_RULES = KNOWN_UPSTREAM_RULES


def run_axe(page, extra_disabled=(), context=None):
    page.add_script_tag(path=str(VENDOR_AXE_JS))
    disabled = sorted(set(DISABLED_RULES).union(extra_disabled))
    result = page.evaluate(
        """([disabledRules, ctx]) => axe.run(ctx || document, {
            rules: Object.fromEntries(disabledRules.map((id) => [id, { enabled: false }]))
        })""",
        [disabled, context],
    )
    return result["violations"]


def format_violations(violations):
    lines = []
    for v in violations:
        targets = [n["target"] for n in v["nodes"][:5]]
        lines.append(
            f"[{v['impact']}] {v['id']}: {v['help']} ({len(v['nodes'])} node(s)) — {targets}"
        )
    return "\n".join(lines)
