const AdminApp = {
  init() {
    this.setupSidebar();
    this.setupDrawers();
    this.setupTabs();
    this.setupFilters();
  },

  setupSidebar() {
    const links = document.querySelectorAll('.sidebar-link');
    const current = window.location.pathname;
    links.forEach(link => {
      if (link.getAttribute('href') === current) link.classList.add('active');
    });
  },

  setupDrawers() {
    document.querySelectorAll('[data-drawer-open]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.drawerOpen;
        document.getElementById(id)?.classList.add('open');
        document.getElementById(id + '-overlay')?.classList.add('open');
      });
    });
    document.querySelectorAll('.drawer-close, .drawer-overlay').forEach(el => {
      el.addEventListener('click', () => {
        document.querySelectorAll('.drawer.open, .drawer-overlay.open').forEach(d => d.classList.remove('open'));
      });
    });
  },

  setupTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const parent = tab.closest('.tabs');
        parent.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const target = tab.dataset.tab;
        const container = tab.closest('.card') || document;
        container.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
        const content = document.getElementById(target);
        if (content) content.style.display = 'block';
      });
    });
    // show first tab content
    document.querySelectorAll('.tabs').forEach(group => {
      const firstTab = group.querySelector('.tab.active') || group.querySelector('.tab');
      if (firstTab) firstTab.click();
    });
  },

  setupFilters() {
    document.querySelectorAll('.filter-select, .filter-search').forEach(input => {
      input.addEventListener('change', () => this.applyFilters());
      input.addEventListener('keyup', () => this.applyFilters());
    });
  },

  applyFilters() {
    const table = document.querySelector('.filter-table');
    if (!table) return;
    const rows = table.querySelectorAll('tbody tr');
    const filters = {};
    document.querySelectorAll('.filter-select, .filter-search').forEach(el => {
      const key = el.dataset.filter || el.id || el.name || 'search';
      filters[key] = el.value.toLowerCase().trim();
    });
    rows.forEach(row => {
      let show = true;
      for (const [key, val] of Object.entries(filters)) {
        if (!val) continue;
        const cell = row.querySelector(`[data-col="${key}"]`);
        if (cell && !cell.textContent.toLowerCase().includes(val)) { show = false; break; }
        if (key === 'search') {
          const txt = row.textContent.toLowerCase();
          if (!txt.includes(val)) { show = false; break; }
        }
      }
      row.style.display = show ? '' : 'none';
    });
  },

  formatCurrency(n) { return '$' + Number(n).toLocaleString('es-CO', { minimumFractionDigits: 0 }); },
  formatDate(d) {
    if (!d) return '-';
    return new Date(d).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
  },
  timeAgo(d) {
    if (!d) return '-';
    const diff = Date.now() - new Date(d).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h`;
    const days = Math.floor(hrs / 24);
    if (days < 30) return `${days}d`;
    return this.formatDate(d);
  }
};

document.addEventListener('DOMContentLoaded', () => AdminApp.init());
