// ui/sidebar-drawer.js — shared drawer open/closed + tool-switcher state mechanics
// for the category nav panel. A service keeps its own nav *content* (links, groups,
// buttons); this module owns only the open/closed state: the localStorage keys, the
// toggle handlers, and the .category-nav-open / .category-nav-closed bookkeeping.
//
// Baseline file. See docs/design/UI-BASELINE.md before changing it here, and copy
// down to consumers rather than editing a consumer's copy in place.
(function (global) {
  var NAV_KEY = 'pavilionCategoryNavCollapsed';

  function createSidebarDrawer(options) {
    var containerEl = typeof options.container === 'string' ? document.querySelector(options.container) : options.container;
    var navKey = options.navKey || NAV_KEY;
    var legacyNavKey = options.legacyNavKey || null;
    var mediaQuery = window.matchMedia('(max-width:820px)');

    function readCollapsed() {
      var stored = legacyNavKey
        ? (localStorage.getItem(navKey) ?? localStorage.getItem(legacyNavKey))
        : localStorage.getItem(navKey);
      return mediaQuery.matches || stored === 'true';
    }

    var state = { navCollapsed: readCollapsed() };

    function render() {
      var mobile = mediaQuery.matches;
      var panel = document.getElementById('category-panel');
      var backdrop = document.getElementById('category-backdrop');
      var toggle = document.getElementById('category-toggle');
      if (panel) panel.classList.toggle('collapsed', state.navCollapsed);
      if (backdrop) backdrop.classList.toggle('visible', mobile && !state.navCollapsed);
      if (containerEl) {
        containerEl.classList.toggle('category-nav-open', !mobile && !state.navCollapsed);
        containerEl.classList.toggle('category-nav-closed', mobile || state.navCollapsed);
      }
      document.body.style.overflow = mobile && !state.navCollapsed ? 'hidden' : '';
      if (toggle) {
        toggle.textContent = state.navCollapsed ? '☰' : '×';
        toggle.setAttribute('aria-expanded', String(!state.navCollapsed));
      }
      if (options.onRender) options.onRender();
    }

    function setCollapsed(value) {
      state.navCollapsed = value;
      localStorage.setItem(navKey, String(value));
      if (options.writeLegacyNavKey && legacyNavKey) localStorage.setItem(legacyNavKey, String(value));
      render();
    }

    function isCollapsed() {
      return state.navCollapsed;
    }

    var toggleButton = document.getElementById('category-toggle');
    if (toggleButton) toggleButton.addEventListener('click', function () { setCollapsed(!state.navCollapsed); });
    var backdropEl = document.getElementById('category-backdrop');
    if (backdropEl) backdropEl.addEventListener('click', function () { setCollapsed(true); });
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', function () {
        state.navCollapsed = readCollapsed();
        render();
      });
    }

    // Apply the saved/default state before the caller can render content.
    render();

    return { render: render, setCollapsed: setCollapsed, isCollapsed: isCollapsed };
  }

  function createToolSwitcherToggle(key) {
    return {
      isCollapsed: function () { return localStorage.getItem(key) === 'true'; },
      toggle: function () { localStorage.setItem(key, String(localStorage.getItem(key) !== 'true')); },
    };
  }

  // Builds the tool-switcher button with the hamburger indicator (☰ collapsed,
  // × expanded) next to its label. Factored here so a service never hand-rolls
    // this markup — three pages each reimplemented it identically, which
  // is the duplication this function exists to stop repeating.
  function createToolSwitcherButton(options) {
    var collapsed = !!options.collapsed;
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'menu-switcher-toggle menu-color-' + (options.color || 'dashboard');
    button.setAttribute('aria-expanded', String(!collapsed));
    button.innerHTML = '<span class="menu-switcher-icon" aria-hidden="true">' + (collapsed ? '☰' : '×') +
      '</span><span>&gt; ' + (options.label || './tools') + '</span>';
    if (options.onClick) button.addEventListener('click', options.onClick);
    return button;
  }

  global.SidebarDrawer = {
    createSidebarDrawer: createSidebarDrawer,
    createToolSwitcherToggle: createToolSwitcherToggle,
    createToolSwitcherButton: createToolSwitcherButton,
  };
})(window);
