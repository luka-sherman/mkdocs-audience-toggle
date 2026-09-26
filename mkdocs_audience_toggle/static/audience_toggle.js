(function () {
  "use strict";

  var CONFIG_SCRIPT_ID = "fcm-config";

  function readConfig() {
    var el = document.getElementById(CONFIG_SCRIPT_ID);
    if (!el) return null;
    try {
      var config = JSON.parse(el.textContent);
      if (!config.modes || !config.modes.length) return null;
      return config;
    } catch (e) {
      return null;
    }
  }

  // Hides/restores an element and, if it's a heading, its whole section
  // (every sibling up to the next heading of the same or higher level).
  function setElementHidden(el, hidden, config) {
    el.style.display = hidden ? "none" : "";

    if (/^H[1-6]$/.test(el.tagName)) {
      var level = Number(el.tagName[1]);
      var sib = el.nextElementSibling;
      while (sib && !(/^H[1-6]$/.test(sib.tagName) && Number(sib.tagName[1]) <= level)) {
        sib.style.display = hidden ? "none" : "";
        sib = sib.nextElementSibling;
      }

      var wrapper = el.parentElement;
      if (
        wrapper &&
        config.wrapperClasses &&
        config.wrapperClasses.length &&
        wrapper.firstElementChild === el &&
        config.wrapperClasses.some(function (cls) {
          return wrapper.classList.contains(cls);
        })
      ) {
        wrapper.style.display = hidden ? "none" : "";
      }

      if (config.hideTocEntries && el.id) {
        setTocEntryHidden(el.id, hidden);
      }
    }
  }

  // Material's toc.integrate nests a page's headings as <a> links in the
  // left nav; hide the matching entry too so there's no dead link to
  // hidden content. querySelectorAll covers both the inert copy inside
  // the primary nav and the real one in a secondary sidebar, if present.
  function setTocEntryHidden(id, hidden) {
    document.querySelectorAll('a.md-nav__link[href$="#' + id + '"]').forEach(function (link) {
      var item = link.closest(".md-nav__item");
      if (item) item.style.display = hidden ? "none" : "";
    });
  }

  function applyContentVisibility(mode, config) {
    var selector = "[" + config.attribute + "]";
    document.querySelectorAll(selector).forEach(function (el) {
      var tokens = (el.getAttribute(config.attribute) || "").split(/\s+/).filter(Boolean);
      setElementHidden(el, tokens.indexOf(mode) !== -1, config);
    });
  }

  function applyState(container, mode, config) {
    var previousMode = container.dataset.active || null;

    document.documentElement.setAttribute("data-fcm-mode", mode);
    applyContentVisibility(mode, config);

    var index = config.modes.findIndex(function (m) {
      return m.name === mode;
    });
    container.dataset.active = mode;
    var activeOption = null;
    container.querySelectorAll(".fcm-option").forEach(function (option) {
      var isActive = option.dataset.name === mode;
      option.setAttribute("aria-pressed", String(isActive));
      if (isActive) activeOption = option;
    });
    positionHighlight(container, activeOption);

    // Callers only ever call applyState when the mode is actually changing
    // (or on first setup, where previousMode is null) — every caller already
    // guards the no-op case before calling in. Dispatched on `document`
    // (not the container) so a site's analytics snippet can add one
    // top-level listener without needing a reference to the toggle itself.
    if (previousMode !== mode) {
      document.dispatchEvent(
        new CustomEvent("fcm:modechange", { detail: { mode: mode, previousMode: previousMode } })
      );
    }
  }

  // Options are flex children, not evenly divided fractions of the track —
  // a flex item's default min-width: auto keeps it from shrinking below
  // its own label's content width, so options with different-length
  // labels end up different widths (most visible with 3+ modes). Measure
  // the actual active button instead of assuming an equal 100%/count
  // share, so the highlight lines up regardless of label length.
  function positionHighlight(container, activeOption) {
    var highlight = container.querySelector(".fcm-highlight");
    if (!highlight || !activeOption) return;
    highlight.style.left = activeOption.offsetLeft + "px";
    highlight.style.width = activeOption.offsetWidth + "px";
  }

  var toastTimer = null;
  function showToast(mode, config) {
    if (!config.showToast) return;
    var text = mode.announcement || mode.label;
    if (!text) return;

    var toast = document.getElementById("fcm-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "fcm-toast";
      toast.className = "fcm-toast";
      toast.setAttribute("role", "status");
      toast.setAttribute("aria-live", "polite");
      document.body.appendChild(toast);
    }
    toast.textContent = text;

    var header = document.querySelector(".md-header");
    var headerBottom = header ? header.getBoundingClientRect().bottom : 0;
    toast.style.top = Math.max(headerBottom, 0) + 12 + "px";

    toast.classList.remove("fcm-toast--visible");
    void toast.offsetWidth;
    toast.classList.add("fcm-toast--visible");

    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.classList.remove("fcm-toast--visible");
    }, 1400);
  }

  function buildToggle(config) {
    var container = document.createElement("div");
    container.id = "fcm-toggle";
    container.className = "fcm-toggle";
    container.setAttribute("role", "group");
    container.setAttribute("aria-label", config.ariaLabel || "Content mode");
    if (config.collapseLabels) container.setAttribute("data-collapse-labels", "");

    var highlight = document.createElement("span");
    highlight.className = "fcm-highlight";
    highlight.setAttribute("aria-hidden", "true");
    container.appendChild(highlight);

    config.modes.forEach(function (mode) {
      var option = document.createElement("button");
      option.type = "button";
      option.className = "fcm-option";
      if (mode.icon) option.className += " fcm-option--icon";
      option.dataset.name = mode.name;
      if (mode.description) option.title = mode.description;
      if (mode.icon) option.style.setProperty("--fcm-icon", mode.icon);

      var label = document.createElement("span");
      label.className = "fcm-label";
      label.textContent = mode.label;
      option.appendChild(label);

      container.appendChild(option);
    });

    container.addEventListener("click", function (event) {
      var option = event.target.closest(".fcm-option");
      if (!option) return;
      var name = option.dataset.name;
      if (container.dataset.active === name) return;
      localStorage.setItem(config.storageKey, name);
      applyState(container, name, config);
      var mode = config.modes.find(function (m) {
        return m.name === name;
      });
      if (mode) showToast(mode, config);
    });

    return container;
  }

  function getOrCreateToggle(config) {
    var existing = document.getElementById("fcm-toggle");
    if (existing) return existing;

    var anchor = config.insertSelector ? document.querySelector(config.insertSelector) : null;
    var container = buildToggle(config);

    if (anchor) {
      anchor.insertAdjacentElement("beforebegin", container);
    } else {
      document.body.appendChild(container);
    }

    return container;
  }

  // With 3+ modes, the mode that reveals a given hidden target isn't
  // necessarily the configured default — e.g. beginner/intermediate/advanced,
  // currently on "beginner", clicking a link hidden only in beginner/advanced:
  // "intermediate" (one step away) reveals it and is the better landing spot
  // than jumping past it to "advanced" just because that's the default.
  // `config.modes` order is taken as the author's own progression (the same
  // order they render left-to-right), so "nearest" means nearest by index,
  // checked outward from the current mode one step at a time; a higher index
  // is tried before an equally-distant lower one, an arbitrary but
  // deterministic tiebreak.
  function findNearestVisibleMode(target, config, currentIndex) {
    var tokens = (target.getAttribute(config.attribute) || "").split(/\s+/).filter(Boolean);
    if (!tokens.length) return null;
    for (var distance = 1; distance < config.modes.length; distance++) {
      var higher = currentIndex + distance;
      var lower = currentIndex - distance;
      if (higher < config.modes.length && tokens.indexOf(config.modes[higher].name) === -1) {
        return config.modes[higher].name;
      }
      if (lower >= 0 && tokens.indexOf(config.modes[lower].name) === -1) {
        return config.modes[lower].name;
      }
    }
    return null;
  }

  // A visible link (e.g. a cheat-sheet table) can point at a section that's
  // hidden in the current mode. Switch to the nearest mode that actually
  // reveals it instead of landing on nothing.
  function revealHashTargetIfHidden(container, config) {
    if (!location.hash) return;
    var target = document.getElementById(location.hash.slice(1));
    if (!target || target.style.display !== "none") return;

    var currentIndex = config.modes.findIndex(function (m) {
      return m.name === container.dataset.active;
    });
    var nextMode = findNearestVisibleMode(target, config, currentIndex);
    if (nextMode === null) {
      // Either every mode hides it (switching wouldn't help — leave the
      // reader's chosen mode alone rather than jumping for nothing), or the
      // target has no attribute of its own to reason about (hidden some
      // other way, e.g. an ancestor wrapper) — fall back to the old
      // single-default behavior as a best-effort guess in that case.
      var tokens = (target.getAttribute(config.attribute) || "").split(/\s+/).filter(Boolean);
      if (tokens.length) return;
      nextMode = config.defaultMode;
    }
    if (nextMode === container.dataset.active) return;

    localStorage.setItem(config.storageKey, nextMode);
    applyState(container, nextMode, config);
  }

  function setUp() {
    var config = readConfig();
    if (!config) return;

    var container = getOrCreateToggle(config);

    var initial = config.defaultMode;
    var stored = localStorage.getItem(config.storageKey);
    if (stored && config.modes.some(function (m) { return m.name === stored; })) {
      initial = stored;
    }
    if (config.queryParam) {
      var override = new URLSearchParams(window.location.search).get(config.queryParam);
      if (override && config.modes.some(function (m) { return m.name === override; })) {
        localStorage.setItem(config.storageKey, override);
        initial = override;
      }
    }

    applyState(container, initial, config);
    revealHashTargetIfHidden(container, config);

    // A webfont (e.g. Material's Roboto, loaded async) can still be mid-swap when
    // this runs on DOMContentLoaded — measuring the active option's width against
    // fallback-font metrics, then never correcting once the real font lands and
    // reflows the label. document.fonts.ready resolves once every requested font has
    // finished loading, so reposition once more after that settles.
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () {
        var current = document.getElementById("fcm-toggle");
        if (!current) return;
        var active = current.querySelector('.fcm-option[aria-pressed="true"]');
        positionHighlight(current, active);
      });
    }

    if (!window.__fcmHashRecoveryBound) {
      window.__fcmHashRecoveryBound = true;
      window.addEventListener("hashchange", function () {
        var current = document.getElementById("fcm-toggle");
        if (current) revealHashTargetIfHidden(current, config);
      });
    }

    // A viewport resize can reflow option widths (e.g. collapseLabels
    // hiding text below its breakpoint), which would leave the highlight
    // sized/positioned for the old layout.
    if (!window.__fcmResizeBound) {
      window.__fcmResizeBound = true;
      window.addEventListener("resize", function () {
        var current = document.getElementById("fcm-toggle");
        if (!current) return;
        var active = current.querySelector('.fcm-option[aria-pressed="true"]');
        positionHighlight(current, active);
      });
    }
  }

  // navigation.instant (Material) swaps page content via JS without a
  // full reload, so DOMContentLoaded only fires once. document$ is
  // Material's own observable that emits on every page change, instant
  // or not; fall back to DOMContentLoaded for other themes/setups.
  if (window.document$) {
    window.document$.subscribe(setUp);
  } else {
    document.addEventListener("DOMContentLoaded", setUp);
  }
})();
