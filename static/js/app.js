/* ==========================================================================
   CTI Risk Decision Radar — dashboard controller.
   Plain ES2020, no build step: fetch → render, with small state machine and
   interruptible UI updates (abortable requests, debounced search).
   ========================================================================== */

(() => {
  'use strict';

  const API = '/api/v1';
  const PAGE_SIZE = 25;

  const PRIORITY_TONE = { P1: '#fb7185', P2: '#fbbf24', P3: '#22d3ee' };
  const LEVEL_TONE = { CRITICAL: 'critical', HIGH: 'high', MEDIUM: 'medium', LOW: 'low' };

  const state = {
    stats: null,
    filters: { priority: '', region: '', category: '', q: '', sort: 'risk' },
    page: 0,
    total: 0,
    matrixSelection: '',
    openRowId: null,
    feedItems: [],
    form: { controls: new Set(), sensitivity: 'medium' },
    feedAbort: null,
    busy: false,
  };

  /* ---------------------------------------------------------------- helpers */

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const esc = (value) =>
    String(value ?? '').replace(/[&<>"']/g, (ch) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
    ));

  const nf = new Intl.NumberFormat('zh-TW');
  const num = (value) => nf.format(Number(value) || 0);

  const pct = (share) => `${Math.round((Number(share) || 0) * 1000) / 10}%`;

  const shortDate = (iso) => (iso ? String(iso).slice(5).replace('-', '/') : '—');

  const debounce = (fn, wait = 260) => {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), wait);
    };
  };

  function toast(message, kind = 'info') {
    const stack = $('#toastStack');
    if (!stack) return;
    const node = document.createElement('div');
    node.className = 'toast';
    node.dataset.kind = kind;
    node.dataset.state = 'enter';
    node.innerHTML = `
      <svg class="ico ico-sm mt-0.5 shrink-0" style="color:${
        kind === 'error' ? '#fb7185' : kind === 'success' ? '#34d399' : '#22d3ee'
      }"><use href="#${kind === 'error' ? 'i-alert' : kind === 'success' ? 'i-check' : 'i-pulse'}" /></svg>
      <span>${esc(message)}</span>`;
    stack.appendChild(node);

    requestAnimationFrame(() => {
      node.dataset.state = 'enter';
      requestAnimationFrame(() => {
        node.dataset.state = '';
      });
    });

    setTimeout(() => {
      node.dataset.state = 'leave';
      setTimeout(() => node.remove(), 260);
    }, 4200);
  }

  async function api(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
      ...options,
    });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const body = await response.json();
        if (typeof body.detail === 'string') detail = body.detail;
        else if (Array.isArray(body.detail) && body.detail[0]?.msg) detail = body.detail[0].msg;
      } catch {
        /* keep the status code */
      }
      throw new Error(detail);
    }
    return response.json();
  }

  /* -------------------------------------------------------------- dashboard */

  async function loadStats({ silent = false } = {}) {
    try {
      const stats = await api('/stats');
      state.stats = stats;
      renderKpis(stats);
      renderMetaLegend(stats);
      renderClusterStrip(stats);
      renderComparisonInsight(stats);
      renderDatasetNote(stats);
      renderTimelineRange(stats);
      renderMatrix(stats.matrix || []);
      renderInsights(stats.insights || []);
      renderChipCounts(stats.priorities || []);
      CTICharts.renderStats(stats);
      setApiStatus(true);
      if (!silent) return stats;
      return stats;
    } catch (error) {
      setApiStatus(false);
      if (!silent) toast(`無法取得情資統計：${error.message}`, 'error');
      throw error;
    }
  }

  function setApiStatus(online) {
    const node = $('#apiStatus');
    if (!node) return;
    node.textContent = online ? 'API 已連線' : 'API 離線';
    const pill = node.closest('span');
    if (pill) {
      pill.classList.toggle('border-emerald-500/25', online);
      pill.classList.toggle('bg-emerald-500/10', online);
      pill.classList.toggle('text-emerald-300', online);
      pill.classList.toggle('border-rose-500/30', !online);
      pill.classList.toggle('bg-rose-500/10', !online);
      pill.classList.toggle('text-rose-300', !online);
    }
  }

  function sparkline(values, tint = 'rgba(34,211,238,0.85)') {
    const max = Math.max(...values, 1);
    return values
      .map((value, index) => {
        const height = Math.max(8, Math.round((value / max) * 100));
        return `<span style="height:${height}%;background:linear-gradient(180deg,${tint},rgba(34,211,238,0.08));animation-delay:${index * 22}ms"></span>`;
      })
      .join('');
  }

  function renderKpis(stats) {
    const totals = stats.totals || {};
    // The corpus still holds 100 rows; only 85 of them are threats, so the
    // headline number is the corpus and the P1 share is computed against the
    // threat subset.
    const corpus = totals.corpus ?? totals.threats ?? 0;
    $('#kpiTotal').textContent = num(corpus);
    const kpiFoot = $('#kpiTotal') && $('#kpiTotal').closest('.kpi') && $('#kpiTotal').closest('.kpi').querySelector('.kpi-foot');
    if (kpiFoot && totals.duplicates && !kpiFoot.querySelector('[data-dup]')) {
      const note = document.createElement('span');
      note.dataset.dup = '1';
      note.className = 'mono text-[10px] text-[color:var(--faint)]';
      note.textContent = '重複 ' + totals.duplicates + ' 已合併';
      kpiFoot.appendChild(note);
    }
    const sampleNote = $('#sampleNote');
    if (sampleNote && totals.balanced_rows && totals.natural_p1_share != null) {
      sampleNote.textContent =
        '本頁含 ' + num(totals.balanced_rows) + ' 筆平衡對照樣本，故 P1 佔比略高於自然語料的 '
        + (totals.natural_p1_share * 100).toFixed(1) + '%（自然語料平均 '
        + totals.natural_avg_score + ' 分）';
    }
    $('#kpiTw').textContent = num(totals.taiwan);
    $('#kpiGlobal').textContent = num(totals.global);
    $('#heroCorpus').innerHTML = `${num(corpus)}<span class="ml-1 text-[11px] text-[color:var(--faint)]">篇</span>`;

    $('#kpiP1').textContent = num(totals.p1);
    $('#kpiP1Share').textContent = totals.threats ? pct(totals.p1 / totals.threats) : '0%';

    const meta = [...(stats.meta_categories || [])].sort((a, b) => b.count - a.count);
    const top = meta[0];
    if (top) {
      $('#kpiTopMeta').textContent = top.label;
      $('#kpiTopMetaShare').textContent = `${num(top.count)} 篇 · ${pct(top.share)}`;
      $('#kpiTopMetaNote').textContent = '台灣 ' + num(top.by_region?.taiwan ?? 0) + ' / 國際 ' + num(top.by_region?.global ?? 0);
    }
    const bar = $('#kpiMetaBar');
    if (bar && meta.length) {
      bar.innerHTML = meta
        .map(
          (item) =>
            `<span style="flex:${item.count};background:${CTICharts.META_KEY_COLOR[item.key] || '#22d3ee'};opacity:.9"></span>`
        )
        .join('');
    }

    $('#kpiAvgScore').textContent = (Math.round((totals.avg_score || 0) * 10) / 10).toFixed(1);
    $('#kpiCritical').textContent = `${num(totals.critical)} 筆`;
    const avgBar = $('#kpiAvgBar');
    if (avgBar) avgBar.style.width = `${Math.min(100, totals.avg_score || 0)}%`;

    const timeline = stats.timeline || [];
    const daily = timeline.slice(-12).map((point) => point.total);
    const spark = $('#kpiSpark');
    if (spark) spark.innerHTML = sparkline(daily);
    const p1Spark = $('#kpiP1Spark');
    if (p1Spark) {
      p1Spark.innerHTML = sparkline(
        (stats.priorities || []).map((row) => row.count),
        'rgba(251,113,133,0.9)'
      );
    }
  }

  function renderMetaLegend(stats) {
    const meta = stats.meta_categories || [];
    $('#pieCenterTotal').textContent = num(stats.totals?.corpus ?? stats.totals?.threats);

    const badge = $('#metaSourceBadge');
    if (badge) {
      badge.textContent = '逐篇分類 · 4 類';
    }

    $('#metaLegend').innerHTML = meta
      .map((item) => {
        const color = CTICharts.META_KEY_COLOR[item.key] || '#22d3ee';
        return `
        <div class="legend-row">
          <div class="legend-label">
            <span class="legend-swatch" style="background:${color}"></span>
            <span title="${esc(item.label_en)}">${esc(item.label)}</span>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span class="mono text-[10px] text-[color:var(--faint)]">台 ${num(item.by_region?.taiwan ?? 0)} / 國 ${num(item.by_region?.global ?? 0)}</span>
            <span class="mono text-[11.5px] font-semibold" style="color:${color}">${num(item.count)}</span>
            <span class="mono text-[10px] text-[color:var(--faint)] w-10 text-right">${pct(item.share)}</span>
          </div>
        </div>`;
      })
      .join('');
  }

  function renderClusterStrip(stats) {
    const strip = $('#categoryStrip');
    if (!strip) return;

    // The cluster count is chosen per region, so the caption is derived from
    // the data instead of assuming C0/C1/C2.
    const caption = $('#clusterCaption');
    if (caption) {
      const ids = [...new Set((stats.clusters || []).map((row) => String(row.cluster)))].sort();
      caption.textContent = ids.length ? `叢集明細（${ids.map((id) => `C${id}`).join(' / ')}）` : '叢集明細';
    }

    const groups = { taiwan: [], global: [] };
    for (const row of stats.clusters || []) {
      (groups[row.region] ||= []).push(row);
    }

    strip.innerHTML = [
      ['taiwan', '台灣'],
      ['global', '國際'],
    ]
      .map(([key, label]) => {
        const items = (groups[key] || [])
          .sort((a, b) => Number(a.cluster) - Number(b.cluster))
          .map((row) => {
            const color = CTICharts.META_KEY_COLOR[row.category] || '#22d3ee';
            const split = Object.entries(row.breakdown || {})
              .map(([key, value]) => `${key} ${value}`)
              .join(' / ');
            return `<span class="tally" title="${esc(row.category_label)}｜${num(row.count)} 篇${
              split ? `（${esc(split)}）` : ''
            }">
              <span class="legend-swatch" style="background:${color}"></span>
              C${esc(row.cluster)}<b>${num(row.count)}</b>
            </span>`;
          })
          .join('');
        return `<span class="mono mr-1 text-[10px] text-[color:var(--faint)]">${label}</span>${items}`;
      })
      .join('');
  }

  function renderComparisonInsight(stats) {
    // Read the same series the bars draw: the displayed Meta-Category values.
    const meta = stats.meta_categories || [];
    const cats = stats.categories || [];
    const rank = (region) =>
      [...meta].sort((a, b) => (b.by_region?.[region] ?? 0) - (a.by_region?.[region] ?? 0));
    const twTop = rank('taiwan')[0];
    const glTop = rank('global')[0];
    const supply = cats.find((item) => item.key === 'SupplyChain');

    if (!twTop || !glTop) return;

    const modeNote = '（逐篇分類）';
    const pieces = [
      `台灣以「${twTop.label}」（${num(twTop.by_region?.taiwan ?? 0)} 篇）為最大宗`,
      `國際則以「${glTop.label}」（${num(glTop.by_region?.global ?? 0)} 篇）為主`,
    ];
    if (supply) {
      pieces.push(
        `供應鏈議題在語料標記中台灣 ${num(supply.by_region?.taiwan ?? 0)} 篇、國際 ${num(
          supply.by_region?.global ?? 0
        )} 篇`
      );
    }
    $('#comparisonInsight').textContent = `${modeNote}${pieces.join('；')}。兩地關注焦點的時間差，即是 CISO 提前部署修補與監控的決策窗口。`;
  }

  function renderDatasetNote(stats) {
    const node = $('#baselineNote');
    if (!node) return;

    const info = stats.dataset || {};
    const files = (info.sources || [])
      .map((source) => String(source).split(/[\\/]/).pop())
      .join('、');
    const rows = info.rows || {};
    const sources = info.date_sources || {};
    const verified = (sources['thehackernews.com'] || 0) + (sources['twcert.org.tw'] || 0) + (sources['ithome.com.tw'] || 0);
    const estimated = sources.estimated || 0;
    const dateNote =
      info.date_policy === 'column'
        ? `時間軸為來源實際發布日期（已驗證 ${num(verified)} 筆${estimated ? `，推估 ${num(estimated)} 筆` : ''}）`
        : '原始 CSV 未含發布日期，時間軸依擷取順序回推';

    const accuracy = info.validation?.accuracy;
    const classified = Object.entries(info.classification || {})
      .map(([key, value]) => `${key} ${num(value)}`)
      .join(' / ');
    const labelNote = accuracy
      ? `逐篇規則分類（${classified}；對 ${num(info.validation?.n ?? 0)} 筆人工標註準確率 ${Math.round(accuracy * 100)}%）`
      : '逐篇規則分類（services/classify.py）';

    node.textContent = `資料來源：${files || '—'}（匯出 ${esc(info.exported_at || '—')}，台灣 ${
      num(rows.taiwan ?? 0)
    } 筆 / 國際 ${num(rows.global ?? 0)} 筆）｜${labelNote}｜${dateNote}`;
  }

  function renderTimelineRange(stats) {
    const node = $('#timelineRange');
    if (!node) return;
    const monthly = stats.timeline_monthly && stats.timeline_monthly.length
      ? stats.timeline_monthly
      : null;
    const points = monthly || stats.timeline || [];
    if (!points.length) {
      node.textContent = '—';
      return;
    }
    // The label must describe the rows that were actually loaded, never a
    // hard-coded window that can drift away from the CSV snapshot.
    const first = points[0].date;
    const last = points[points.length - 1].date;
    node.textContent = monthly
      ? `${first} → ${last}（${points.length} 個月）`
      : `${first} → ${last}（${points.length} 個日期）`;
  }

  function renderChipCounts(priorities) {
    const map = Object.fromEntries(priorities.map((row) => [row.key, row.count]));
    const total = priorities.reduce((sum, row) => sum + row.count, 0);
    if ($('#cntAll')) $('#cntAll').textContent = num(total);
    if ($('#cntP1')) $('#cntP1').textContent = num(map.P1 || 0);
    if ($('#cntP2')) $('#cntP2').textContent = num(map.P2 || 0);
    if ($('#cntP3')) $('#cntP3').textContent = num(map.P3 || 0);
  }

  function stepsHtml(plan) {
    if (!plan || !plan.length) return '<p class="text-[11.5px] text-[color:var(--faint)]">尚無處置建議。</p>';
    return plan
      .map(
        (step) => `
      <li class="step">
        <div class="min-w-0">
          <div class="step-title">${esc(step.title)}</div>
          <div class="step-meta">
            <span><svg class="ico ico-sm inline -mt-0.5 mr-1"><use href="#i-user" /></svg>${esc(step.owner)}</span>
            <span><svg class="ico ico-sm inline -mt-0.5 mr-1"><use href="#i-clock" /></svg>${esc(step.sla_hours)}h</span>
          </div>
          <p class="step-detail">${esc(step.detail)}</p>
        </div>
      </li>`
      )
      .join('');
  }

  /* ----------------------------------------------------------------- matrix */

  function renderMatrix(rows) {
    const grid = $('#matrixGrid');
    if (!grid) return;

    grid.innerHTML = rows
      .map((row, index) => {
        const tone = row.tone || 'monitor';
        const accent = PRIORITY_TONE[row.priority] || '#22d3ee';
        const total = rows.reduce((sum, item) => sum + item.count, 0) || 1;
        const share = Math.round((row.count / total) * 100);
        return `
        <article class="matrix-card" style="--accent:${accent}" data-priority="${esc(row.priority)}" data-active="false">
          <button type="button" class="matrix-select block w-full p-4 text-left" data-matrix-select="${esc(row.priority)}">
            <div class="flex items-start justify-between gap-2">
              <span class="badge badge-${esc(row.priority.toLowerCase())}">
                <span class="dot"></span>${esc(row.priority)} · ${esc(row.label.replace(/^P\d\s*/, ''))}
              </span>
              <span class="mono text-2xl font-semibold leading-none" style="color:${accent}">${num(row.count)}</span>
            </div>
            <p class="mt-2.5 text-[12.5px] font-medium leading-snug text-white">${esc(row.headline)}</p>
            <div class="mt-2 h-1 overflow-hidden rounded-full bg-white/5">
              <div class="h-full rounded-full" style="width:${share}%;background:${accent}"></div>
            </div>
            <div class="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-[color:var(--faint)]">
              <span class="mono">SLA ${esc(row.sla_hours)}h</span>
              <span class="mono">台 ${num(row.taiwan)} / 國 ${num(row.global)}</span>
              <span class="mono">均分 ${esc(row.avg_score)}</span>
            </div>
            <p class="mt-2 line-clamp-2 text-[11px] leading-relaxed text-[color:var(--muted)]">${esc(row.criteria)}</p>
          </button>
          <button type="button" class="matrix-toggle" aria-expanded="false" aria-controls="matrix-plan-${esc(row.priority)}" data-matrix-toggle="${esc(row.priority)}">
            <span class="flex items-center gap-1.5"><svg class="ico ico-sm text-[color:var(--muted)]"><use href="#i-list" /></svg>處置建議（${row.action_plan?.length || 0} 步）</span>
            <svg class="ico ico-sm chev"><use href="#i-chevron" /></svg>
          </button>
          <div class="accordion" id="matrix-plan-${esc(row.priority)}" data-open="false" data-branch="${tone}">
            <div>
              <ol class="steps px-3 pb-3">${stepsHtml(row.action_plan)}</ol>
            </div>
          </div>
        </article>`;
      })
      .join('');

    grid.querySelectorAll('[data-matrix-select]').forEach((button) => {
      button.addEventListener('click', () => selectMatrixLane(button.dataset.matrixSelect));
    });
    grid.querySelectorAll('[data-matrix-toggle]').forEach((button) => {
      button.addEventListener('click', () => toggleAccordion(button));
    });
    syncMatrixSelection();
  }

  function toggleAccordion(button) {
    const panel = document.getElementById(button.getAttribute('aria-controls'));
    if (!panel) return;
    const open = button.getAttribute('aria-expanded') === 'true';
    button.setAttribute('aria-expanded', String(!open));
    panel.dataset.open = String(!open);
  }

  function selectMatrixLane(priority) {
    state.matrixSelection = state.matrixSelection === priority ? '' : priority;
    state.filters.priority = state.matrixSelection;
    state.page = 0;
    syncMatrixSelection();
    renderPriorityChips();
    loadThreats();
    if (state.matrixSelection) {
      $('#feed')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function syncMatrixSelection() {
    $$('[data-priority][data-active]').forEach((card) => {
      const active = !!state.matrixSelection && card.dataset.priority === state.matrixSelection;
      card.dataset.active = String(active);
    });
    const clearBtn = $('#clearMatrixBtn');
    if (clearBtn) clearBtn.hidden = !state.matrixSelection;
    const hint = $('#matrixHint');
    if (hint) {
      hint.textContent = state.matrixSelection
        ? `已篩選 ${state.matrixSelection} 情資`
        : '依風險分數自動分派';
    }
    $$('[data-priority][data-active]').forEach((card) => {
      if (card.dataset.priority === state.matrixSelection) {
        card.querySelector('.matrix-toggle')?.setAttribute('aria-expanded', 'true');
        const panel = card.querySelector('.accordion');
        if (panel) panel.dataset.open = 'true';
      }
    });
  }

  function renderInsights(insights) {
    const grid = $('#insightGrid');
    if (!grid) return;
    const icons = ['i-pulse', 'i-flow', 'i-layers', 'i-target'];
    grid.innerHTML = insights
      .slice(0, 4)
      .map(
        (text, index) => `
      <article class="panel panel-hover p-4">
        <div class="flex items-center gap-2">
          <span class="icon-chip h-7 w-7 rounded-lg"><svg class="ico ico-sm"><use href="#${icons[index % icons.length]}" /></svg></span>
          <span class="kicker">Insight ${String(index + 1).padStart(2, '0')}</span>
        </div>
        <p class="mt-2.5 text-[11.5px] leading-relaxed text-[color:var(--muted)]">${esc(text)}</p>
      </article>`
      )
      .join('');
  }

  /* ------------------------------------------------------------------- feed */

  function renderPriorityChips() {
    $$('[data-priority]').forEach((chip) => {
      if (!chip.classList.contains('chip')) return;
      chip.setAttribute('aria-pressed', String((chip.dataset.priority || '') === (state.filters.priority || '')));
    });
    $$('[data-region]').forEach((chip) => {
      if (!chip.classList.contains('chip')) return;
      chip.setAttribute('aria-pressed', String((chip.dataset.region || '') === (state.filters.region || '')));
    });
  }

  function buildFeedQuery() {
    const params = new URLSearchParams();
    const { priority, region, category, q, sort } = state.filters;
    if (priority) params.set('priority', priority);
    if (region) params.set('region', region);
    if (category) params.set('category', category);
    if (q) params.set('q', q);
    if (sort) params.set('sort', sort);
    params.set('limit', String(PAGE_SIZE));
    params.set('offset', String(state.page * PAGE_SIZE));
    return params.toString();
  }

  function validateForm() {
    const cveInput = $('#cveId');
    const value = cveInput.value.trim();
    const valid = !value || /^CVE-\d{4}-\d{4,7}$/i.test(value);
    cveInput.setAttribute('aria-invalid', String(!valid));
    $('#cveError').classList.toggle('hidden', valid);
    return valid;
  }

  async function loadThreats() {
    state.feedAbort?.abort();
    state.feedAbort = new AbortController();
    renderFeedLoading();

    try {
      const data = await api(`/threats?${buildFeedQuery()}`, { signal: state.feedAbort.signal });
      state.total = data.total;
      renderFeed(data.items || []);
      renderPagination();
    } catch (error) {
      if (error.name === 'AbortError') return;
      $('#feedBody').innerHTML = `
        <tr><td colspan="6" class="py-8 text-center text-[color:var(--faint)]">
          無法載入情資：${esc(error.message)}
        </td></tr>`;
      toast(`情資列表載入失敗：${error.message}`, 'error');
    }
  }

  function renderFeedLoading() {
    $('#feedBody').innerHTML = Array.from({ length: 6 })
      .map(
        () => `<tr>
          <td class="py-3"><div class="skeleton h-3.5 w-14"></div></td>
          <td class="py-3"><div class="skeleton h-3.5 w-3/4"></div></td>
          <td class="py-3"><div class="skeleton h-3.5 w-24"></div></td>
          <td class="py-3"><div class="skeleton h-3.5 w-10"></div></td>
          <td class="py-3"><div class="skeleton h-3.5 w-10"></div></td>
          <td class="py-3"><div class="skeleton h-3.5 w-16"></div></td>
        </tr>`
      )
      .join('');
    $('#feedCount').textContent = '—';
    $('#feedTotal').textContent = '—';
  }

  function detailRowHtml(item) {
    return `<tr class="feed-detail-row"><td colspan="6">
              <div class="feed-detail-grid">
                <div>
                  <div class="kicker mb-2">${item.priority ? `Recommended Playbook · ${esc(item.priority)}` : '產業動態 · 不進入處置流程'}</div>
                  <ol class="steps">${stepsHtml(item.action_plan)}</ol>
                  ${item.action_plan?.length ? '' : '<p class="text-[11.5px] text-[color:var(--faint)]">此篇為產品／財報類消息，經分類後排除於 P1–P3 與平均分數之外。</p>'}
                </div>
                <div class="rounded-xl border border-[#1b2739] bg-[#08101b]/70 p-3">
                  <div class="kicker mb-2">Signal</div>
                  <dl class="space-y-1.5 text-[11px]">
                    <div class="flex justify-between gap-3"><dt class="text-[color:var(--faint)]">來源</dt><dd class="mono text-[color:var(--ink-soft)]">${esc(item.source)}</dd></div>
                    <div class="flex justify-between gap-3"><dt class="text-[color:var(--faint)]">地區</dt><dd class="mono text-[color:var(--ink-soft)]">${item.region === 'taiwan' ? '台灣在地' : '國際來源'}</dd></div>
                    <div class="flex justify-between gap-3"><dt class="text-[color:var(--faint)]">類別</dt><dd class="text-right text-[color:var(--ink-soft)]">${esc(item.category_label)}</dd></div>
                    <div class="flex justify-between gap-3"><dt class="text-[color:var(--faint)]">Meta-Category</dt><dd class="text-right text-[color:var(--ink-soft)]">${esc(item.meta_label)}</dd></div>
                    <div class="flex justify-between gap-3"><dt class="text-[color:var(--faint)]">風險分數</dt><dd class="mono text-[color:var(--ink-soft)]">${esc(item.risk_score)}</dd></div>
                    <div class="flex justify-between gap-3"><dt class="text-[color:var(--faint)]">發布日期</dt><dd class="mono text-[color:var(--ink-soft)]">${esc(item.published_at)}</dd></div>
                    <div class="flex justify-between gap-3"><dt class="text-[color:var(--faint)]">原始報導</dt><dd class="text-right">${
                      item.source_url
                        ? `<a class="feed-link" href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">開啟來源 ↗</a>`
                        : '—'
                    }</dd></div>
                    <div class="flex justify-between gap-3"><dt class="text-[color:var(--faint)]">事件 ID</dt><dd class="mono text-[color:var(--ink-soft)]">#${esc(item.id)}</dd></div>
                  </dl>
                </div>
              </div>
            </td></tr>`;
  }

  function feedRowHtml(item) {
    const metaColor = CTICharts.META_KEY_COLOR[item.meta_category] || '#64748b';
    const sourceTone = item.source === 'THN' ? 'global' : 'tw';
    const scored = item.risk_score != null;
    const scoreCell = scored
      ? `<span class="mono text-[12px] font-semibold text-[color:var(--ink)]">${esc(item.risk_score)}</span>`
      : '<span class="mono text-[11px] text-[color:var(--faint)]">—</span>';
    const priorityCell = item.priority
      ? `<span class="badge" data-tone="${esc(LEVEL_TONE[item.risk_level] || 'low')}">${esc(item.priority)}</span>`
      : '<span class="badge" data-tone="low">產業</span>';
    return `
        <tr class="feed-row" data-row="${item.id}" data-open="false" tabindex="0" aria-expanded="false">
          <td><span class="badge" data-tone="${sourceTone}">${esc(item.source)}</span></td>
          <td>
            <div class="feed-title">${
              item.source_url
                ? `<a class="feed-link" href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a>`
                : esc(item.title)
            }</div>
            <div class="mt-1 flex items-center gap-2 text-[10px] text-[color:var(--faint)]">
              <span class="mono">#${esc(item.id)}</span>
              <span class="h-2 w-px bg-[#27384f]"></span>
              <span>${esc(item.category_label)}</span>
              <span class="mono rounded border border-[#27384f] px-1">C${esc(item.cluster ?? '—')}</span>
              <span class="mono text-[color:var(--muted)]">${esc(item.published_at)}</span>
            </div>
          </td>
          <td>
            <span class="inline-flex items-center gap-1.5 text-[11px]">
              <span class="legend-swatch" style="background:${metaColor}"></span>
              ${esc(item.meta_label)}
            </span>
          </td>
          <td>${scoreCell}</td>
          <td>${priorityCell}</td>
          <td><span class="mono text-[10.5px] text-[color:var(--faint)]">${esc(item.published_at)}</span></td>
        </tr>`;
  }

  /* Rows are rendered once. Expanding one only inserts or removes its own
     detail row: the previous code rebuilt the whole tbody and re-attached two
     listeners to every row on each click. */
  function syncFeedDetail() {
    const body = $('#feedBody');
    if (!body) return;

    body.querySelectorAll('.feed-detail-row').forEach((node) => node.remove());
    const rows = Array.from(body.querySelectorAll('.feed-row'));
    rows.forEach((row) => {
      row.setAttribute('aria-expanded', "false");
      row.dataset.open = 'false';
    });

    const id = state.openRowId;
    if (id == null) return;

    const row = rows.find((node) => Number(node.dataset.row) === id);
    const item = (state.feedItems || []).find((entry) => entry.id === id);
    if (!row || !item) return;

    row.setAttribute('aria-expanded', "true");
    row.dataset.open = 'true';
    row.insertAdjacentHTML('afterend', detailRowHtml(item));
  }

  function toggleFeedRow(id) {
    state.openRowId = state.openRowId === id ? null : id;
    syncFeedDetail();
  }

  function bindFeed() {
    const body = $('#feedBody');
    if (!body) return;

    const rowFrom = (event) => {
      if (event.target.closest('a')) return null;
      return event.target.closest('.feed-row');
    };

    body.addEventListener('click', (event) => {
      const row = rowFrom(event);
      if (row) toggleFeedRow(Number(row.dataset.row));
    });

    body.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      const row = rowFrom(event);
      if (!row) return;
      event.preventDefault();
      toggleFeedRow(Number(row.dataset.row));
    });
  }

  function renderFeed(items) {
    const body = $('#feedBody');
    if (!body) return;

    state.feedItems = items;

    if (!items.length) {
      body.innerHTML = `
        <tr><td colspan="6" class="py-10">
          <div class="empty">
            <svg class="ico h-6 w-6"><use href="#i-search" /></svg>
            <p>目前篩選條件下沒有符合的情資項目。</p>
          </div>
        </td></tr>`;
      $('#feedCount').textContent = '0';
      $('#feedTotal').textContent = num(state.total);
      return;
    }

    body.innerHTML = items.map(feedRowHtml).join('');
    $('#feedCount').textContent = num(items.length);
    $('#feedTotal').textContent = num(state.total);
    syncFeedDetail();
  }

  function renderPagination() {
    const pages = Math.max(1, Math.ceil(state.total / PAGE_SIZE));
    $('#pageLabel').textContent = `${state.page + 1} / ${pages}`;
    $('#prevPageBtn').disabled = state.page === 0;
    $('#nextPageBtn').disabled = state.page + 1 >= pages;
  }

  /* -------------------------------------------------------------- assessment */

  function collectAssessment() {
    const cvssEnabled = $('#cvssEnabled').checked;
    const payload = {
      asset_type: $('#assetType').value,
      threat_source: $('#threatSource').value,
      category: $('#category').value,
      region: state.form.region || 'taiwan',
      exposure: $('#exposure').value,
      exploit_status: $('#exploitStatus').value,
      data_sensitivity: state.form.sensitivity,
      controls: Array.from(state.form.controls),
    };
    if (cvssEnabled) payload.cvss = Number($('#cvss').value);
    const cve = $('#cveId').value.trim().toUpperCase();
    if (cve) payload.cve_id = cve;
    const name = $('#assetName').value.trim();
    if (name) payload.asset_name = name;
    return payload;
  }

  async function runAssessment(event) {
    event?.preventDefault();
    if (state.busy) return;
    if (!validateForm()) {
      toast('CVE 編號格式不正確，請使用 CVE-YYYY-NNNN。', 'error');
      $('#cveId').focus();
      return;
    }

    const payload = collectAssessment();
    payload.region = state.form.region || 'taiwan';

    state.busy = true;
    const btn = $('#assessBtn');
    const icon = $('#assessIcon');
    const label = $('#assessBtnLabel');
    btn.disabled = true;
    label.textContent = '運算中…';
    icon.classList.add('spin');

    try {
      const result = await api('/assess', { method: 'POST', body: JSON.stringify(payload) });
      renderAssessment(result);
      toast(`評估完成：${result.priority} · 風險分數 ${result.score}`, 'success');
    } catch (error) {
      toast(`評估失敗：${error.message}`, 'error');
    } finally {
      state.busy = false;
      btn.disabled = false;
      label.textContent = '執行風險評估';
      icon.classList.remove('spin');
    }
  }

  function animateScore(target, tone) {
    const ring = $('#scoreRing');
    const valueEl = $('#scoreValue');
    if (!ring || !valueEl) return;

    ring.style.setProperty('--ring-color', tone);
    const reduced =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reduced) {
      ring.style.setProperty('--pct', String(target));
      valueEl.textContent = Math.round(target);
      return;
    }

    const duration = 560;
    const start = performance.now();
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = target * eased;
      ring.style.setProperty('--pct', current.toFixed(1));
      valueEl.textContent = Math.round(current);
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  function renderAssessment(result) {
    $('#assessEmpty').classList.add('hidden');
    const panel = $('#assessResult');
    panel.classList.remove('hidden');

    const tone = PRIORITY_TONE[result.priority] || '#22d3ee';
    animateScore(result.score, tone);

    const badge = $('#priorityBadge');
    badge.textContent = result.priority;
    badge.className = `badge badge-${result.priority.toLowerCase()}`;
    badge.style.color = tone;
    badge.style.borderColor = `${tone}66`;
    badge.style.background = `${tone}1f`;

    $('#resultHeadline').textContent = result.headline || result.priority_label;
    $('#resultLevel').textContent = `${result.risk_level} · 信賴度 ${(result.confidence * 100).toFixed(0)}%`;
    $('#resultSla').textContent = `SLA ${result.sla_hours}h`;
    $('#resultConfidence').textContent = result.cve_id || '無 CVE';
    $('#resultSummary').textContent = result.summary;
    $('#resultOwner').textContent = result.owner;
    $('#assessIdBadge').textContent = `#${result.assessment_id}`;
    $('#planCount').textContent = `${result.action_plan.length} steps`;

    const maxPoints = Math.max(...result.factors.map((factor) => factor.weight * 100), 1);
    $('#factorList').innerHTML = result.factors
      .map((factor, index) => {
        const width = Math.min(100, (factor.points / maxPoints) * 100);
        return `
        <div class="factor" style="animation-delay:${index * 40}ms">
          <div class="factor-head">
            <span class="factor-label">${esc(factor.label)}</span>
            <span class="factor-value">${esc(factor.value)} · ${esc(factor.points)} pt</span>
          </div>
          <div class="factor-track"><div class="factor-fill" data-width="${width.toFixed(1)}"></div></div>
        </div>`;
      })
      .join('');

    requestAnimationFrame(() => {
      $$('#factorList .factor-fill').forEach((fill) => {
        fill.style.width = `${fill.dataset.width}%`;
      });
    });

    $('#adjustmentList').innerHTML = (result.adjustments || [])
      .map((adjustment) => {
        const positive = adjustment.points > 0;
        const negative = adjustment.points < 0;
        const color = positive ? '#fb7185' : negative ? '#34d399' : '#8b9ab2';
        const sign = positive ? '+' : '';
        return `<span class="badge" style="color:${color};border-color:${color}44;background:${color}14">
          ${esc(adjustment.label)}${adjustment.points ? ` ${sign}${esc(adjustment.points)}` : ''}
        </span>`;
      })
      .join('');

    $('#resultPlan').innerHTML = stepsHtml(result.action_plan);
  }

  /* ------------------------------------------------------------------- wiring */

  function bindFilters() {
    $$('[data-priority]').forEach((chip) => {
      if (!chip.classList.contains('chip')) return;
      chip.addEventListener('click', () => {
        state.filters.priority = chip.dataset.priority || '';
        state.matrixSelection = state.filters.priority;
        state.page = 0;
        renderPriorityChips();
        syncMatrixSelection();
        loadThreats();
      });
    });

    $$('[data-region]').forEach((chip) => {
      if (!chip.classList.contains('chip')) return;
      chip.addEventListener('click', () => {
        state.filters.region = chip.dataset.region || '';
        state.page = 0;
        renderPriorityChips();
        loadThreats();
      });
    });

    $('#categoryFilter')?.addEventListener('change', (event) => {
      state.filters.category = event.target.value;
      state.page = 0;
      loadThreats();
    });

    $('#sortSelect')?.addEventListener('change', (event) => {
      state.filters.sort = event.target.value;
      state.page = 0;
      loadThreats();
    });

    const search = $('#searchInput');
    search?.addEventListener(
      'input',
      debounce((event) => {
        state.filters.q = event.target.value.trim();
        state.page = 0;
        loadThreats();
      }, 280)
    );

    $('#prevPageBtn')?.addEventListener('click', () => {
      if (state.page > 0) {
        state.page -= 1;
        loadThreats();
      }
    });
    $('#nextPageBtn')?.addEventListener('click', () => {
      if ((state.page + 1) * PAGE_SIZE < state.total) {
        state.page += 1;
        loadThreats();
      }
    });

    $('#clearMatrixBtn')?.addEventListener('click', () => {
      state.matrixSelection = '';
      state.filters.priority = '';
      state.page = 0;
      syncMatrixSelection();
      renderPriorityChips();
      loadThreats();
    });
  }

  function bindForm() {
    const form = $('#assessForm');
    form?.addEventListener('submit', runAssessment);

    $('#cvss')?.addEventListener('input', (event) => {
      const value = Number(event.target.value);
      $('#cvssValue').textContent = $('#cvssEnabled').checked ? value.toFixed(1) : '未提供';
    });

    $('#cvssEnabled')?.addEventListener('change', (event) => {
      const enabled = event.target.checked;
      $('#cvss').disabled = !enabled;
      $('#cvssValue').textContent = enabled ? Number($('#cvss').value).toFixed(1) : '未提供';
    });

    const check = $('[data-group="sensitivity"][aria-pressed="true"]');
    if (check) state.form.sensitivity = check.dataset.value;

    $$('[data-group="sensitivity"]').forEach((chip) => {
      chip.addEventListener('click', () => {
        $$('[data-group="sensitivity"]').forEach((other) =>
          other.setAttribute('aria-pressed', String(other === chip))
        );
        state.form.sensitivity = chip.dataset.value;
      });
    });

    $$('[data-control]').forEach((chip) => {
      chip.addEventListener('click', () => {
        const pressed = chip.getAttribute('aria-pressed') === 'true';
        chip.setAttribute('aria-pressed', String(!pressed));
        if (pressed) state.form.controls.delete(chip.dataset.control);
        else state.form.controls.add(chip.dataset.control);
      });
    });

    // Region selector inside the form (reuses chip styling).
    $$('[data-form-region]').forEach((chip) => {
      chip.addEventListener('click', () => {
        $$('[data-form-region]').forEach((other) =>
          other.setAttribute('aria-pressed', String(other === chip))
        );
        state.form.region = chip.dataset.formRegion;
      });
    });
    state.form.region = 'taiwan';

    $('#resetFormBtn')?.addEventListener('click', () => {
      form.reset();
      state.form.controls.clear();
      state.form.sensitivity = 'medium';
      state.form.region = 'taiwan';
      $$('[data-control]').forEach((chip) => chip.setAttribute('aria-pressed', 'false'));
      $$('[data-group="sensitivity"]').forEach((chip) =>
        chip.setAttribute('aria-pressed', String(chip.dataset.value === 'medium'))
      );
      $$('[data-form-region]').forEach((chip) =>
        chip.setAttribute('aria-pressed', String(chip.dataset.formRegion === 'taiwan'))
      );
      $('#cvssValue').textContent = '7.5';
      $('#cveError').classList.add('hidden');
      $('#cveId').setAttribute('aria-invalid', 'false');
      $('#assessEmpty').classList.remove('hidden');
      $('#assessResult').classList.add('hidden');
      $('#assessIdBadge').textContent = '待評估';
      toast('已重設評估參數。', 'info');
    });

    $('#cveId')?.addEventListener('input', () => validateForm());
  }

  function bindGlobal() {
    const refresh = async () => {
      const icon = $('#refreshIcon');
      icon?.classList.add('spin');
      try {
        await Promise.all([loadStats({ silent: true }), loadThreats()]);
        toast('情資統計已同步。', 'success');
      } catch (error) {
        toast(`同步失敗：${error.message}`, 'error');
      } finally {
        setTimeout(() => icon?.classList.remove('spin'), 250);
      }
    };
    $('#refreshBtn')?.addEventListener('click', refresh);

    document.addEventListener('keydown', (event) => {
      if (event.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        event.preventDefault();
        $('#searchInput')?.focus();
      }
    });
  }

  /* --------------------------------------------------------------------- boot */

  /* -------------------------------------------------------- patch priority */
  let patchExposure = true;

  function exposureBadge(item) {
    const span = document.createElement('span');
    const tone = item.exposure === 'public'
      ? 'border-cyan-400/40 bg-cyan-400/10 text-cyan-300'
      : item.exposure === 'internal'
        ? 'border-amber-400/40 bg-amber-400/10 text-amber-300'
        : 'border-slate-600/50 bg-slate-700/20 text-slate-400';
    span.className = 'inline-flex items-center rounded-full border px-2 py-0.5 text-[10.5px] ' + tone;
    span.textContent = item.exposure === 'public' ? '對外' : item.exposure === 'internal' ? '內網' : '未知';
    span.title = item.exposure_label || '';
    return span;
  }

  function patchBadge(priority) {
    const span = document.createElement('span');
    span.className = 'badge badge-' + priority.toLowerCase();
    span.textContent = priority;
    return span;
  }

  function patchCell(text, className) {
    const td = document.createElement('td');
    if (className) td.className = className;
    td.textContent = text;
    return td;
  }

  // Values from the API are untrusted: every cell goes through textContent.
  function renderPatchPriority(data) {
    const body = $('#patchBody');
    const summary = $('#patchSummary');
    if (!body) return;
    body.textContent = '';
    if (summary) {
      summary.textContent = '';
      const counts = (data.summary && data.summary.by_priority) || {};
      ['P1', 'P2', 'P3'].forEach((key) => {
        const chip = patchBadge(key);
        chip.textContent = key + ' ' + (counts[key] || 0);
        summary.appendChild(chip);
      });
    }
    const asOf = $('#patchAsOf');
    if (asOf) {
      asOf.textContent = data.data_as_of
        ? '資料截止 ' + data.data_as_of + (data.stale_days != null ? '（' + data.stale_days + ' 天前）' : '')
        : '';
    }
    const fragment = document.createDocumentFragment();
    (data.items || []).forEach((item) => {
      const tr = document.createElement('tr');
      tr.className = 'border-t border-[#1b2739]/70';

      const cve = document.createElement('td');
      cve.className = 'px-4 py-2.5 mono text-[11.5px] text-cyan-200';
      cve.textContent = item.cve;
      tr.appendChild(cve);

      const epssCell = document.createElement('td');
      epssCell.className = 'px-2 py-2.5';
      const bar = document.createElement('div');
      bar.className = 'epss-bar';
      const fill = document.createElement('span');
      fill.className = 'epss-fill';
      const ratio = Math.max(0, Math.min(1, Number(item.epss) || 0));
      fill.style.width = Math.round(ratio * 100) + '%';
      bar.appendChild(fill);
      epssCell.appendChild(bar);
      const label = document.createElement('span');
      label.className = 'mono mt-1 block text-[10px] text-[color:var(--faint)]';
      label.textContent = item.epss == null ? '—' : Math.round(ratio * 100) + '%';
      epssCell.appendChild(label);
      tr.appendChild(epssCell);

      tr.appendChild(patchCell(item.cvss == null ? '—' : Number(item.cvss).toFixed(1),
        'px-2 py-2.5 mono text-[11.5px] text-slate-300'));
      const exposureCell = document.createElement('td');
      exposureCell.className = 'px-2 py-2.5';
      exposureCell.appendChild(exposureBadge(item));
      if (item.assets && item.assets.length) {
        const assetsLine = document.createElement('span');
        assetsLine.className = 'mono mt-1 block text-[9.5px] text-[color:var(--faint)]';
        assetsLine.textContent = item.assets.slice(0, 2).join(', ') + (item.assets.length > 2 ? ' +' + (item.assets.length - 2) : '');
        assetsLine.title = item.assets.join(', ');
        exposureCell.appendChild(assetsLine);
      }
      tr.appendChild(exposureCell);

      tr.appendChild(patchCell(String(item.articles || 0), 'px-2 py-2.5 mono text-[11.5px] text-slate-400'));

      const badgeCell = document.createElement('td');
      badgeCell.className = 'px-2 py-2.5';
      badgeCell.appendChild(patchBadge(item.priority));
      tr.appendChild(badgeCell);

      tr.appendChild(patchCell(item.sla, 'px-2 py-2.5 text-[11.5px] text-slate-300'));
      tr.appendChild(patchCell(item.reason, 'px-4 py-2.5 text-[11.5px] text-[color:var(--muted)]'));
      fragment.appendChild(tr);
    });
    body.appendChild(fragment);
  }

  async function loadPatchPriority() {
    const body = $('#patchBody');
    if (!body) return;
    try {
      const suffix = patchExposure ? '' : '&exposure=false';
      const data = await api('/patch-priority?limit=8' + suffix);
      renderPatchPriority(data);
    } catch (error) {
      body.textContent = '';
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 8;
      td.className = 'px-4 py-8 text-center text-[12px] text-[color:var(--faint)]';
      td.textContent = '修補優先級載入失敗：' + error.message;
      tr.appendChild(td);
      body.appendChild(tr);
    }
  }

  // The footer build tag mirrors the asset query string, so it can never drift
  // from the bundle that is actually running.
  function stampBuild() {
    const tag = $('#buildTag');
    const link = document.querySelector('link[href*="styles.css"]');
    if (!tag || !link) return;
    try {
      const version = new URL(link.href, location.href).searchParams.get('v');
      if (version) tag.textContent = 'build ' + version;
    } catch {
      /* keep the placeholder */
    }
  }

  async function init() {
    stampBuild();
    bindFilters();
    bindFeed();
    bindForm();
    bindGlobal();
    renderPriorityChips();

    try {
      await loadStats();
    } catch {
      /* the error toast already fired */
    }
    loadThreats();
    loadPatchPriority();

    const exposureToggle = $('#patchExposureToggle');
    if (exposureToggle) {
      exposureToggle.addEventListener('click', () => {
        patchExposure = !patchExposure;
        exposureToggle.textContent = patchExposure ? '曝險：開' : '曝險：關';
        exposureToggle.setAttribute('aria-pressed', String(patchExposure));
        loadPatchPriority();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
