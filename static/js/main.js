/**
 * Library Management System – Main JavaScript
 * Handles: dark mode, sidebar toggle, toast notifications,
 *          live search, loading spinners, auto-dismiss alerts
 */

(function () {
  'use strict';

  /* ── Dark Mode ──────────────────────────────────────────── */
  const THEME_KEY = 'lms_theme';

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    const icon = document.getElementById('theme-icon');
    if (icon) {
      icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
    const label = document.getElementById('theme-label');
    if (label) label.textContent = theme === 'dark' ? 'Light' : 'Dark';
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || 'light';
    applyTheme(saved);
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  }

  window.toggleTheme = toggleTheme;

  /* ── Sidebar Toggle ─────────────────────────────────────── */
  const SIDEBAR_KEY = 'lms_sidebar_collapsed';

  function initSidebar() {
    const sidebar  = document.querySelector('.sidebar');
    const content  = document.querySelector('.main-content');
    const topbar   = document.querySelector('.topbar');
    if (!sidebar) return;

    // Desktop collapse state
    const collapsed = localStorage.getItem(SIDEBAR_KEY) === 'true';
    if (window.innerWidth >= 992 && collapsed) {
      sidebar.classList.add('collapsed');
      content?.classList.add('collapsed');
      topbar?.classList.add('collapsed');
    }

    // Toggle button
    const toggleBtn = document.getElementById('sidebar-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        if (window.innerWidth < 992) {
          // Mobile: use overlay
          sidebar.classList.toggle('mobile-open');
          document.querySelector('.sidebar-overlay')?.classList.toggle('active');
        } else {
          sidebar.classList.toggle('collapsed');
          content?.classList.toggle('collapsed');
          topbar?.classList.toggle('collapsed');
          localStorage.setItem(SIDEBAR_KEY, sidebar.classList.contains('collapsed'));
        }
      });
    }

    // Overlay click closes sidebar on mobile
    document.querySelector('.sidebar-overlay')?.addEventListener('click', () => {
      sidebar.classList.remove('mobile-open');
      document.querySelector('.sidebar-overlay')?.classList.remove('active');
    });
  }

  /* ── Toast Notifications ────────────────────────────────── */
  function showToast(message, type = 'info', duration = 4000) {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const icons = {
      success: 'fa-circle-check',
      danger:  'fa-circle-xmark',
      warning: 'fa-triangle-exclamation',
      info:    'fa-circle-info',
    };

    const colors = {
      success: '#22c55e',
      danger:  '#ef4444',
      warning: '#f59e0b',
      info:    '#3b82f6',
    };

    const toast = document.createElement('div');
    toast.className = `lms-toast toast-${type}`;
    toast.innerHTML = `
      <i class="fas ${icons[type] || icons.info}" style="color:${colors[type] || colors.info};font-size:18px;flex-shrink:0"></i>
      <span style="flex:1;font-size:13px;color:var(--text-primary)">${message}</span>
      <button onclick="this.parentElement.remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;padding:0;font-size:14px">
        <i class="fas fa-times"></i>
      </button>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'fadeOut .3s ease forwards';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  window.showToast = showToast;

  /* ── Auto-convert Flask flash messages to toasts ─────────── */
  function initFlashToasts() {
    const flashContainer = document.getElementById('flash-messages');
    if (!flashContainer) return;
    const alerts = flashContainer.querySelectorAll('[data-flash]');
    alerts.forEach(alert => {
      const type = alert.dataset.flash;
      const msg  = alert.textContent.trim();
      showToast(msg, type === 'error' ? 'danger' : type);
      alert.remove();
    });
  }

  /* ── Auto-dismiss regular Bootstrap alerts ───────────────── */
  function initAlertDismiss() {
    document.querySelectorAll('.alert-dismissible').forEach(alert => {
      setTimeout(() => {
        alert.style.transition = 'opacity .5s';
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 500);
      }, 5000);
    });
  }

  /* ── Loading Spinner ─────────────────────────────────────── */
  function showSpinner() {
    const el = document.getElementById('loading-overlay');
    if (el) el.style.display = 'flex';
  }

  function hideSpinner() {
    const el = document.getElementById('loading-overlay');
    if (el) el.style.display = 'none';
  }

  window.showSpinner = showSpinner;
  window.hideSpinner = hideSpinner;

  // Show spinner on form submit & link clicks
  document.addEventListener('submit', (e) => {
    const form = e.target;
    if (!form.dataset.noSpinner) showSpinner();
  });

  /* ── Live Search (generic) ──────────────────────────────── */
  function initLiveSearch() {
    const input = document.getElementById('live-search');
    if (!input) return;

    let timeout;
    input.addEventListener('input', () => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        const form = input.closest('form');
        if (form) form.submit();
      }, 400);
    });
  }

  /* ── Confirm Delete ─────────────────────────────────────── */
  function initConfirmDelete() {
    document.querySelectorAll('[data-confirm]').forEach(el => {
      el.addEventListener('click', (e) => {
        const msg = el.dataset.confirm || 'Are you sure?';
        if (!confirm(msg)) e.preventDefault();
      });
    });
  }

  /* ── Book / Member Typeahead (Issue form) ────────────────── */
  function initTypeahead(inputId, apiUrl, displayFn) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const dropdown = document.createElement('div');
    dropdown.className = 'typeahead-dropdown';
    dropdown.style.cssText = `
      position: absolute; z-index: 1000; background: var(--surface);
      border: 1px solid var(--border); border-radius: 10px;
      box-shadow: var(--shadow); max-height: 260px; overflow-y: auto;
      width: 100%; display: none; margin-top: 4px;
    `;
    input.parentElement.style.position = 'relative';
    input.parentElement.appendChild(dropdown);

    let debounceTimer;
    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const q = input.value.trim();
      if (q.length < 2) { dropdown.style.display = 'none'; return; }

      debounceTimer = setTimeout(async () => {
        try {
          const res  = await fetch(`${apiUrl}?q=${encodeURIComponent(q)}`);
          const data = await res.json();
          dropdown.innerHTML = '';
          if (!data.length) {
            dropdown.innerHTML = '<div style="padding:12px 16px;color:var(--text-muted);font-size:13px">No results found</div>';
          } else {
            data.forEach(item => {
              const div = document.createElement('div');
              div.style.cssText = 'padding:10px 16px;cursor:pointer;font-size:13px;border-bottom:1px solid var(--border);transition:background .15s';
              div.innerHTML = displayFn(item);
              div.addEventListener('mouseenter', () => div.style.background = 'var(--bg)');
              div.addEventListener('mouseleave', () => div.style.background = '');
              div.addEventListener('click', () => {
                input.value = item.isbn || item.username || item.membership_id || item.student_id || '';
                dropdown.style.display = 'none';
              });
              dropdown.appendChild(div);
            });
          }
          dropdown.style.display = 'block';
        } catch (err) { console.error('Typeahead error:', err); }
      }, 300);
    });

    document.addEventListener('click', (e) => {
      if (!input.parentElement.contains(e.target)) dropdown.style.display = 'none';
    });
  }

  function initIssueFormTypeaheads() {
    // Book typeahead
    initTypeahead('book_isbn', '/api/books/search', (b) =>
      `<strong>${b.title}</strong><br><small style="color:var(--text-muted)">ISBN: ${b.isbn} | ${b.available} available</small>`
    );
    // Member typeahead
    initTypeahead('member_isbn', '/api/members/search', (m) =>
      `<strong>${m.full_name}</strong><br><small style="color:var(--text-muted)">${m.username} | Books: ${m.active_issues} | Fine: ₹${m.pending_fine}</small>`
    );
  }

  /* ── Notification Badge ─────────────────────────────────── */
  async function fetchNotifCount() {
    try {
      const res  = await fetch('/api/notifications/count');
      const data = await res.json();
      const badge = document.getElementById('notif-badge');
      if (badge) {
        if (data.overdue > 0) {
          badge.textContent = data.overdue;
          badge.style.display = 'flex';
        } else {
          badge.style.display = 'none';
        }
      }
    } catch (e) {}
  }

  /* ── Tooltip init ───────────────────────────────────────── */
  function initTooltips() {
    if (typeof bootstrap !== 'undefined') {
      document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
      });
    }
  }

  /* ── Table row click ────────────────────────────────────── */
  function initClickableRows() {
    document.querySelectorAll('tr[data-href]').forEach(row => {
      row.style.cursor = 'pointer';
      row.addEventListener('click', () => {
        window.location.href = row.dataset.href;
      });
    });
  }

  /* ── Copy to clipboard ──────────────────────────────────── */
  window.copyToClipboard = function (text, btnEl) {
    navigator.clipboard.writeText(text).then(() => {
      if (btnEl) {
        const orig = btnEl.innerHTML;
        btnEl.innerHTML = '<i class="fas fa-check"></i>';
        setTimeout(() => btnEl.innerHTML = orig, 1500);
      }
      showToast('Copied to clipboard!', 'success', 2000);
    });
  };

  /* ── Active nav link highlight ─────────────────────────── */
  function highlightActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.sidebar-link').forEach(link => {
      if (link.getAttribute('href') === path) {
        link.classList.add('active');
      }
    });
  }

  /* ── DOMContentLoaded ───────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
    initFlashToasts();
    initAlertDismiss();
    initLiveSearch();
    initConfirmDelete();
    initIssueFormTypeaheads();
    initTooltips();
    initClickableRows();
    highlightActiveNav();
    fetchNotifCount();

    // Refresh notif badge every 60s
    setInterval(fetchNotifCount, 60000);

    // Hide spinner on page load complete
    hideSpinner();
  });

})();
