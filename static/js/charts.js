/**
 * Library Management System – Charts (Chart.js)
 * Renders: Books by Category (doughnut), Issue Trend (line), Fine Summary (bar)
 */

(function () {
  'use strict';

  // Chart.js global defaults
  function setChartDefaults() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    Chart.defaults.color          = isDark ? '#94a3b8' : '#64748b';
    Chart.defaults.borderColor    = isDark ? '#334155' : '#e2e8f0';
    Chart.defaults.font.family    = "'Inter', sans-serif";
    Chart.defaults.font.size      = 12;
    Chart.defaults.plugins.legend.labels.padding = 16;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
  }

  const PALETTE = [
    '#6366f1','#14b8a6','#f59e0b','#ef4444','#3b82f6',
    '#8b5cf6','#06b6d4','#f97316','#84cc16','#ec4899',
  ];

  /* ── Books by Category (Doughnut) ──────────────────────── */
  async function renderCategoryChart() {
    const canvas = document.getElementById('categoryChart');
    if (!canvas) return;

    try {
      const res  = await fetch('/api/charts/books-by-category');
      const data = await res.json();
      if (!data.labels.length) return;

      setChartDefaults();
      new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels: data.labels,
          datasets: [{
            data:            data.data,
            backgroundColor: PALETTE.slice(0, data.labels.length),
            borderWidth:     2,
            borderColor:     document.documentElement.getAttribute('data-theme') === 'dark'
                               ? '#1e293b' : '#fff',
            hoverBorderWidth: 0,
            hoverOffset: 6,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '68%',
          plugins: {
            legend: {
              position: 'right',
              labels: { font: { size: 12 }, boxWidth: 12, padding: 12 },
            },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ${ctx.label}: ${ctx.parsed} books`,
              },
            },
          },
        },
      });
    } catch (e) { console.error('Category chart error:', e); }
  }

  /* ── Issue Trend (Line) ─────────────────────────────────── */
  async function renderIssueTrendChart() {
    const canvas = document.getElementById('issueTrendChart');
    if (!canvas) return;

    try {
      const res  = await fetch('/api/charts/issue-trend');
      const data = await res.json();

      setChartDefaults();
      new Chart(canvas, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label:           'Books Issued',
            data:            data.data,
            borderColor:     '#6366f1',
            backgroundColor: 'rgba(99,102,241,.1)',
            borderWidth:     2.5,
            pointRadius:     3,
            pointBackgroundColor: '#6366f1',
            fill:            true,
            tension:         0.4,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ${ctx.parsed.y} books issued`,
              },
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { precision: 0, stepSize: 1 },
              grid: { color: 'rgba(148,163,184,.12)' },
            },
            x: {
              grid: { display: false },
              ticks: {
                maxTicksLimit: 10,
                maxRotation: 0,
              },
            },
          },
        },
      });
    } catch (e) { console.error('Issue trend chart error:', e); }
  }

  /* ── Fine Summary (Bar) ──────────────────────────────────── */
  async function renderFineSummaryChart() {
    const canvas = document.getElementById('fineChart');
    if (!canvas) return;

    try {
      const res  = await fetch('/api/charts/fine-summary');
      const data = await res.json();

      setChartDefaults();
      new Chart(canvas, {
        type: 'bar',
        data: {
          labels: data.labels,
          datasets: [{
            label: 'Amount (₹)',
            data:  data.data,
            backgroundColor: ['rgba(245,158,11,.8)', 'rgba(34,197,94,.8)', 'rgba(100,116,139,.8)'],
            borderRadius: 8,
            borderWidth:  0,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ₹${ctx.parsed.y.toFixed(2)}`,
              },
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(148,163,184,.12)' },
              ticks: { callback: (v) => `₹${v}` },
            },
            x: { grid: { display: false } },
          },
        },
      });
    } catch (e) { console.error('Fine chart error:', e); }
  }

  /* ── Student: Borrowing History Mini Chart ───────────────── */
  function renderStudentHistoryChart(labels, data) {
    const canvas = document.getElementById('studentHistoryChart');
    if (!canvas) return;
    setChartDefaults();
    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Books Borrowed',
          data:  data,
          backgroundColor: 'rgba(20,184,166,.7)',
          borderRadius: 6,
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: 'rgba(148,163,184,.12)' } },
          x: { grid: { display: false } },
        },
      },
    });
  }

  window.renderStudentHistoryChart = renderStudentHistoryChart;

  /* ── Init all charts on page load ───────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    renderCategoryChart();
    renderIssueTrendChart();
    renderFineSummaryChart();
  });

  // Re-render when theme changes
  document.addEventListener('themeChanged', () => {
    // Destroy and re-render
    Chart.instances && Object.values(Chart.instances).forEach(c => c.destroy());
    renderCategoryChart();
    renderIssueTrendChart();
    renderFineSummaryChart();
  });

})();
