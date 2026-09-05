/* Read-only engagement dashboard. API requests are GET; future actions are labels only. */
(function () {
  "use strict";

  var routes = { overview: "/api/overview", engagements: "/api/engagements", engagement: "/api/engagements/", health: "/api/health", controls: "/api/controls", handoffs: "/api/handoffs", tooling: "/api/tooling", runStatus: "/api/run-status" };
  var OPEN_ENGAGEMENTS_KEY = "stumblebreachOpenEngagements";
  var tabs = ["overview", "workboard", "journey", "findings", "evidence", "delegation", "health"];
  var root = document.getElementById("dashboard"), model = {};

  function safePrefix(value) {
    if (typeof value !== "string" || value.indexOf("/") !== 0 || value.indexOf("//") === 0 || /[?#]/.test(value) || value.indexOf("\\") >= 0) return null;
    return value === "/" ? "" : value.replace(/\/+$/, "");
  }
  function deploymentPrefix() {
    var configured = document.documentElement && document.documentElement.getAttribute("data-dashboard-api-base");
    if (configured !== null && configured !== undefined) { var configuredPrefix = safePrefix(configured); if (configuredPrefix !== null) return configuredPrefix; }
    var script = document.currentScript;
    if (!script) return "";
    try { var page = new URL(document.baseURI), scriptUrl = new URL(script.getAttribute("src") || "", page); if (scriptUrl.origin !== page.origin) return ""; var slash = scriptUrl.pathname.lastIndexOf("/"); return slash > 0 ? scriptUrl.pathname.slice(0, slash).replace(/\/+$/, "") : ""; } catch (_) { return ""; }
  }
  var apiPrefix = deploymentPrefix();
  function apiPath(path) { return apiPrefix + path; }
  function get(path) {
    var requestPath = apiPath(path);
    return fetch(requestPath, { method: "GET", headers: { Accept: "application/json" } }).then(function (response) { if (!response.ok) throw new Error(requestPath + " returned HTTP " + response.status); return response.json(); });
  }
  function optional(path) { return get(path).catch(function () { return null; }); }
  function el(tag, text, className) { var node = document.createElement(tag); if (text !== undefined && text !== null) node.textContent = String(text); if (className) node.className = className; return node; }
  function section(id, title, detail) { var node = el("section", undefined, "panel"); if (id) node.id = id; var heading = el("div", undefined, "panel-heading"); heading.append(el("h2", title), detail ? el("span", detail, "muted") : el("span")); node.appendChild(heading); return node; }
  function badge(value) { var state = String(value || "unknown"); return el("span", state, "pill pill-" + state.toLowerCase().replace(/[^a-z0-9]+/g, "-")); }
  function stateOf(value) { return (value && value.state) || value || "unknown"; }
  function textValue(value, fallback) { return value === undefined || value === null || value === "" ? (fallback || "unknown") : String(value); }
  function source(value) { return el("code", value ? "source: " + value : "source: unavailable", "source-ref"); }
  function empty(text) { return el("p", text || "No records supplied by the read-only API.", "empty muted"); }
  function meaning(selected, subject) {
    return el("p", "What this means: " + subject + " is reported for operator review; the next decision stays with the engagement owner.", "meaning");
  }
  function details(items) {
    var disclosure = el("details", undefined, "details"); disclosure.appendChild(el("summary", "Details")); var list = el("ul");
    (items || []).forEach(function (item) { list.appendChild(el("li", item)); }); disclosure.appendChild(list); return disclosure;
  }
  function renderTable(host, key, columns, rows) {
    if (!rows.length) { host.appendChild(empty("No records supplied by this engagement.")); return; }
    var renderRow = function (row) { var tr = el("tr"); columns.forEach(function (column) { var td = el("td"); td.dataset.column = column.key; td.appendChild(column.render ? column.render(row) : el("span", textValue(row[column.key], ""))); tr.appendChild(td); }); return tr; };
    if (window.DataTable && typeof window.DataTable.render === "function") { window.DataTable.render(host, { storageKey: key, columns: columns.map(function (column) { return { key: column.key, label: column.label, sortable: column.sortable !== false }; }), rows: rows, renderRow: renderRow }); return; }
    var table = el("table", undefined, "data-table"), head = el("tr"), thead = el("thead"), body = el("tbody"); columns.forEach(function (column) { var th = el("th", column.label); th.dataset.column = column.key; head.appendChild(th); }); thead.appendChild(head); table.appendChild(thead); rows.forEach(function (row) { body.appendChild(renderRow(row)); }); table.appendChild(body); var wrap = el("div", undefined, "table-wrap"); wrap.appendChild(table); host.appendChild(wrap);
  }
  function hashState() {
    var raw = (window.location.hash || "").slice(1), params = new URLSearchParams(raw), tab = params.get("tab");
    return { engagement: params.get("engagement"), tab: tabs.indexOf(tab) >= 0 ? tab : "overview", filter: (params.get("filter") || "all").toLowerCase(), page: raw === "system-health" ? "health" : raw === "settings" ? "settings" : "overview" };
  }
  function engagementHref(branch, tab) { return "#engagement=" + encodeURIComponent(branch) + "&tab=" + (tab || "overview"); }
  function mergeEngagement(summary, detail) {
    var payload = detail && detail.engagement && typeof detail.engagement === "object" ? detail.engagement : detail;
    if (!payload || typeof payload !== "object") return summary;
    return Object.assign({}, summary, payload, { branch: summary.branch, analysis: payload.analysis || summary.analysis });
  }
  function engagementForHash(records, hash) {
    var branch = new URLSearchParams(String(hash || "").replace(/^#/, "")).get("engagement");
    return (records || []).find(function (item) { return item && String(item.branch) === String(branch); });
  }
  function overviewCards(records) {
    var overview = model.overview || {}, wrap = el("div", undefined, "summary-grid"), count = function (status) { return records.filter(function (item) { return String(item.status).toLowerCase() === status; }).length; };
    [["Engagements", overview.engagement_count || records.length, "all registered records", "accent"], ["Active", count("active"), "operator-owned work", "success"], ["Paused", count("paused"), "held for review", "warning"], ["Closed", count("closed"), "retained records", "danger"]].forEach(function (item) { var card = el("article", undefined, "metric " + item[3]); card.append(el("span", item[0], "label"), el("strong", item[1]), el("small", item[2], "muted")); wrap.appendChild(card); }); return wrap;
  }
  function engagementTable(host, records, key) {
    var rows = records.map(function (item) { return { name: textValue(item.name, "Unnamed"), type: textValue(item.type), status: textValue(item.status), branch: textValue(item.branch, "unavailable"), view: textValue(item.view || (item.analysis && item.analysis.view)), data: stateOf(item.data_state) }; });
    renderTable(host, key, [{ key: "name", label: "Engagement", render: function (row) { var link = el("a", row.name, "engagement-link"); link.href = engagementHref(row.branch); return link; } }, { key: "type", label: "Type" }, { key: "status", label: "Status", render: function (row) { return badge(row.status); } }, { key: "branch", label: "Branch" }, { key: "view", label: "View" }, { key: "data", label: "Data" }], rows);
  }
  function overviewPanel(records, state) {
    var panel = section("overview", "Engagement overview", state.filter === "all" ? "all engagements" : state.filter + " engagements"), visible = state.filter === "all" ? records : records.filter(function (item) { return String(item.status).toLowerCase() === state.filter; });
    panel.appendChild(overviewCards(records)); var host = el("div"); engagementTable(host, visible, "stumblebreach-engagements-" + state.filter); panel.appendChild(host); if (!visible.length) panel.appendChild(empty("No engagements match this filter.")); panel.appendChild(details(["Source: main:ENGAGEMENTS.md", "Generated: " + textValue(model.generated_at, "time unavailable")])); return panel;
  }
  function tabNav(selected, active) {
    var nav = el("nav", undefined, "tabs"); nav.setAttribute("aria-label", "Engagement sections"); tabs.forEach(function (tab) { var link = el("a", tab.charAt(0).toUpperCase() + tab.slice(1), tab === active ? "active" : ""); link.href = engagementHref(selected.branch, tab); if (tab === active) link.setAttribute("aria-current", "page"); nav.appendChild(link); }); return nav;
  }
  function openEngagements() {
    try {
      var stored = JSON.parse(localStorage.getItem(OPEN_ENGAGEMENTS_KEY) || "[]");
      var normalized = [], seen = {};
      (Array.isArray(stored) ? stored : []).forEach(function (branch) {
        if (typeof branch === "string" && branch && !seen[branch]) { seen[branch] = true; normalized.push(branch); }
      });
      if (JSON.stringify(stored) !== JSON.stringify(normalized)) localStorage.setItem(OPEN_ENGAGEMENTS_KEY, JSON.stringify(normalized));
      return normalized;
    } catch (_) { return []; }
  }
  function rememberEngagement(branch) {
    if (!branch) return;
    var branches = openEngagements();
    if (branches.indexOf(branch) >= 0) return;
    branches.push(branch);
    localStorage.setItem(OPEN_ENGAGEMENTS_KEY, JSON.stringify(branches));
  }
  function renderEngagementTabs(activeBranch) {
    var host = document.getElementById("engagement-tabs");
    if (!host) return;
    host.replaceChildren();
    openEngagements().forEach(function (branch) {
      var tab = el("span", undefined, "nav-job-tab"), link = el("a", branch), close = el("button", "×", "nav-job-close");
      tab.classList.toggle("active", branch === activeBranch);
      link.href = engagementHref(branch, "overview");
      close.type = "button";
      close.setAttribute("aria-label", "Close " + branch);
      close.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        var remaining = openEngagements().filter(function (item) { return item !== branch; });
        localStorage.setItem(OPEN_ENGAGEMENTS_KEY, JSON.stringify(remaining));
        if (branch === activeBranch) window.location.hash = remaining.length ? engagementHref(remaining[remaining.length - 1], "overview") : "filter=all";
        else renderEngagementTabs(activeBranch);
      });
      tab.append(link, close);
      host.appendChild(tab);
    });
  }
  function overviewTab(selected) { var panel = section("engagement-overview", "Overview", selected.name || "selected engagement"), host = el("div"); panel.appendChild(meaning(selected, "The selected engagement")); renderTable(host, "stumblebreach-selected-engagement", [{ key: "field", label: "Field" }, { key: "value", label: "Value" }], [{ field: "Name", value: textValue(selected.name) }, { field: "Branch", value: textValue(selected.branch) }, { field: "Type", value: textValue(selected.type) }, { field: "Status", value: textValue(selected.status) }, { field: "Data", value: stateOf(selected.data_state) }]); panel.append(host, details(["Source: main:ENGAGEMENTS.md · engagement detail route", "Created: " + textValue(selected.created, "timestamp unavailable") ])); return panel; }
  function workboardTab(selected) {
    var analysis = selected.analysis || {}, panel = section("workboard", "Workboard", analysis.view === "ctf" ? "challenge progress" : "coverage and queue"), host = el("div");
    if (analysis.view === "ctf") { renderTable(host, "stumblebreach-ctf-challenges", [{ key: "name", label: "Challenge" }, { key: "state", label: "State", render: function (row) { return badge(row.state); } }, { key: "captured", label: "Captured" }, { key: "total", label: "Total" }], analysis.challenges || []); panel.append(meaning(selected, "Challenge progress"), host, details(["Source: STATUS.md", "Flag counts are read from challenge records."])); }
    else { var coverage = analysis.coverage || {}, queue = analysis.queue || {}, plan = analysis.plan || {}, rows = [{ name: "Coverage", state: stateOf(coverage.state), detail: coverage.record ? Object.keys(coverage.record.areas || {}).join(", ") || "record present" : "record unavailable" }, { name: "Queue", state: stateOf(queue.state), detail: "authoritative queue record" }, { name: "Finding plan", state: stateOf(plan.state), detail: (plan.done || 0) + " done / " + (plan.total || 0) + " total" }]; renderTable(host, "stumblebreach-coverage-queue", [{ key: "name", label: "Area" }, { key: "state", label: "State", render: function (row) { return badge(row.state); } }, { key: "detail", label: "Detail" }], rows); panel.append(meaning(selected, "Coverage and queue state"), host, details(["Source: harness/coverage.json · harness/queue.md · findings/plan.md"])); }
    return panel;
  }
  function findingsTab(selected) {
    var analysis = selected.analysis || {}, panel = section("findings", "Findings", "finding lifecycle"), rows = analysis.view === "ctf" ? (analysis.challenges || []).map(function (item) { return { name: item.name, state: item.state, evidence: item.captured + " captured" }; }) : [{ name: "Findings", state: stateOf((analysis.findings || {}).state), evidence: String((analysis.findings || {}).count || 0) + " records" }, { name: "Scope", state: stateOf((analysis.scope || {}).state), evidence: (analysis.scope || {}).source || "unavailable" }, { name: "Activity", state: stateOf((analysis.activity || {}).state), evidence: (analysis.activity || {}).last_timestamp || "timestamp unavailable" }];
    panel.appendChild(meaning(selected, "Finding and evidence records")); renderTable(panel, "stumblebreach-findings", [{ key: "name", label: "Record" }, { key: "state", label: "State", render: function (row) { return badge(row.state); } }, { key: "evidence", label: "Evidence" }], rows); panel.appendChild(details(["Source: " + (analysis.view === "ctf" ? "STATUS.md · challenges/" : "findings/ · evidence/ · scope.md · logs/activity.log")])); return panel;
  }
  function evidenceTab(selected) {
    var panel = section("evidence", "Evidence", "sanitized records"), items = (model.tooling && model.tooling.items || []).filter(function (item) { return !selected.branch || !item.branch || item.branch === selected.branch; }); panel.appendChild(meaning(selected, "Tool receipts")); renderTable(panel, "stumblebreach-tool-receipts", [{ key: "receipt_id", label: "Receipt" }, { key: "server_tool", label: "Tool" }, { key: "status", label: "Status", render: function (row) { return badge(row.status); } }, { key: "action", label: "Action" }, { key: "exit_code", label: "Exit" }], items); panel.appendChild(details(["Source: logs/tool-receipts.jsonl", "Actions are redacted by the read model."])); return panel;
  }

  function journeyData(selected) {
    var analysis = selected.analysis || {}, graph = analysis.journey || selected.journey || {}, rawNodes = Array.isArray(graph.nodes) ? graph.nodes : [], rawEdges = Array.isArray(graph.edges) ? graph.edges : [], nodes = rawNodes.map(function (node) { return { id: textValue(node.id), label: textValue(node.label, node.id), kind: textValue(node.kind), state: stateOf(node.state) }; });
    if (!nodes.length && Array.isArray(graph.events)) graph.events.forEach(function (event) { (event.node_ids || [event.id]).forEach(function (id) { if (!nodes.some(function (node) { return node.id === id; })) nodes.push({ id: id, label: textValue(event.summary, id), kind: textValue(event.role || event.actor, "event"), state: stateOf(event.provenance && event.provenance.review_state) }); }); });
    if (!nodes.length) [{ id: "engagement", label: textValue(selected.name, "Engagement"), kind: "engagement", state: textValue(selected.status) }, { id: "scope", label: "Scope", kind: "scope", state: stateOf(analysis.scope && analysis.scope.state) }, { id: "work", label: "Work records", kind: "work", state: "unknown" }].forEach(function (node) { nodes.push(node); });
    var ids = nodes.map(function (node) { return node.id; }); return { nodes: nodes, edges: rawEdges.filter(function (edge) { return edge && edge.provenance && edge.provenance.review_state === "accepted" && ids.indexOf(edge.from) >= 0 && ids.indexOf(edge.to) >= 0 && edge.from !== edge.to; }).map(function (edge) { return { from: edge.from, to: edge.to, type: textValue(edge.type, "relationship") }; }), gaps: graph.gaps || [] };
  }
  function svgNode(name, attrs) { var node = document.createElementNS("http://www.w3.org/2000/svg", name); Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); }); return node; }
  function journeyGraph(data) { var linked = {}; data.edges.forEach(function (edge) { linked[edge.from] = true; linked[edge.to] = true; }); data = { nodes: data.nodes.filter(function (node) { return linked[node.id]; }), edges: data.edges };
    var wrap = el("div", undefined, "journey-graph"), svg = svgNode("svg", { viewBox: "0 0 900 420", role: "img", "aria-labelledby": "journey-graph-title journey-graph-desc" }), title = svgNode("title", { id: "journey-graph-title" }), desc = svgNode("desc", { id: "journey-graph-desc" }); title.textContent = "Engagement relationship graph"; desc.textContent = "Nodes show recorded engagement work and arrows show only explicit relationships."; svg.append(title, desc);
    var defs = svgNode("defs"), marker = svgNode("marker", { id: "journey-arrow", markerWidth: "8", markerHeight: "8", refX: "7", refY: "4", orient: "auto" }), arrow = svgNode("path", { d: "M0,0 L8,4 L0,8 Z", fill: "currentColor" }); marker.appendChild(arrow); defs.appendChild(marker); svg.insertBefore(defs, title);
    var layers = {}, layerOf = {}; data.nodes.forEach(function (node) { layerOf[node.id] = 0; }); data.edges.forEach(function (edge) { layerOf[edge.to] = Math.max(layerOf[edge.to] || 0, (layerOf[edge.from] || 0) + 1); }); data.nodes.forEach(function (node) { (layers[layerOf[node.id]] || (layers[layerOf[node.id]] = [])).push(node); });
    var positions = {}, maxLayer = Math.max.apply(null, Object.keys(layers).map(Number)), widestLayer = Math.max.apply(null, Object.keys(layers).map(function (layer) { return layers[layer].length; })), canvasWidth = Math.max(900, 90 + (maxLayer + 1) * 360), canvasHeight = Math.max(420, 60 + widestLayer * 120); svg.setAttribute("viewBox", "0 0 " + canvasWidth + " " + canvasHeight); svg.setAttribute("width", canvasWidth); svg.setAttribute("height", canvasHeight); Object.keys(layers).forEach(function (layer) { layers[layer].forEach(function (node, index) { positions[node.id] = { x: 30 + Number(layer) * 360, y: 30 + index * 120 }; }); });
    data.edges.forEach(function (edge) { var from = positions[edge.from], to = positions[edge.to]; if (!from || !to) return; var line = svgNode("path", { d: "M" + (from.x + 320) + " " + (from.y + 38) + " C " + (from.x + 330) + " " + (from.y + 38) + ", " + (to.x - 30) + " " + (to.y + 38) + ", " + to.x + " " + (to.y + 38), class: "journey-edge-line", "marker-end": "url(#journey-arrow)" }); line.setAttribute("aria-label", edge.type + ": " + edge.from + " to " + edge.to); svg.appendChild(line); });
    data.nodes.forEach(function (node) { var point = positions[node.id], group = svgNode("g", { class: "journey-svg-node" }), rect = svgNode("rect", { x: point.x, y: point.y, width: "320", height: "76", rx: "4", tabindex: "0" }), label = svgNode("text", { x: point.x + 10, y: point.y + 23 }), kind = svgNode("text", { x: point.x + 10, y: point.y + 64, class: "journey-svg-kind" }); var words = node.label.split(" "), first = "", second = ""; words.forEach(function (word) { if ((first + " " + word).trim().length <= 36) first = (first + " " + word).trim(); else second = (second + " " + word).trim(); }); label.textContent = first; if (second) { var continuation = svgNode("tspan", { x: point.x + 10, dy: "1.1em" }); continuation.textContent = second; label.appendChild(continuation); } kind.textContent = node.kind + " · " + node.state; group.append(rect, label, kind); svg.appendChild(group); }); wrap.appendChild(svg); return wrap;
  }
  function journeyInventory(data) {
    var counts = {}, grid = el("div", undefined, "summary-grid journey-inventory");
    data.nodes.forEach(function (node) { counts[node.kind] = (counts[node.kind] || 0) + 1; });
    Object.keys(counts).sort().forEach(function (kind) { var card = el("article", undefined, "metric"); card.append(el("span", kind, "label"), el("strong", counts[kind]), el("small", "recorded items", "muted")); grid.appendChild(card); });
    return grid;
  }
  function journeyTab(selected) {
    var data = journeyData(selected), hasRelationships = data.edges.length > 0, panel = section("journey", "Journey", hasRelationships ? "recorded relationships" : "recorded data; no relationships yet"); panel.appendChild(meaning(selected, hasRelationships ? "The engagement relationship graph" : "The engagement data map")); if (hasRelationships) panel.appendChild(journeyGraph(data)); else { panel.appendChild(el("p", "No explicit relationships are recorded yet, so this view groups the existing data instead of drawing a misleading graph.", "empty muted")); panel.appendChild(journeyInventory(data)); } var alt = el("details", undefined, "text-alternative"); alt.appendChild(el("summary", "Text alternative")); var list = el("ul"); data.nodes.forEach(function (node) { list.appendChild(el("li", node.label + " (" + node.kind + ", " + node.state + ")")); }); data.edges.forEach(function (edge) { list.appendChild(el("li", edge.from + " → " + edge.to + " (" + edge.type + ")")); }); if (!data.edges.length) list.appendChild(el("li", "No explicit relationships supplied; no links inferred.")); alt.appendChild(list); panel.appendChild(alt); var placeholder = el("div", undefined, "future-action"); placeholder.append(el("strong", "Backpatch"), el("span", "Read-only · unavailable")); panel.append(placeholder, details(["Source: journey.json · legacy engagement records", "Only recorded edges are drawn."])); return panel;
  }

  function recordList(selected) { var records = []; [selected && selected.delegation, selected && selected.analysis && selected.analysis.delegation, model.delegation, model.handoffs && model.handoffs.items, model.tooling && model.tooling.items].forEach(function (value) { if (Array.isArray(value)) value.forEach(function (item) { if (item && records.indexOf(item) < 0) records.push(item); }); }); return records.filter(function (item) { return !selected || !item.branch || item.branch === selected.branch; }); }
  function field(record, keys) { for (var index = 0; index < keys.length; index += 1) if (record[keys[index]] !== undefined && record[keys[index]] !== null && record[keys[index]] !== "") return record[keys[index]]; return null; }
  function delegationTab(selected) {
    var records = recordList(selected), groups = {}; records.forEach(function (record, index) { var key = textValue(field(record, ["session_id", "session", "run_id", "handoff_id"]), "session-" + (index + 1)); (groups[key] || (groups[key] = [])).push(record); }); var panel = section("delegation", "Delegation", "generic orchestration records"); panel.appendChild(meaning(selected, "Delegation records")); var flow = el("div", undefined, "delegation-flow"), rootNode = el("article", undefined, "delegation-node coordinator"); rootNode.append(el("strong", "User / main mastermind"), el("small", "coordination root", "muted")); flow.appendChild(rootNode); var keys = Object.keys(groups); if (!keys.length) keys = ["no-records"];
    keys.forEach(function (key) { var session = el("section", undefined, "delegation-session"); session.appendChild(el("h3", key === "no-records" ? "Sub-master session" : "Sub-master · " + key)); var roles = [], workerRecords = groups[key] || []; workerRecords.forEach(function (record) { var role = field(record, ["role", "worker_role", "actor_role", "worker", "agent", "kind"]); if (role && roles.indexOf(String(role)) < 0) roles.push(String(role)); }); if (!roles.length) roles.push("workers / Karma records"); var workerList = el("ul"); roles.forEach(function (role) { workerList.appendChild(el("li", role)); }); session.append(el("p", "Workers/Karma within this session", "muted"), workerList, el("p", "Synthesized sub-master return", "delegation-return")); flow.appendChild(session); });
    panel.append(flow, el("p", records.length ? records.length + " record(s) grouped by session; role labels come from supplied fields." : "No delegation records supplied; generic session placeholder retained.", "muted"), details(["Source: handoffs · tool receipts · delegation records", "Grouping keys are read from session_id, session, run_id, or handoff_id."])); return panel;
  }
  function healthCards(selected) {
    var health = model.health || {}, tooling = model.tooling || {}, run = model.runStatus || {}, controls = model.controls || {}, analysis = selected && selected.analysis || {}, version = analysis.harness_version || {}, controlsReady = Array.isArray(controls.knobs), grid = el("div", undefined, "health-grid"); [["Dashboard", "fresh", "GET-only read model"], ["Harness", stateOf(version.state), version.value || "HARNESS_VERSION unavailable"], ["Tool / MCP", stateOf(health.state), health.state && health.state.detail], ["Controls", controlsReady ? "available" : "unavailable", controlsReady ? controls.knobs.length + " documented controls" : "optional controls API unavailable"], ["Receipts", stateOf(tooling.state), tooling.state && tooling.state.detail], ["Runner", run.state || "unknown", run.detail || "runner deferred"], ["Scope", analysis.scope ? stateOf(analysis.scope.state) : "unknown", "engagement scope"]].forEach(function (item) { var card = el("article", undefined, "health-card"); card.append(el("h3", item[0]), badge(item[1]), el("p", item[2] || "state unavailable", "muted")); grid.appendChild(card); }); return grid;
  }
  function healthTab(selected) { var panel = section("health", "Health", "observability only"); panel.appendChild(meaning(selected, "Health and compatibility signals")); panel.appendChild(healthCards(selected)); [["Backpatch", "Read-only · unavailable"], ["Push / export", "Read-only · unavailable"]].forEach(function (item) { var placeholder = el("div", undefined, "future-action"); placeholder.append(el("strong", item[0]), el("span", item[1])); panel.appendChild(placeholder); }); panel.appendChild(details(["Source: tools_mcp/doctor-report.json · /api/controls · /api/run-status", "No execution endpoint is exposed."])); return panel; }
  function settingsPage() { var panel = section("settings", "Settings", "display preferences only"); panel.append(el("p", "What this means: only local display preferences can change from this view; engagement records remain untouched."), el("p", "Theme is controlled from the navigation drawer."), details(["No write API is called by this page."])); return panel; }
  function systemHealthPage() { var panel = section("system-health", "System health", "read-only service status"); panel.appendChild(healthCards(null)); panel.appendChild(details(["Source: /api/health · /api/controls · /api/tooling · /api/run-status"])); return panel; }
  function render() {
    var records = Array.isArray(model.engagements) ? model.engagements : [], state = hashState(), selected = engagementForHash(records, window.location.hash);
    if (selected) rememberEngagement(selected.branch);
    renderEngagementTabs(selected && selected.branch);
    root.replaceChildren();
    if (state.page === "settings") { root.appendChild(settingsPage()); return; } if (state.page === "health") { root.appendChild(systemHealthPage()); return; }
    if (!selected) { root.append(el("p", "Read-only observations · generated " + textValue(model.generated_at, "time unavailable"), "read-only-banner"), overviewPanel(records, state)); return; }
    var tab = state.tab === "overview" ? overviewTab(selected) : state.tab === "workboard" ? workboardTab(selected) : state.tab === "journey" ? journeyTab(selected) : state.tab === "findings" ? findingsTab(selected) : state.tab === "evidence" ? evidenceTab(selected) : state.tab === "delegation" ? delegationTab(selected) : healthTab(selected); root.append(tabNav(selected, state.tab), tab);
  }
  function bindShell() {
    if (window.SidebarDrawer && typeof window.SidebarDrawer.createSidebarDrawer === "function") window.SidebarDrawer.createSidebarDrawer({
      container: "#app-layout", navKey: "stumblebreachCategoryNavCollapsed", onRender: function () {
        var toggle = document.getElementById("category-toggle"), panel = document.getElementById("category-panel"), open = !!toggle && toggle.getAttribute("aria-expanded") === "true";
        if (toggle) toggle.setAttribute("aria-label", open ? "Close dashboard navigation" : "Open dashboard navigation");
        if (panel) panel.setAttribute("aria-hidden", String(!open));
      }
    });
  var themeInput = document.getElementById("theme-switch-input"), normie = document.querySelector(".theme-option.normie"), hacker = document.querySelector(".theme-option.hacker"), storedTheme = localStorage.getItem("rtkTheme");
    if (themeInput) {
    themeInput.checked = storedTheme !== "normie";
    document.documentElement.dataset.theme = themeInput.checked ? "" : "normie";
      function renderTheme() {
      if (normie) normie.classList.toggle("active", !themeInput.checked);
      if (hacker) hacker.classList.toggle("active", themeInput.checked);
      }
      renderTheme();
    themeInput.addEventListener("change", function () { localStorage.setItem("rtkTheme", themeInput.checked ? "hacker" : "normie"); document.documentElement.dataset.theme = themeInput.checked ? "" : "normie"; renderTheme(); });
    }
    var pavilion = document.getElementById("pavilion-link");
    if (pavilion && window.RoutePrefix && typeof window.RoutePrefix.pavilionPath === "function") pavilion.href = window.RoutePrefix.pavilionPath() || "/";
    window.addEventListener("hashchange", render);
  }
  function load() { var keys = Object.keys(routes).filter(function (key) { return key !== "engagement" && key !== "engagements" && key !== "controls"; }); Promise.all(keys.map(function (key) { return get(routes[key]).then(function (value) { return [key, value]; }); }).concat([optional(routes.controls).then(function (value) { return ["controls", value]; })])).then(function (pairs) { pairs.forEach(function (pair) { model[pair[0]] = pair[1]; }); return get(routes.engagements); }).then(function (collection) { var summaries = collection && Array.isArray(collection.items) ? collection.items : []; return Promise.all(summaries.map(function (summary) { return summary.branch ? get(routes.engagement + encodeURIComponent(summary.branch)).then(function (detail) { return mergeEngagement(summary, detail); }).catch(function () { return summary; }) : summary; })); }).then(function (engagements) { model.engagements = engagements; render(); }).catch(function (error) { root.replaceChildren(el("p", "Dashboard data unavailable: " + error.message, "state-unknown")); }); }
  bindShell(); load();
}());
