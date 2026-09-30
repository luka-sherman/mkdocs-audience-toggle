"""axe-core checks in each mode, and the toast's live region."""

import pytest

from conftest import FULL_PAGE_ONLY_DISABLED_RULES, format_violations, run_axe

MODES = ["beginner", "intermediate", "expert"]


@pytest.mark.parametrize("mode", MODES)
def test_page_has_no_axe_violations(page, site_url, mode):
    page.goto(f"{site_url}/?mode={mode}")
    violations = run_axe(page, extra_disabled=FULL_PAGE_ONLY_DISABLED_RULES)
    assert not violations, format_violations(violations)


def test_toggle_has_no_axe_violations_scoped(page, site_url):
    """Runs every rule, including the ones the full-page scan skips."""
    page.goto(site_url)
    violations = run_axe(page, context="#audience-toggle")
    assert not violations, format_violations(violations)


def test_toast_is_a_polite_live_region(page, site_url):
    page.goto(site_url)
    page.click('.audience-option[data-name="expert"]')
    page.wait_for_selector("#audience-toast")
    role, live = page.evaluate(
        """() => {
            const toast = document.getElementById('audience-toast');
            return [toast.getAttribute('role'), toast.getAttribute('aria-live')];
        }"""
    )
    assert role == "status"
    assert live == "polite"


def test_toast_announces_the_configured_text(page, site_url):
    page.goto(site_url)
    page.click('.audience-option[data-name="expert"]')
    text = page.evaluate("() => document.getElementById('audience-toast').textContent")
    assert "Now showing everything" in text
