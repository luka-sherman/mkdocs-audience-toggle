"""Keyboard use and focus visibility for the toggle."""


def test_toggle_options_are_real_labeled_buttons(page, site_url):
    page.goto(site_url)
    options = page.evaluate(
        """() => [...document.querySelectorAll('.fcm-option')].map((b) => ({
            tag: b.tagName,
            type: b.getAttribute('type'),
            display: getComputedStyle(b).display,
            accessibleName: (b.textContent || '').trim(),
            ariaPressed: b.getAttribute('aria-pressed'),
        }))"""
    )
    assert len(options) == 3
    assert all(o["tag"] == "BUTTON" and o["type"] == "button" for o in options)
    assert all(o["display"] != "none" for o in options)
    assert all(o["accessibleName"] for o in options)
    assert sum(o["ariaPressed"] == "true" for o in options) == 1, (
        "exactly one option should be aria-pressed at a time"
    )


def test_toggle_is_reachable_by_tab(page, site_url):
    page.goto(site_url)
    for _ in range(40):
        page.keyboard.press("Tab")
        if page.evaluate("() => document.activeElement?.classList.contains('fcm-option')"):
            return
    raise AssertionError("Tab never reached a .fcm-option within 40 stops")


def test_space_and_enter_activate_the_focused_option(page, site_url):
    page.goto(site_url)
    expert = page.locator('.fcm-option[data-name="expert"]')
    expert.focus()
    page.keyboard.press("Enter")
    mode = page.evaluate("() => document.documentElement.getAttribute('data-fcm-mode')")
    assert mode == "expert"

    beginner = page.locator('.fcm-option[data-name="beginner"]')
    beginner.focus()
    page.keyboard.press("Space")
    mode = page.evaluate("() => document.documentElement.getAttribute('data-fcm-mode')")
    assert mode == "beginner"


def test_focused_option_has_a_visible_focus_indicator(page, site_url):
    page.goto(site_url)
    result = page.evaluate(
        """() => {
            const el = document.querySelector('.fcm-option');
            el.focus({ focusVisible: true });
            const cs = getComputedStyle(el);
            const outline = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
            const shadow = cs.boxShadow && cs.boxShadow !== 'none';
            return outline || shadow;
        }"""
    )
    assert result, ".fcm-option shows no outline or box-shadow when focused"


def test_no_positive_tabindex_inside_the_toggle(page, site_url):
    page.goto(site_url)
    positive = page.evaluate(
        """() => [...document.querySelectorAll('#fcm-toggle [tabindex]')]
            .map((el) => parseInt(el.getAttribute('tabindex'), 10))
            .filter((v) => v > 0)"""
    )
    assert not positive
