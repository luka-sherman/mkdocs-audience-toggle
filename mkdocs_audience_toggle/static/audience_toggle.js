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

  // A heading hides its whole section: every following sibling up to the next
  // heading of the same or higher level.
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

  // Material can render the same TOC link more than once (primary nav and
  // secondary sidebar), so hide every match.
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

    container.dataset.active = mode;
    var activeOption = null;
    container.querySelectorAll(".fcm-option").forEach(function (option) {
      var isActive = option.dataset.name === mode;
      option.setAttribute("aria-pressed", String(isActive));
      if (isActive) activeOption = option;
    });
    positionHighlight(container, activeOption);

    if (previousMode !== mode) {
      document.dispatchEvent(
        new CustomEvent("fcm:modechange", { detail: { mode: mode, previousMode: previousMode } })
      );
    }
  }

  // Options size to their labels, so the highlight is measured from the active
  // option rather than set to an equal share of the track.
  function positionHighlight(container, activeOption) {
    var highlight = container.querySelector(".fcm-highlight");
    if (!highlight || !activeOption) return;
    highlight.style.left = activeOption.offsetLeft + "px";
    highlight.style.width = activeOption.offsetWidth + "px";
  }

  // Material header only: if the toggle wrapped below the title, give it a row
  // to itself (see .fcm-toggle--own-row in the CSS). Measured with the class
  // off, so the toggle keeps its place whenever it fits.
  function updateHeaderRow(container) {
    var inner = container.parentElement;
    if (!inner || !inner.classList.contains("md-header__inner")) return;
    var title = inner.querySelector(".md-header__title");
    if (!title) return;

    container.classList.remove("fcm-toggle--own-row");
    var wrapped = container.getBoundingClientRect().top >= title.getBoundingClientRect().bottom - 1;
    container.classList.toggle("fcm-toggle--own-row", wrapped);
  }

  function refreshLayout() {
    var container = document.getElementById("fcm-toggle");
    if (!container) return;
    updateHeaderRow(container);
    positionHighlight(container, container.querySelector('.fcm-option[aria-pressed="true"]'));
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

    // Force a reflow so the transition restarts if the toast is already showing.
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

  function marksMode(el, mode, config) {
    var tokens = (el.getAttribute(config.attribute) || "").split(/\s+/).filter(Boolean);
    return tokens.indexOf(mode) !== -1;
  }

  function headingLevel(el) {
    return /^H[1-6]$/.test(el.tagName) ? Number(el.tagName[1]) : null;
  }

  // Same rules as setElementHidden, checked without changing the page.
  function isHiddenInMode(el, mode, config) {
    for (var node = el; node && node !== document.body; node = node.parentElement) {
      if (marksMode(node, mode, config)) return true;

      // An earlier sibling heading owns `node` if it's a higher level than
      // `node` and every heading in between.
      var limit = headingLevel(node) || 7;
      for (var sib = node.previousElementSibling; sib && limit > 1; sib = sib.previousElementSibling) {
        var level = headingLevel(sib);
        if (level === null || level >= limit) continue;
        if (marksMode(sib, mode, config)) return true;
        limit = level;
      }

      var first = node.firstElementChild;
      if (
        first &&
        headingLevel(first) &&
        marksMode(first, mode, config) &&
        (config.wrapperClasses || []).some(function (cls) {
          return node.classList.contains(cls);
        })
      ) {
        return true;
      }
    }
    return false;
  }

  // Checks modes one position away from the current mode, then two, and so
  // on. On a tie, the later mode in the list wins.
  function findNearestVisibleMode(target, config, currentIndex) {
    for (var distance = 1; distance < config.modes.length; distance++) {
      var candidates = [currentIndex + distance, currentIndex - distance];
      for (var i = 0; i < candidates.length; i++) {
        var mode = config.modes[candidates[i]];
        if (mode && !isHiddenInMode(target, mode.name, config)) return mode.name;
      }
    }
    return null;
  }

  function revealHashTargetIfHidden(container, config) {
    if (!location.hash) return;
    var target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    var current = container.dataset.active;
    if (!target || !isHiddenInMode(target, current, config)) return;

    var currentIndex = config.modes.findIndex(function (m) {
      return m.name === current;
    });
    var nextMode = findNearestVisibleMode(target, config, currentIndex);
    if (nextMode === null) return;

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
    refreshLayout();

    // Label widths can change when a web font finishes loading.
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(refreshLayout);
    }

    // setUp runs on every page change with navigation.instant, so bind
    // window listeners only once.
    if (!window.__fcmHashRecoveryBound) {
      window.__fcmHashRecoveryBound = true;
      window.addEventListener("hashchange", function () {
        var current = document.getElementById("fcm-toggle");
        if (current) revealHashTargetIfHidden(current, config);
      });
    }

    if (!window.__fcmResizeBound) {
      window.__fcmResizeBound = true;
      window.addEventListener("resize", refreshLayout);
    }
  }

  // Material's document$ emits on every page change, including instant
  // navigation, where DOMContentLoaded only fires once.
  if (window.document$) {
    window.document$.subscribe(setUp);
  } else {
    document.addEventListener("DOMContentLoaded", setUp);
  }
})();
