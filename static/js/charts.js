/* ==========================================================================
   Chart.js renderers for the CTI dashboard.
   Instances are created once and updated in place so refresh animates the
   data change instead of re-entering from zero.
   ========================================================================== */

const CTICharts = (() => {
  const COLORS = {
    vuln: '#22d3ee',
    malware: '#fb7185',
    research: '#a78bfa',
    taiwan: '#2dd4bf',
    global: '#60a5fa',
    p1: '#fb7185',
    p2: '#fbbf24',
    p3: '#22d3ee',
    grid: 'rgba(39, 56, 79, 0.55)',
    tick: '#8b9ab2',
    ink: '#e9eef7',
  };

  const META_KEY_COLOR = {
    VULN: COLORS.vuln,
    MALWARE: COLORS.malware,
    RESEARCH: COLORS.research,
  };

  const instances = { pie: null, comparison: null, timeline: null, priority: null };
  let defaultsApplied = false;

  const hasChart = () => typeof window.Chart !== 'undefined';

  function applyDefaults() {
    if (defaultsApplied || !hasChart()) return;
    defaultsApplied = true;
    Chart.defaults.font.family = 'Inter, "Noto Sans TC", "Microsoft JhengHei", sans-serif';
    Chart.defaults.font.size = 11;
    Chart.defaults.color = COLORS.tick;
    Chart.defaults.animation = { duration: 620, easing: 'easeOutQuart' };
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(9, 15, 25, 0.96)';
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(60, 82, 110, 0.9)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.titleColor = '#f3f7fd';
    Chart.defaults.plugins.tooltip.bodyColor = '#c3cede';
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.displayColors = false;
    Chart.defaults.plugins.tooltip.titleFont = { size: 11.5, weight: '600' };
    Chart.defaults.plugins.tooltip.bodyFont = { size: 11 };
  }

  function canvas(id) {
    return document.getElementById(id);
  }

  function destroyIfOrphan(key, element) {
    if (instances[key] && instances[key].canvas !== element) {
      instances[key].destroy();
      instances[key] = null;
    }
  }

  /* ---------------------------------------------------------------- doughnut */
  function renderPie(stats) {
    const el = canvas('clusterPieChart');
    if (!el || !hasChart()) return;

    const meta = stats.meta_categories || [];
    const labels = meta.map((m) => m.label);
    const data = meta.map((m) => m.count);
    const colors = meta.map((m) => META_KEY_COLOR[m.key] || COLORS.vuln);

    const dataset = {
      data,
      backgroundColor: colors,
      borderColor: '#0a111c',
      borderWidth: 3,
      hoverOffset: 8,
      hoverBorderColor: '#0a111c',
      spacing: 1,
    };

    destroyIfOrphan('pie', el);
    if (instances.pie) {
      instances.pie.data.labels = labels;
      instances.pie.data.datasets[0] = dataset;
      instances.pie.update();
      return;
    }

    instances.pie = new Chart(el, {
      type: 'doughnut',
      data: { labels, datasets: [dataset] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '74%',
        layout: { padding: 4 },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => labels[items[0].dataIndex],
              label: (ctx) => {
                const item = meta[ctx.dataIndex] || {};
                const share = Math.round((item.share || 0) * 1000) / 10;
                return ` ${item.count} 篇 · ${share}%（台灣 ${item.by_region?.taiwan ?? 0} / 國際 ${item.by_region?.global ?? 0}）`;
              },
            },
          },
        },
      },
    });
  }

  /* -------------------------------------------------------------- comparison */
  function renderComparison(stats) {
    const el = canvas('comparisonBarChart');
    if (!el || !hasChart()) return;

    const meta = stats.meta_categories || [];
    const labels = meta.map((m) =>
      m.key === 'VULN' ? '漏洞與修補' : m.key === 'MALWARE' ? '惡意與攻擊' : '研究與治理'
    );
    const tw = meta.map((m) => m.by_region?.taiwan ?? 0);
    const gl = meta.map((m) => m.by_region?.global ?? 0);

    destroyIfOrphan('comparison', el);
    if (instances.comparison) {
      const chart = instances.comparison;
      chart.data.labels = labels;
      chart.data.datasets[0].data = tw;
      chart.data.datasets[1].data = gl;
      chart.update();
      return;
    }

    instances.comparison = new Chart(el, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: '台灣在地',
            data: tw,
            backgroundColor: 'rgba(45, 212, 191, 0.78)',
            hoverBackgroundColor: '#2dd4bf',
            borderRadius: 5,
            borderSkipped: false,
            maxBarThickness: 46,
          },
          {
            label: '國際來源',
            data: gl,
            backgroundColor: 'rgba(96, 165, 250, 0.78)',
            hoverBackgroundColor: '#60a5fa',
            borderRadius: 5,
            borderSkipped: false,
            maxBarThickness: 46,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: (ctx) => ` ${ctx.dataset.label}：${ctx.raw} 篇` },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { color: COLORS.grid },
            ticks: { color: COLORS.tick, font: { size: 11 } },
          },
          y: {
            beginAtZero: true,
            suggestedMax: 45,
            grid: { color: COLORS.grid, drawTicks: false },
            border: { display: false },
            ticks: { color: COLORS.tick, stepSize: 10, padding: 6, font: { size: 10.5 } },
            title: {
              display: true,
              text: '文章篇數',
              color: '#61728d',
              font: { size: 10 },
              padding: { bottom: 4 },
            },
          },
        },
      },
    });
  }

  /* ---------------------------------------------------------------- timeline */
  function renderTimeline(stats) {
    const el = canvas('timelineChart');
    if (!el || !hasChart()) return;

    const points = stats.timeline || [];
    const labels = points.map((p) => p.date.slice(5).replace('-', '/'));
    const tw = points.map((p) => p.taiwan);
    const gl = points.map((p) => p.global);

    const ctx = el.getContext('2d');
    const fillTw = ctx.createLinearGradient(0, 0, 0, 210);
    fillTw.addColorStop(0, 'rgba(45, 212, 191, 0.26)');
    fillTw.addColorStop(1, 'rgba(45, 212, 191, 0)');
    const fillGl = ctx.createLinearGradient(0, 0, 0, 210);
    fillGl.addColorStop(0, 'rgba(96, 165, 250, 0.22)');
    fillGl.addColorStop(1, 'rgba(96, 165, 250, 0)');

    destroyIfOrphan('timeline', el);
    if (instances.timeline) {
      const chart = instances.timeline;
      chart.data.labels = labels;
      chart.data.datasets[0].data = tw;
      chart.data.datasets[1].data = gl;
      chart.update();
      return;
    }

    instances.timeline = new Chart(el, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: '台灣',
            data: tw,
            borderColor: COLORS.taiwan,
            backgroundColor: fillTw,
            fill: true,
            tension: 0.36,
            borderWidth: 1.8,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: COLORS.taiwan,
            pointHoverBorderColor: '#06121a',
            pointHoverBorderWidth: 2,
          },
          {
            label: '國際',
            data: gl,
            borderColor: COLORS.global,
            backgroundColor: fillGl,
            fill: true,
            tension: 0.36,
            borderWidth: 1.8,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: COLORS.global,
            pointHoverBorderColor: '#06121a',
            pointHoverBorderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => `2026/${items[0].label}`,
              label: (ctx) => ` ${ctx.dataset.label}：${ctx.raw} 篇`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { color: COLORS.grid },
            ticks: {
              color: COLORS.tick,
              maxTicksLimit: 7,
              autoSkip: true,
              font: { size: 10 },
              maxRotation: 0,
            },
          },
          y: {
            beginAtZero: true,
            suggestedMax: 3,
            grid: { color: COLORS.grid, drawTicks: false },
            border: { display: false },
            ticks: { color: COLORS.tick, stepSize: 1, padding: 6, font: { size: 10 } },
          },
        },
      },
    });
  }

  /* ---------------------------------------------------------------- priority */
  function renderPriority(stats) {
    const el = canvas('priorityChart');
    if (!el || !hasChart()) return;

    const rows = stats.priorities || [];
    const labels = rows.map((r) => r.key);
    const data = rows.map((r) => r.count);
    const colors = rows.map((r) =>
      r.key === 'P1' ? COLORS.p1 : r.key === 'P2' ? COLORS.p2 : COLORS.p3
    );

    destroyIfOrphan('priority', el);
    if (instances.priority) {
      const chart = instances.priority;
      chart.data.labels = labels;
      chart.data.datasets[0].data = data;
      chart.data.datasets[0].backgroundColor = colors.map((c) => `${c}cc`);
      chart.data.datasets[0].hoverBackgroundColor = colors;
      chart.update();
      return;
    }

    instances.priority = new Chart(el, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: '情資數量',
            data,
            backgroundColor: colors.map((c) => `${c}cc`),
            hoverBackgroundColor: colors,
            borderRadius: 6,
            borderSkipped: false,
            maxBarThickness: 58,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 8 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => {
                const row = rows[items[0].dataIndex] || {};
                return row.label || items[0].label;
              },
              label: (ctx) => {
                const row = rows[ctx.dataIndex] || {};
                return ` ${row.count} 篇 · 佔 ${Math.round((row.share || 0) * 100)}%`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { color: COLORS.grid },
            ticks: {
              color: COLORS.ink,
              font: { family: '"JetBrains Mono", monospace', size: 11, weight: '600' },
            },
          },
          y: {
            beginAtZero: true,
            grid: { color: COLORS.grid, drawTicks: false },
            border: { display: false },
            ticks: { color: COLORS.tick, padding: 6, font: { size: 10 } },
          },
        },
      },
    });
  }

  function renderStats(stats) {
    applyDefaults();
    if (!hasChart()) {
      document.querySelectorAll('.chart-frame canvas').forEach((node) => {
        node.replaceWith(
          Object.assign(document.createElement('div'), {
            className: 'empty h-full',
            textContent: 'Chart.js 未載入，請檢查網路連線。',
          })
        );
      });
      return;
    }
    renderPie(stats);
    renderComparison(stats);
    renderTimeline(stats);
    renderPriority(stats);
  }

  return { renderStats, COLORS, META_KEY_COLOR };
})();
