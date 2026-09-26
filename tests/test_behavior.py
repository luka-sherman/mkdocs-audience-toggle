"""Core plugin mechanics: default mode, content hiding via each of the three marking
methods the README documents, persistence, and hash-link recovery.
"""


def test_default_mode_is_the_one_marked_default(page, site_url):
    page.goto(site_url)
    mode = page.evaluate("() => document.documentElement.getAttribute('data-fcm-mode')")
    assert mode == "intermediate"


def test_attr_list_marker_hides_heading_and_its_section(page, site_url):
    """The '## Advanced topic { data-fcm-hide="beginner" }' heading and its own paragraph
    should both hide, and its TOC entry with them, while Beginner is active."""
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
    for mode in ("beginner", "intermediate"):
        page.goto(f"{site_url}/?mode={mode}")
        display = page.evaluate(
            """() => {
                const span = [...document.querySelectorAll('span')]
                    .find((s) => s.textContent.includes('phrase hidden'));
                return span ? getComputedStyle(span).display : null;
            }"""
        )
        assert display == "none", f"span should be hidden in {mode} mode"

    page.goto(f"{site_url}/?mode=expert")
    display = page.evaluate(
        """() => {
            const span = [...document.querySelectorAll('span')]
                .find((s) => s.textContent.includes('phrase hidden'));
            return span ? getComputedStyle(span).display : null;
        }"""
    )
    assert display != "none", "span should be visible in expert mode"


def test_card_grid_has_rule_hides_the_whole_card(page, site_url):
    """Regression for the README's documented workaround: attr_list can only attach
    data-fcm-hide to a card's first paragraph, not the surrounding <li> — the fixture's
    own extra.css adds the :has() rule the README recommends, and this confirms it
    actually hides the whole card end to end, not just the marked paragraph."""
    page.goto(f"{site_url}/?mode=beginner")
    result = page.evaluate(
        """() => {
            const marked = document.querySelector('.grid.cards > ul > li > p[data-fcm-hide~="beginner"]');
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
    mode = page.evaluate("() => document.documentElement.getAttribute('data-fcm-mode')")
    assert mode == "expert"
    display = page.evaluate(
        """() => getComputedStyle(document.getElementById('expert-only-section')).display"""
    )
    assert display != "none", "expert-only section should be visible once mode carries over"


def test_link_to_hidden_section_recovers_to_the_nearest_mode_that_reveals_it(page, site_url):
    """'Advanced topic' is hidden only in beginner, so it's visible in both
    intermediate (index 1) and expert (index 2) — intermediate is the nearer of
    the two, so that's where a beginner-mode reader following this link should
    land, not expert. It happens to also be this fixture's default mode, but
    that's coincidence, not the reason — see the dedicated nearest-mode tests
    below for a case where the default and the nearest mode differ."""
    page.goto(f"{site_url}/?mode=beginner")

    # Scoped to the prose link, not the (currently-hidden, since its own heading is
    # hidden) matching TOC entry that toc.integrate also renders for this same anchor.
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

    mode = page.evaluate("() => document.documentElement.getAttribute('data-fcm-mode')")
    assert mode == "intermediate", "should recover to the nearer of the two modes that reveal it"


def test_highlight_pill_aligns_with_the_active_option_regardless_of_label_length(page, site_url):
    """Regression: the highlight used to assume every option was an equal 100%/count
    share of the track. Flex items don't shrink below their own label's content width
    by default, so "Intermediate" (this fixture's longest label) ends up wider than a
    plain third — the highlight must track the option's actual measured box, not a
    fixed fraction."""
    page.goto(site_url)
    # The plugin corrects the highlight's position again once document.fonts.ready
    # resolves (a webfont can still be swapping in when it first measures on
    # DOMContentLoaded) — that correction is async, so poll for it rather than
    # asserting the instant goto() returns.
    page.wait_for_function(
        """() => {
            const o = document.querySelector('.fcm-option[data-name="intermediate"]').getBoundingClientRect();
            const h = document.querySelector('.fcm-highlight').getBoundingClientRect();
            return Math.abs(o.left - h.left) < 1 && Math.abs(o.width - h.width) < 1;
        }"""
    )


def test_reduced_motion_disables_the_highlight_transition(page, site_url):
    page.emulate_media(reduced_motion="reduce")
    page.goto(site_url)
    transition = page.evaluate(
        "() => getComputedStyle(document.querySelector('.fcm-highlight')).transitionDuration"
    )
    assert transition in ("0s", ""), f"expected no transition under reduced motion, got {transition!r}"


def test_toggle_drops_to_its_own_row_on_a_narrow_viewport(page, site_url):
    """Below 45em, three full-length labels (Beginner/Intermediate/Expert) don't fit
    alongside the hamburger/title/search/palette on one header row. The plugin's CSS
    should drop the toggle to a second row rather than letting it overflow off-screen
    — not stretched to the header's full width (which would space the three short
    labels awkwardly wide apart), just wrapped and centered."""
    page.set_viewport_size({"width": 375, "height": 400})
    page.goto(site_url)
    result = page.evaluate(
        """() => {
            const hamburger = document.querySelector('.md-header__button.md-icon');
            const toggle = document.getElementById('fcm-toggle');
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
    assert result["onOwnRow"], "toggle should render below the hamburger/title row"
    assert result["fullyOnScreen"], "toggle should not overflow past the viewport edge"
    assert result["notStretched"], "toggle should stay content-sized, not stretch full-width"


def test_toggle_stays_on_the_header_row_on_a_wide_viewport(page, site_url):
    """Above 45em, Material's own tab bar replaces the hamburger button entirely (it
    reports a zero-size rect rather than being absent, so it isn't a usable anchor
    here) — check against the title instead, and confirm the header itself stays a
    single row tall rather than the two rows the mobile CSS (scoped to max-width:
    45em, so it plainly can't apply here) would produce."""
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(site_url)
    result = page.evaluate(
        """() => {
            const title = document.querySelector('.md-header__title');
            const toggle = document.getElementById('fcm-toggle');
            const inner = document.querySelector('.md-header__inner');
            const g = title.getBoundingClientRect();
            const t = toggle.getBoundingClientRect();
            return {
                sameRow: Math.abs((t.top + t.bottom) / 2 - (g.top + g.bottom) / 2) < g.height,
                singleRowHeight: inner.getBoundingClientRect().height < 60,
            };
        }"""
    )
    assert result["sameRow"], "toggle should share the same row as the header title"
    assert result["singleRowHeight"], "header shouldn't be tall enough for two rows here"


def test_hash_recovery_picks_the_nearest_mode_that_reveals_it_not_just_the_default(page, site_url):
    """Regression: with 3+ modes, "the mode that reveals a hidden target" isn't
    necessarily the configured default. This fixture's modes are ordered
    beginner(0)/intermediate(1, default)/expert(2), and other.md's own
    '## Expert-only section { data-fcm-hide="beginner intermediate" }' is hidden in
    *both* beginner and the default (intermediate) — so landing there while in
    Beginner mode must skip straight to Expert (the only mode that actually shows
    it), not stop at the default, which would silently leave it hidden."""
    page.goto(f"{site_url}/other/?mode=beginner#expert-only-section")
    page.wait_for_function(
        "() => getComputedStyle(document.getElementById('expert-only-section')).display !== 'none'"
    )
    mode = page.evaluate("() => document.documentElement.getAttribute('data-fcm-mode')")
    assert mode == "expert", "should land on the only mode that reveals the target, not the default"


def test_hash_recovery_prefers_the_closer_mode_when_more_than_one_would_reveal_it(page, site_url):
    """Starting from Expert (index 2) and following a link hidden only in
    "beginner" (visible in both intermediate and expert already) shouldn't move
    the reader at all — they can already see it. This is really a sanity check
    that the recovery logic doesn't fire when nothing needs revealing."""
    page.goto(f"{site_url}/?mode=expert#advanced-topic")
    page.wait_for_timeout(100)
    mode = page.evaluate("() => document.documentElement.getAttribute('data-fcm-mode')")
    assert mode == "expert", "already-visible target should not trigger a mode switch"


def test_query_param_override_does_not_touch_the_url(page, site_url):
    """Regression: an earlier version stripped ?mode=... back out of the address bar
    via history.replaceState once applied, to avoid the one shared-link landing
    showing up as its own URL to analytics. That broke normal in-page navigation —
    Material for MkDocs bakes the *current* URL (query string included) into TOC/nav
    links as absolute hrefs during its own startup, which runs before this plugin's
    script; rewriting location afterward left those already-baked-in links pointing
    at a URL that no longer matched, turning what should be an in-page hash jump into
    a full reload. The mode still needs to apply — the URL just has to stay put."""
    page.goto(f"{site_url}/?mode=expert&keep=me#advanced-topic")
    page.wait_for_function("() => document.documentElement.getAttribute('data-fcm-mode') === 'expert'")

    result = page.evaluate(
        """() => ({ search: location.search, hash: location.hash })"""
    )
    assert "mode=expert" in result["search"], "the query param should stay in the URL, untouched"
    assert "keep=me" in result["search"]
    assert result["hash"] == "#advanced-topic"


def test_query_param_with_unrecognized_value_is_ignored(page, site_url):
    page.goto(f"{site_url}/?mode=not-a-real-mode")
    mode = page.evaluate("() => document.documentElement.getAttribute('data-fcm-mode')")
    assert mode == "intermediate", "an unrecognized mode value should be ignored, falling back to default"


def test_modechange_event_fires_with_the_new_and_previous_mode(page, site_url):
    """Documented in the README's 'Reacting to the active mode elsewhere' section as
    the way to hook analytics up to mode switches without polling data-fcm-mode."""
    page.goto(site_url)
    page.evaluate(
        """() => {
            window.__events = [];
            document.addEventListener('fcm:modechange', (e) => window.__events.push(e.detail));
        }"""
    )
    page.click('.fcm-option[data-name="expert"]')
    events = page.evaluate("() => window.__events")
    assert events == [{"mode": "expert", "previousMode": "intermediate"}]


def test_modechange_event_does_not_fire_for_a_no_op_click(page, site_url):
    page.goto(site_url)
    page.evaluate(
        """() => {
            window.__events = [];
            document.addEventListener('fcm:modechange', (e) => window.__events.push(e.detail));
        }"""
    )
    page.click('.fcm-option[data-name="intermediate"]')  # already active
    events = page.evaluate("() => window.__events")
    assert events == []


def test_hash_recovery_finds_the_mode_for_a_subheading_inside_a_hidden_section(page, site_url):
    """other.md's '### Expert subsection' has no attribute of its own. It's hidden
    because its parent '## Expert-only section' is marked "beginner intermediate",
    so from Beginner the only mode that shows it is Expert, not the default
    (Intermediate), which also hides it."""
    page.goto(f"{site_url}/other/?mode=beginner#expert-subsection")
    page.wait_for_function(
        "() => getComputedStyle(document.getElementById('expert-subsection')).display !== 'none'"
    )
    mode = page.evaluate("() => document.documentElement.getAttribute('data-fcm-mode')")
    assert mode == "expert"


def test_hash_recovery_finds_the_mode_for_a_heading_inside_a_hidden_div(page, site_url):
    """The heading sits inside a <div data-fcm-hide="intermediate">, so it has no
    attribute and no inline style of its own. From Intermediate, Beginner and
    Expert both show it at the same distance; the later mode in the list wins."""
    page.goto(f"{site_url}/other/?mode=intermediate#heading-inside-a-hidden-div")
    page.wait_for_function(
        """() => {
            const heading = document.getElementById('heading-inside-a-hidden-div');
            return heading.getClientRects().length > 0;
        }"""
    )
    mode = page.evaluate("() => document.documentElement.getAttribute('data-fcm-mode')")
    assert mode == "expert"
