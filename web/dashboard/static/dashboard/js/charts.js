/* Charts for the investigation console. Colours come from the CSS tokens. */
(function () {
  "use strict";

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  function data(id) {
    var el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }
  function base() {
    Chart.defaults.font.family = css("--font");
    Chart.defaults.font.size = 12;
    Chart.defaults.color = css("--ink-2");
    Chart.defaults.borderColor = css("--rule");
    Chart.defaults.plugins.legend.display = false;
    Chart.defaults.plugins.tooltip.backgroundColor = css("--ink");
    Chart.defaults.plugins.tooltip.titleColor = "#ffffff";
    Chart.defaults.plugins.tooltip.bodyColor = "#ffffff";
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 6;
    Chart.defaults.plugins.tooltip.displayColors = true;
    Chart.defaults.animation = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 450 };
    Chart.defaults.maintainAspectRatio = false;
  }
  var nf = new Intl.NumberFormat("en-IN");

  /* ------------------------------------------------------------- overview */
  function overview() {
    base();
    var c = data("chart-data");
    var high = css("--high"), med = css("--med"), rule = css("--rule"), accent = css("--accent"), warmBg = css("--warm-soft");

    var warmBand = {
      id: "warmBand",
      beforeDatasetsDraw: function (chart) {
        if (!c.warm_until) return;
        var x = chart.scales.x, y = chart.scales.y, ctx = chart.ctx;
        var right = (x.getPixelForValue(c.warm_until - 1) + x.getPixelForValue(c.warm_until)) / 2;
        ctx.save();
        ctx.fillStyle = warmBg;
        ctx.fillRect(x.left, y.top, right - x.left, y.bottom - y.top);
        ctx.fillStyle = css("--ink-3");
        ctx.font = "12px " + css("--font");
        ctx.fillText("Warm-up: building history", x.left + 8, y.top + 16);
        ctx.restore();
      }
    };

    new Chart(document.getElementById("timeline"), {
      type: "bar",
      data: {
        labels: c.labels,
        datasets: [
          { label: "High risk", data: c.high, backgroundColor: high, borderRadius: 3, stack: "a", barPercentage: 0.85, categoryPercentage: 0.9 },
          { label: "Medium risk", data: c.medium, backgroundColor: med, borderRadius: 3, stack: "a", barPercentage: 0.85, categoryPercentage: 0.9 }
        ]
      },
      options: {
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            stacked: true, grid: { display: false },
            ticks: {
              autoSkip: false, maxRotation: 0,
              callback: function (v, i) { var l = c.labels[i]; return l.slice(-5) === "00:00" ? l.slice(0, 6) : ""; }
            }
          },
          y: { stacked: true, beginAtZero: true, grid: { color: rule }, border: { display: false }, title: { display: true, text: "Alerts" }, ticks: { precision: 0 } }
        },
        plugins: {
          tooltip: {
            callbacks: {
              title: function (items) { var l = c.labels[items[0].dataIndex]; return l + " (6 hours)"; },
              footer: function (items) { return nf.format(c.payments[items[0].dataIndex]) + " payments in this block"; }
            }
          }
        }
      },
      plugins: [warmBand]
    });

    new Chart(document.getElementById("types"), {
      type: "bar",
      data: { labels: c.type_labels, datasets: [{ label: "Alerts", data: c.type_counts, backgroundColor: accent, borderRadius: 4, barPercentage: 0.55 }] },
      options: {
        indexAxis: "y",
        scales: { x: { beginAtZero: true, grid: { color: rule }, border: { display: false }, ticks: { precision: 0 } }, y: { grid: { display: false } } },
        plugins: { tooltip: { displayColors: false, callbacks: { label: function (i) { return nf.format(i.raw) + " alerts"; } } } }
      }
    });
  }

  /* ------------------------------------------------------------- payment detail */
  function payment() {
    base();
    var c = data("contrib-data");
    if (!c) return;
    var up = css("--high"), down = css("--low"), rule = css("--rule");
    new Chart(document.getElementById("contrib"), {
      type: "bar",
      data: {
        labels: c.labels,
        datasets: [{ data: c.points, backgroundColor: c.points.map(function (v) { return v >= 0 ? up : down; }), borderRadius: 3, barPercentage: 0.7 }]
      },
      options: {
        indexAxis: "y",
        scales: {
          x: { grid: { color: rule }, border: { display: false }, title: { display: true, text: "Points added to (+) or removed from (−) the score" } },
          y: { grid: { display: false }, ticks: { autoSkip: false, font: { size: 12 }, callback: function (v) { var t = this.getLabelForValue(v); return t.length > 44 ? t.slice(0, 42) + "…" : t; } }, afterFit: function (axis) { axis.width = Math.min(Math.max(axis.width, 220), 330); } }
        },
        plugins: { tooltip: { displayColors: false, callbacks: { title: function (i) { return i[0].label; }, label: function (i) { return (i.raw >= 0 ? "+" : "") + i.raw.toFixed(1) + " points"; } } } }
      }
    });
  }

  window.UPI = { overview: overview, payment: payment, css: css, data: data };
})();
