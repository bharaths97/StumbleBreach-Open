// ui/route-prefix.js — makes a service's pages work both standalone on their own
// port and mounted behind a Pavilion proxy_path, without the page knowing which.
//
// Declare the service's registry proxy_path on the script tag:
//   <script src="/ui/route-prefix.js" data-proxy-path="/mytool"></script>
//
// When the current URL sits under that path, every same-origin absolute link and
// fetch is rewritten to carry the prefix. Served standalone the prefix is empty
// and every rewrite is a no-op, so a service never depends on Pavilion running.
//
// Baseline file. See docs/design/UI-BASELINE.md. Pavilion ships a superset of this
// (multi-tool cross-linking between resume-ops and indeed) and is not expected
// to match byte-for-byte; it is excluded from the ui-drift check.
(function (global) {
  var script = document.currentScript;
  var declared = script && script.dataset ? (script.dataset.proxyPath || '') : '';
  var pathname = window.location.pathname;
  var prefix = declared && (pathname === declared || pathname.indexOf(declared + '/') === 0) ? declared : '';

  // Absolute same-origin paths only. Protocol-relative and fully qualified URLs
  // are left alone so an outbound link is never rewritten into the proxy.
  function withPrefix(value) {
    if (typeof value !== 'string' || !prefix) return value;
    if (value.charAt(0) !== '/' || value.charAt(1) === '/') return value;
    if (value === prefix || value.indexOf(prefix + '/') === 0) return value;
    var parsed = new URL(value, window.location.origin);
    return prefix + parsed.pathname + parsed.search + parsed.hash;
  }

  // Root of the dashboard when mounted, empty when standalone — so a nav can do
  // `pavilionPath() ? renderBackLink() : null` without branching on anything else.
  function pavilionPath() {
    return prefix ? '/' : '';
  }

  if (prefix && window.fetch) {
    var nativeFetch = window.fetch.bind(window);
    window.fetch = function (input, init) {
      if (typeof input === 'string') return nativeFetch(withPrefix(input), init);
      if (input && typeof input.url === 'string') {
        var nextUrl = withPrefix(input.url);
        if (nextUrl !== input.url) input = new Request(nextUrl, input);
      }
      return nativeFetch(input, init);
    };
  }

  document.addEventListener('click', function (event) {
    var link = event.target && event.target.closest ? event.target.closest('a[href]') : null;
    if (!link || link.target || event.defaultPrevented || link.hasAttribute('data-route-prefix-skip')) return;
    var href = link.getAttribute('href');
    var next = withPrefix(href);
    if (next === href) return;
    event.preventDefault();
    window.location.href = next;
  });

  global.RoutePrefix = { path: withPrefix, pavilionPath: pavilionPath };
})(window);
