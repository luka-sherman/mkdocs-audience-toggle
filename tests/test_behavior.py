"""Hiding, persistence, links to hidden content, layout, the URL parameter, and events."""


def current_mode(page):
    return page.evaluate("() => document.documentElement.getAttribute('data-audience-mode')")


def test_default_mode_is_the_one_marked_default(page, site_url):
    page.goto(site_url)
    assert current_mode(page) == "intermediate"


def test_attr_list_marker_hides_heading_and_its_section(page, site_url):
    """The marked heading, the paragraph under it, and its TOC entry are all hidden."""
    page.goto(f"{site_url}/?mode=beginner")

    result = page.evaluate(
        """() => {
            const heading = document.getElementById('advanced-topic');
            const para = heading.nextElementSibling;
            const tocLink = document.querySelector('a.md-nav__link[href$="#advanced-topic"]');
            const tocItem = tocLink ? tocLink.closest('.md-nav__item') : null;
            return {
                headingDisplay: getComputedStyle(heading).display,
                paraDisplay: getComputedStyle(para).display,
                tocItemDisplay: tocItem ? getComputedStyle(tocItem).display : null,
            };
        }"""
    )
    assert result["headingDisplay"] == "none"
    assert result["paraDisplay"] == "none"
    assert result["tocItemDisplay"] == "none"


def test_wrapper_class_hides_with_its_first_child_heading(page, site_url):
    page.goto(f"{site_url}/?mode=beginner")
    display = page.evaluate(
        """() => getComputedStyle(document.querySelector('.wrap-me')).display"""
    )
    assert display == "none"


def test_inline_span_marker_hides_in_every_listed_mode(page, site_url):
    find_span = """() => {
        const span = [...document.querySelectorAll('span')]
            .find((s) => s.textContent.includes('phrase hidden'));
        return span ? getComputedStyle(span).display : null;
    }"""

    for mode in ("beginner", "intermediate"):
        page.goto(f"{site_url}/?mode={mode}")
        assert page.evaluate(find_span) == "none", f"span should be hidden in {mode} mode"

    page.goto(f"{site_url}/?mode=expert")
    assert page.evaluate(find_span) != "none", "span should be visible in expert mode"


def test_card_grid_has_rule_hides_the_whole_card(page, site_url):
    """The fixture's extra.css has the :has() rule from the README. The whole card
    should be hidden, not only the marked paragraph."""
    page.goto(f"{site_url}/?mode=beginner")
    result = page.evaluate(
        """() => {
            const selector = '.grid.cards > ul > li > p[data-audience-hide~="beginner"]';
            const marked = document.querySelector(selector);
            const card = marked ? marked.closest('li') : null;
            const otherCard = [...document.querySelectorAll('.grid.cards > ul > li')]
                .find((li) => li.textContent.includes('Card B'));
            return {
                markedCardDisplay: card ? getComputedStyle(card).display : null,
                otherCardDisplay: otherCard ? getComputedStyle(otherCard).display : null,
            };
        }"""
    )
    assert result["markedCardDisplay"] == "none"
    assert result["otherCardDisplay"] != "none"


def test_mode_persists_across_navigation(page, site_url):
    page.goto(f"{site_url}/?mode=expert")
    page.goto(f"{site_url}/other/")
    assert current_mode(page) == "expert"
    display = page.evaluate(
        """() => getComputedStyle(document.getElementById('expert-only-section')).display"""
    )
    assert display != "none"


def test_link_to_hidden_heading_switches_to_the_closer_of_two_modes(page, site_url):
    """'Advanced topic' is hidden only in Beginner. From Beginner, Intermediate is
    one step away and Expert is two, so the link should switch to Intermediate."""
    page.goto(f"{site_url}/?mode=beginner")

    # Use the link in the page body. The matching TOC link is hidden in this mode.
    link = page.locator('.md-content a[href="#advanced-topic"]')
    assert link.count() > 0

    before = page.evaluate(
        "() => getComputedStyle(document.getElementById('advanced-topic')).display"
    )
    assert before == "none"

    link.first.click()
    page.wait_for_function(
        "() => getComputedStyle(document.getElementById('advanced-topic')).display !== 'none'"
    )
    assert current_mode(page) == "intermediate"


def test_link_skips_a_mode_that_also_hides_the_target(page, site_url):
    """'Expert-only section' is hidden in Beginner and Intermediate (the default), so
    from Beginner the link should switch to Expert."""
    page.goto(f"{site_url}/other/?mode=beginner#expert-only-section")
    page.wait_for_function(
        "() => getComputedStyle(document.getElementById('expert-only-section')).display !== 'none'"
    )
    assert current_mode(page) == "expert"


def test_link_to_subheading_inside_a_hidden_section(page, site_url):
    """'Expert subsection' isn't marked. It's hidden because the section above it is
    hidden in Beginner and Intermediate, so the link should switch to Expert."""
    page.goto(f"{site_url}/other/?mode=beginner#expert-subsection")
    page.wait_for_function(
        "() => getComputedStyle(document.getElementById('expert-subsection')).display !== 'none'"
    )
    assert current_mode(page) == "expert"


def test_link_to_heading_inside_a_hidden_div(page, site_url):
    """The heading is inside a <div data-audience-hide="intermediate">. From Intermediate,
    Beginner and Expert are equally close, and the later one (Expert) wins."""
    page.goto(f"{site_url}/other/?mode=intermediate#heading-inside-a-hidden-div")
    page.wait_for_function(
        """() => {
            const heading = document.getElementById('heading-inside-a-hidden-div');
            return heading.getClientRects().length > 0;
        }"""
    )
    assert current_mode(page) == "expert"


def test_link_to_visible_heading_does_not_switch_modes(page, site_url):
    page.goto(f"{site_url}/?mode=expert#advanced-topic")
    page.wait_for_timeout(100)
    assert current_mode(page) == "expert"


def test_highlight_pill_aligns_with_the_active_option_regardless_of_label_length(page, site_url):
    """Options size to their labels, so "Intermediate" is wider than a third of the
    toggle. The highlight should match the option's actual size."""
    page.goto(site_url)
    # The script repositions the highlight after web fonts load, so wait for it.
    page.wait_for_function(
        """() => {
            const opt = document.querySelector('.audience-option[data-name="intermediate"]');
            const o = opt.getBoundingClientRect();
            const h = document.querySelector('.audience-highlight').getBoundingClientRect();
            return Math.abs(o.left - h.left) < 1 && Math.abs(o.width - h.width) < 1;
        }"""
    )


def test_reduced_motion_disables_the_highlight_transition(page, site_url):
    page.emulate_media(reduced_motion="reduce")
    page.goto(site_url)
    transition = page.evaluate(
        "() => getComputedStyle(document.querySelector('.audience-highlight')).transitionDuration"
    )
    assert transition in ("0s", ""), f"expected no transition, got {transition!r}"


def test_toggle_drops_to_its_own_row_on_a_narrow_viewport(page, site_url):
    """At 375px the three labels don't fit in the header row. The toggle should wrap
    to its own row, stay on screen, and keep its natural width."""
    page.set_viewport_size({"width": 375, "height": 400})
    page.goto(site_url)
    result = page.evaluate(
        """() => {
            const hamburger = document.querySelector('.md-header__button.md-icon');
            const toggle = document.getElementById('audience-toggle');
            const header = document.querySelector('.md-header__inner');
            const h = hamburger.getBoundingClientRect();
            const t = toggle.getBoundingClientRect();
            return {
                onOwnRow: t.top > h.bottom - 1,
                fullyOnScreen: t.left >= 0 && t.right <= window.innerWidth,
                notStretched: t.width < header.getBoundingClientRect().width - 4,
            };
        }"""
    )
    assert result["onOwnRow"], "toggle should be below the hamburger and title"
    assert result["fullyOnScreen"], "toggle should not overflow the viewport"
    assert result["notStretched"], "toggle should not stretch to the full width"


def test_toggle_keeps_its_place_on_a_narrow_viewport_when_it_fits(page, site_url):
    """At 700px (below the 45em breakpoint) the toggle fits beside the title, so it
    should stay before the header's other buttons instead of moving to its own row."""
    page.set_viewport_size({"width": 700, "height": 400})
    page.goto(site_url)
    result = page.evaluate(
        """() => {
            const toggle = document.getElementById('audience-toggle');
            const option = document.querySelector('.md-header__option');
            const toggleRight = toggle.getBoundingClientRect().right;
            const optionLeft = option.getBoundingClientRect().left;
            return {
                ownRow: toggle.classList.contains('audience-toggle--own-row'),
                beforeOption: toggleRight <= optionLeft,
            };
        }"""
    )
    assert not result["ownRow"]
    assert result["beforeOption"], "toggle should sit before the palette button"


def test_toggle_stays_on_the_header_row_on_a_wide_viewport(page, site_url):
    """Compared against the title, because Material hides the hamburger at this width."""
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(site_url)
    result = page.evaluate(
        """() => {
            const title = document.querySelector('.md-header__title');
            const toggle = document.getElementById('audience-toggle');
            const inner = document.querySelector('.md-header__inner');
            const g = title.getBoundingClientRect();
            const t = toggle.getBoundingClientRect();
            return {
                sameRow: Math.abs((t.top + t.bottom) / 2 - (g.top + g.bottom) / 2) < g.height,
                singleRowHeight: inner.getBoundingClientRect().height < 60,
            };
        }"""
    )
    assert result["sameRow"], "toggle should be on the same row as the title"
    assert result["singleRowHeight"], "header should be one row tall"


def test_query_param_does_not_change_the_url(page, site_url):
    """Removing the parameter would break Material's instant-navigation links, which
    already include it. See "Setting the mode from a URL" in the README."""
    page.goto(f"{site_url}/?mode=expert&keep=me#advanced-topic")
    page.wait_for_function(
        "() => document.documentElement.getAttribute('data-audience-mode') === 'expert'"
    )

    result = page.evaluate("""() => ({ search: location.search, hash: location.hash })""")
    assert "mode=expert" in result["search"]
    assert "keep=me" in result["search"]
    assert result["hash"] == "#advanced-topic"


def test_query_param_with_unrecognized_value_is_ignored(page, site_url):
    page.goto(f"{site_url}/?mode=not-a-real-mode")
    assert current_mode(page) == "intermediate"


RECORD_EVENTS = """() => {
    window.__events = [];
    document.addEventListener('audience:modechange', (e) => window.__events.push(e.detail));
}"""


def test_modechange_event_fires_with_the_new_and_previous_mode(page, site_url):
    page.goto(site_url)
    page.evaluate(RECORD_EVENTS)
    page.click('.audience-option[data-name="expert"]')
    events = page.evaluate("() => window.__events")
    assert events == [{"mode": "expert", "previousMode": "intermediate"}]


def test_modechange_event_does_not_fire_when_clicking_the_active_option(page, site_url):
    page.goto(site_url)
    page.evaluate(RECORD_EVENTS)
    page.click('.audience-option[data-name="intermediate"]')
    events = page.evaluate("() => window.__events")
    assert events == []
