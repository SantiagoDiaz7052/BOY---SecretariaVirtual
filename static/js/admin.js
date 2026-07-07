const AdminApp = {
  notifications: [],
  searchData: [],

  init() {
    this.setupSidebar();
    this.setupDrawers();
    this.setupNotifications();
    this.setupSearch();
    this.setupBandejaFilters();
  },

  /* ─── SIDEBAR ─── */
  setupSidebar() {
    const links = document.querySelectorAll('.sidebar-link');
    const current = window.location.pathname;
    links.forEach(link => {
      if (link.getAttribute('href') === current ||
          (current === '/admin' && link.getAttribute('href') === '/admin')) {
        link.classList.add('active');
      }
    });
  },

  /* ─── DRAWERS ─── */
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

  /* ─── NOTIFICACIONES ─── */
  setupNotifications() {
    const btn = document.getElementById('bellBtn');
    const dd = document.getElementById('notifDropdown');
    if (!btn || !dd) return;

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      dd.classList.toggle('open');
      this.loadNotifications();
    });
    document.addEventListener('click', () => dd.classList.remove('open'));
  },

  loadNotifications() {
    fetch('/admin/api/notificaciones')
      .then(r => r.json())
      .then(data => {
        this.notifications = data;
        this.renderNotifications();
      })
      .catch(() => {});
  },

  renderNotifications() {
    const list = document.getElementById('notifList');
    const badge = document.getElementById('bellBadge');
    if (!list) return;

    if (this.notifications.length === 0) {
      list.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:.85rem">No hay notificaciones</div>';
      if (badge) badge.textContent = '0';
      return;
    }

    list.innerHTML = this.notifications.map(n =>
      `<div class="notif-item" onclick="AdminApp.handleNotifClick('${n.id}')">
        <div class="notif-icon">${n.icon}</div>
        <div class="notif-content">
          <div class="notif-text">${n.text}</div>
          <div class="notif-time">${n.time}</div>
        </div>
      </div>`
    ).join('');
    if (badge) badge.textContent = this.notifications.length > 9 ? '9+' : this.notifications.length;
  },

  handleNotifClick(id) {
    window.location.href = '/admin/bandeja';
  },

  /* ─── BÚSQUEDA GLOBAL ─── */
  setupSearch() {
    const input = document.getElementById('globalSearch');
    const results = document.getElementById('searchResults');
    if (!input || !results) return;

    let timer;
    input.addEventListener('input', () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) { results.classList.remove('open'); return; }
      timer = setTimeout(() => this.doSearch(q), 200);
    });
    input.addEventListener('focus', () => {
      if (results.querySelector('.search-result-item')) results.classList.add('open');
    });
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.search-global')) results.classList.remove('open');
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') results.classList.remove('open');
    });
  },

  doSearch(q) {
    const results = document.getElementById('searchResults');
    fetch(`/admin/api/buscar?q=${encodeURIComponent(q)}`)
      .then(r => r.json())
      .then(data => {
        if (data.length === 0) {
          results.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:.82rem">Sin resultados</div>';
        } else {
          results.innerHTML = data.map(item =>
            `<div class="search-result-item" onclick="AdminApp.goToDeportista('${item.id}')">
              <div>
                <div class="sr-name">${item.nombre}</div>
                <div class="sr-detail">${item.documento} · ${item.nivel || 'Sin nivel'} · ${item.estado}</div>
              </div>
              <div style="margin-left:auto;font-size:.75rem;color:var(--text-muted)">${item.telefono || ''}</div>
            </div>`
          ).join('');
        }
        results.classList.add('open');
      })
      .catch(() => {});
  },

  goToDeportista(id) {
    document.getElementById('searchResults')?.classList.remove('open');
    document.getElementById('globalSearch').value = '';
    window.location.href = '/admin/deportistas';
  },

  /* ─── BANDEJA FILTROS ─── */
  setupBandejaFilters() {
    document.querySelectorAll('.bf-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const parent = btn.closest('.bandeja-filters');
        parent.querySelectorAll('.bf-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = btn.dataset.filter;
        document.querySelectorAll('.bandeja-section').forEach(section => {
          if (!filter || filter === 'todas') {
            section.style.display = '';
            return;
          }
          const type = section.dataset.type;
          section.style.display = type === filter ? '' : 'none';
        });
      });
    });
  },
};

document.addEventListener('DOMContentLoaded', () => AdminApp.init());
