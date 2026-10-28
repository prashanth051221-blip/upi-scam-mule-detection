/* Mule-ring views: money-flow (Sankey, Chart.js plugin) and network (vis-network). */
(function () {
  "use strict";
  var src = document.getElementById("graph-data");
  if (!src) return;
  var g = JSON.parse(src.textContent);
  function css(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  var nf = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
  function rupee(v) { return "₹" + nf.format(v); }
  function short(id) {
    var at = id.indexOf("@");
    var name = at > 0 ? id.slice(0, at) : id;
    return name.length > 16 ? name.slice(0, 15) + "…" : name;
  }

  var role = {}, level = {};
  g.nodes.forEach(function (n) { role[n.id] = n.role; level[n.id] = n.level; });
  var colour = {
    source: { fill: css("--accent"), soft: css("--accent-soft") },
    mule: { fill: css("--med"), soft: css("--med-soft") },
    cashout: { fill: css("--high"), soft: css("--high-soft") }
  };
  var ink = css("--ink"), font = css("--font"), mono = css("--mono");

  /* ---------------------------------------------------------- money-flow (Sankey) */
  var sankeyDone = false;
  function drawSankey() {
    if (sankeyDone || typeof Chart === "undefined") return;
    sankeyDone = true;
    // A Sankey needs money to move strictly forward. Flows that go "backwards"
    // (rare loops between mules) are left out here and listed in the note.
    var forward = [], hidden = 0, MAX_FLOWS = 60;
    g.edges.forEach(function (e) {
      if (level[e.to] > level[e.from]) forward.push({ from: e.from, to: e.to, flow: e.amount });
      else hidden += 1;
    });
    var trimmed = 0;
    if (forward.length > MAX_FLOWS) {
      forward.sort(function (a, b) { return b.flow - a.flow; });
      trimmed = forward.length - MAX_FLOWS;
      forward = forward.slice(0, MAX_FLOWS);
    }
    var used = {};
    forward.forEach(function (f) { used[f.from] = true; used[f.to] = true; });
    var columns = {}, labels = {};
    g.nodes.forEach(function (n) { if (used[n.id]) { columns[n.id] = n.level; labels[n.id] = short(n.id); } });
    var box = document.getElementById("flow-view");
    var perColumn = {};
    g.nodes.forEach(function (n) { if (used[n.id]) perColumn[n.level] = (perColumn[n.level] || 0) + 1; });
    var tallest = Math.max.apply(null, Object.keys(perColumn).map(function (k) { return perColumn[k]; }));
    box.style.height = Math.max(460, Math.min(1600, tallest * 30 + 80)) + "px";

    new Chart(document.getElementById("ring-sankey"), {
      type: "sankey",
      data: {
        datasets: [{
          data: forward,
          labels: labels,
          column: columns,
          colorFrom: function (c) { var r = role[c.dataset.data[c.dataIndex].from]; return colour[r].fill; },
          colorTo: function (c) { var r = role[c.dataset.data[c.dataIndex].to]; return colour[r].fill; },
          colorMode: "gradient",
          alpha: 0.35,
          borderWidth: 0,
          nodeWidth: 12,
          nodePadding: 14,
          size: "max",
          color: ink,
          font: { family: mono, size: 11 }
        }]
      },
      options: {
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: ink, padding: 10, displayColors: false,
            callbacks: {
              title: function () { return ""; },
              label: function (c) {
                var d = c.dataset.data[c.dataIndex];
                return d.from + "  →  " + d.to + ":  " + rupee(d.flow);
              }
            }
          }
        }
      }
    });
    var note = document.getElementById("flow-note"), parts = [];
    if (trimmed > 0) parts.push("Large ring: showing the " + MAX_FLOWS + " biggest money flows; " + trimmed + " smaller flows are in the Network view and the payment list below.");
    if (hidden > 0) parts.push(hidden + " backward flow" + (hidden > 1 ? "s" : "") + " between mules " + (hidden > 1 ? "are" : "is") + " shown only in the Network view.");
    if (parts.length) { note.textContent = parts.join(" "); note.classList.remove("hidden"); }
  }

  /* ---------------------------------------------------------- network (vis-network) */
  var network = null, nodes = null, edges = null, labelsOn = false, focusId = null;
  function nodeStyle(n, dim) {
    var c = colour[n.role];
    return {
      id: n.id, label: short(n.id), level: n.level, shape: "box",
      margin: { top: 6, bottom: 6, left: 9, right: 9 }, borderWidth: 1.5,
      color: { background: dim ? "#f4f6fa" : c.soft, border: dim ? "#dfe5ef" : c.fill,
               highlight: { background: c.soft, border: ink }, hover: { background: c.soft, border: ink } },
      font: { face: mono, size: 12, color: dim ? "#b5bfd0" : ink },
      title: n.id + "\nReceived: " + rupee(n.inflow) + "\nSent on: " + rupee(n.outflow)
    };
  }
  function edgeStyle(e, i, dim) {
    return {
      id: i, from: e.from, to: e.to,
      arrows: { to: { enabled: true, scaleFactor: 0.55 } },
      dashes: !e.alerted,
      width: dim ? 1 : Math.max(1.2, Math.min(5, Math.log10(e.amount + 1) - 2.2)),
      color: { color: dim ? "#e3e8f1" : (e.alerted ? css("--ink-2") : css("--ink-3")), highlight: css("--accent"), hover: css("--accent") },
      label: labelsOn && !dim ? rupee(e.amount) : undefined,
      font: { face: font, size: 10, color: css("--ink-2"), strokeWidth: 3, strokeColor: "#ffffff", align: "top" },
      title: e.from + " → " + e.to + "\n" + rupee(e.amount) + " in " + e.count + " payment" + (e.count > 1 ? "s" : "")
    };
  }
  function pathOf(id) {
    // every account money can reach from `id`, and every account that fed money into it
    var keep = {}; keep[id] = true;
    var changed = true;
    var down = {}, up = {}; down[id] = true; up[id] = true;
    while (changed) {
      changed = false;
      g.edges.forEach(function (e) {
        if (down[e.from] && !down[e.to]) { down[e.to] = true; changed = true; }
        if (up[e.to] && !up[e.from]) { up[e.from] = true; changed = true; }
      });
    }
    Object.keys(down).forEach(function (k) { keep[k] = true; });
    Object.keys(up).forEach(function (k) { keep[k] = true; });
    return keep;
  }
  function restyle() {
    var keep = focusId ? pathOf(focusId) : null;
    nodes.update(g.nodes.map(function (n) { return nodeStyle(n, keep && !keep[n.id]); }));
    edges.update(g.edges.map(function (e, i) { return edgeStyle(e, i, keep && !(keep[e.from] && keep[e.to])); }));
  }
  function drawNetwork() {
    if (network || typeof vis === "undefined") return;
    var el = document.getElementById("ring-graph");
    nodes = new vis.DataSet(g.nodes.map(function (n) { return nodeStyle(n, false); }));
    edges = new vis.DataSet(g.edges.map(function (e, i) { return edgeStyle(e, i, false); }));
    network = new vis.Network(el, { nodes: nodes, edges: edges }, {
      layout: { hierarchical: { enabled: true, direction: "LR", sortMethod: "directed", levelSeparation: 230, nodeSpacing: 38, treeSpacing: 40, blockShifting: true, edgeMinimization: true } },
      physics: false,
      interaction: { hover: true, tooltipDelay: 100, keyboard: true, zoomView: true, dragView: true },
      edges: { smooth: { type: "cubicBezier", forceDirection: "horizontal", roundness: 0.45 } }
    });
    network.once("afterDrawing", function () { network.fit({ animation: false }); });
    network.on("click", function (p) {
      focusId = p.nodes.length ? p.nodes[0] : null;
      restyle();
    });
  }

  /* ---------------------------------------------------------- toggle */
  var buttons = document.querySelectorAll(".view-toggle button");
  var flowView = document.getElementById("flow-view"), netView = document.getElementById("ring-graph");
  var hint = document.getElementById("view-hint"), legendNet = document.getElementById("legend-net");
  var bLabels = document.getElementById("net-labels"), bReset = document.getElementById("net-reset");
  function show(view) {
    buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.view === view)); });
    var net = view === "network";
    flowView.classList.toggle("hidden", net);
    netView.classList.toggle("hidden", !net);
    bLabels.classList.toggle("hidden", !net);
    bReset.classList.toggle("hidden", !net);
    legendNet.classList.toggle("hidden", !net);
    hint.textContent = net
      ? "Click an account to highlight only the money that passed through it. Scroll to zoom, drag to move."
      : "Money moves left to right. Band thickness shows rupees. Hover a band for the amount.";
    if (net) hint.textContent = "Click an account to highlight its money path.";
    if (net) { drawNetwork(); setTimeout(function () { network && network.fit({ animation: false }); }, 30); }
    else drawSankey();
    try { localStorage.setItem("ringView", view); } catch (e) { /* storage unavailable */ }
  }
  buttons.forEach(function (b) { b.addEventListener("click", function () { show(b.dataset.view); }); });
  bLabels.addEventListener("click", function () {
    labelsOn = !labelsOn;
    bLabels.textContent = labelsOn ? "Hide amounts" : "Show amounts";
    restyle();
  });
  bReset.addEventListener("click", function () { focusId = null; restyle(); network.fit({ animation: true }); });

  var start = "flow";
  try { start = localStorage.getItem("ringView") || "flow"; } catch (e) { /* ignore */ }
  show(start === "network" ? "network" : "flow");
})();
