# Fixture Site

Intro paragraph, visible in every mode.

Some inline text with a <span data-fcm-hide="beginner intermediate">phrase hidden except in Expert</span> mixed in.

Link to a section that's hidden in Beginner mode: [jump to Advanced topic](#advanced-topic).

## Advanced topic {: data-fcm-hide="beginner" }

This whole section, including this paragraph, is hidden while Beginner is active.

<div class="wrap-me" markdown="block">
### Wrapped heading {: data-fcm-hide="beginner" }

This heading's whole `.wrap-me` wrapper should hide too, not just the heading and its siblings.
</div>

<div class="grid cards" markdown="block">

-   __Card A__
    {: data-fcm-hide="beginner" }

    This card should disappear entirely in Beginner mode, not just its first line.

-   __Card B__

    This card stays visible in every mode.

</div>
