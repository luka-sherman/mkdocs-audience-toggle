"""axe-core over the fixture site, in each of the toggle's three modes, plus the toast."""

import pytest

from conftest import FULL_PAGE_ONLY_DISABLED_RULES, format_violations, run_axe

MODES = ["beginner", "intermediate", "expert"]


@pytest.mark.parametrize("mode", MODES)
def test_page_has_no_axe_violations(page, site_url, mode):
    page.goto(f"{site_url}/?mode={mode}")
    violations = run_axe(page, extra_disabled=FULL_PAGE_ONLY_DISABLED_RULES)
    assert not violations, format_violations(violations)


def test_toggle_has_no_axe_violations_scoped(page, site_url):
    """Scoped separately from the full-page scan above so a violation inside the toggle
    itself is unambiguous in the failure message, rather than mixed in with the rest of
    the fixture page's markup."""
    page.goto(site_url)
    violations = run_axe(page, context="#fcm-toggle")
    assert not violations, format_violations(violations)


def test_toast_is_a_polite_live_region(page, site_url):
    page.goto(site_url)
    page.click('.fcm-option[data-name="expert"]')
    page.wait_for_selector("#fcm-toast")
    role, live = page.evaluate(
        """() => {
            const toast = document.getElementById('fcm-toast');
            return [toast.getAttribute('role'), toast.getAttribute('aria-live')];
        }"""
    )
    assert role == "status"
    assert live == "polite"


def test_toast_announces_the_configured_text(page, site_url):
    page.goto(site_url)
    page.click('.fcm-option[data-name="expert"]')
    text = page.evaluate("() => document.getElementById('fcm-toast').textContent")
    assert "Now showing everything" in text
