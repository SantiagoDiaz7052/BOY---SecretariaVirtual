const AdminApp = {
  notifications: [],
  searchData: [],
  currentContextoId: null,
  currentControl: null,
  pollTimer: null,

  init() {
    this.setupSidebar();
    this.setupDrawers();
    this.setupNotifications();
    this.setupSearch();
    this.setupBandejaFilters();
    this.setupBandejaAutoOpen();
    this.startPolling();
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
    fetch('/admin/api/notificaciones', { credentials: 'same-origin' })
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
    const notif = this.notifications.find(n => n.id === id);
    if (notif && notif.referencia_id) {
      window.location.href = '/admin/bandeja?conversacion=' + notif.referencia_id;
    } else {
      window.location.href = '/admin/bandeja';
    }
  },

  /* ─── POLLING ─── */
  startPolling() {
    this.loadNotifications();
    this.pollTimer = setInterval(() => {
      this.loadNotifications();
    }, 10000);
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
    fetch(`/admin/api/buscar?q=${encodeURIComponent(q)}`, { credentials: 'same-origin' })
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
        document.querySelectorAll('[data-control]').forEach(card => {
          if (!filter || filter === 'todas') {
            card.style.display = '';
            return;
          }
          card.style.display = card.dataset.control === filter ? '' : 'none';
        });
      });
    });
  },

  /* ─── BANDEJA AUTO-OPEN ─── */
  setupBandejaAutoOpen() {
    const params = new URLSearchParams(window.location.search);
    const conversacionId = params.get('conversacion');
    if (conversacionId && window.location.pathname === '/admin/bandeja') {
      setTimeout(() => this.abrirConversacion(conversacionId), 500);
    }
  },

  /* ─── CONVERSACIÓN ─── */
  abrirConversacion(contextoId) {
    this.currentContextoId = contextoId;
    const drawer = document.getElementById('conversationDrawer');
    const overlay = document.getElementById('conversationOverlay');
    if (drawer) drawer.classList.add('open');
    if (overlay) overlay.classList.add('open');

    fetch(`/admin/api/conversacion/${contextoId}`, { credentials: 'same-origin' })
      .then(r => r.json())
      .then(data => {
        if (data.error) return;
        this.currentControl = data.control;
        this.renderConversation(data);
        this._startConvPoll();
      })
      .catch(err => console.error('[CONV] Error cargando:', err));
  },

  cerrarConversacion() {
    const drawer = document.getElementById('conversationDrawer');
    const overlay = document.getElementById('conversationOverlay');
    if (drawer) drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
    this.currentContextoId = null;
    this.currentControl = null;
    this._stopConvPoll();
  },

  _convPollTimer: null,
  _lastMsgCount: 0,

  _startConvPoll() {
    this._stopConvPoll();
    this._lastMsgCount = document.querySelectorAll('#convMessages > div').length;
    this._convPollTimer = setInterval(() => {
      if (!this.currentContextoId) { this._stopConvPoll(); return; }
      this._refreshConversation();
    }, 5000);
  },

  _stopConvPoll() {
    if (this._convPollTimer) { clearInterval(this._convPollTimer); this._convPollTimer = null; }
  },

  _refreshConversation() {
    if (!this.currentContextoId) return;
    fetch(`/admin/api/conversacion/${this.currentContextoId}`, { credentials: 'same-origin' })
      .then(r => r.json())
      .then(data => {
        if (data.error) return;
        this.currentControl = data.control;
        const newCount = data.mensajes ? data.mensajes.length : 0;
        if (newCount !== this._lastMsgCount) {
          this._lastMsgCount = newCount;
          this.renderConversation(data);
        }
      })
      .catch(() => {});
  },

  renderConversation(data) {
    const title = document.getElementById('convTitle');
    const status = document.getElementById('convStatus');
    const messages = document.getElementById('convMessages');
    const btnTomar = document.getElementById('btnTomarControl');
    const btnDevolver = document.getElementById('btnDevolverControl');

    if (title) title.textContent = data.numero;
    if (status) {
      const esBoy = data.control === 'boy';
      status.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px;font-size:.85rem;font-weight:500">
        <span style="width:8px;height:8px;border-radius:50%;background:${esBoy ? '#22c55e' : '#a855f7'}"></span>
        ${esBoy ? 'BOY activo' : 'Atención humana — Ivonn'}
      </span>`;
    }
    if (btnTomar) btnTomar.style.display = data.control === 'boy' ? '' : 'none';
    if (btnDevolver) btnDevolver.style.display = data.control === 'ivonn' ? '' : 'none';

    if (messages) {
      messages.innerHTML = data.mensajes.map(m => {
        const esUser = m.rol === 'user';
        const esResumen = m.rol === 'resumen';
        if (esResumen) {
          return `<div style="text-align:center;padding:8px;margin:8px 0;background:var(--bg-secondary);border-radius:6px;font-size:.8rem;color:var(--text-muted)">
            📋 ${m.content}
          </div>`;
        }
        return `<div style="display:flex;${esUser ? 'justify-content:flex-start' : 'justify-content:flex-end'};margin:6px 0">
          <div style="max-width:75%;padding:10px 14px;border-radius:12px;font-size:.85rem;
            ${esUser ? 'background:var(--bg-secondary);color:var(--text-primary)' : 'background:#3b82f6;color:white'}">
            ${m.content}
          </div>
        </div>`;
      }).join('');
      messages.scrollTop = messages.scrollHeight;
    }
  },

  tomarControl() {
    if (!this.currentContextoId) return;
    const btn = document.getElementById('btnTomarControl');
    if (btn) { btn.disabled = true; btn.textContent = 'Tomando...'; }

    fetch(`/admin/api/conversacion/${this.currentContextoId}/tomar-control`, { method: 'POST', credentials: 'same-origin' })
      .then(r => r.json().then(d => ({ ok: r.ok, data: d })))
      .then(({ ok, data }) => {
        if (ok && data.ok) {
          this.currentControl = 'ivonn';
          this._clearConvError();
          this.abrirConversacion(this.currentContextoId);
        } else {
          this._showConvError(`Error al tomar control: ${data.error || 'desconocido'}`);
        }
      })
      .catch(err => {
        this._showConvError('Error de conexión: ' + err.message);
      })
      .finally(() => {
        if (btn) { btn.disabled = false; btn.textContent = 'Tomar control'; }
      });
  },

  devolverControl() {
    if (!this.currentContextoId) return;
    const btn = document.getElementById('btnDevolverControl');
    if (btn) { btn.disabled = true; btn.textContent = 'Devolviendo...'; }

    fetch(`/admin/api/conversacion/${this.currentContextoId}/devolver-control`, { method: 'POST', credentials: 'same-origin' })
      .then(r => r.json().then(d => ({ ok: r.ok, data: d })))
      .then(({ ok, data }) => {
        if (ok && data.ok) {
          this.currentControl = 'boy';
          this._clearConvError();
          this.abrirConversacion(this.currentContextoId);
        } else {
          this._showConvError(`Error al devolver control: ${data.error || 'desconocido'}`);
        }
      })
      .catch(err => {
        this._showConvError('Error de conexión: ' + err.message);
      })
      .finally(() => {
        if (btn) { btn.disabled = false; btn.textContent = 'Devolver a BOY'; }
      });
  },

  responderMensaje() {
    if (!this.currentContextoId) return;
    if (this.currentControl === 'boy') {
      this._showConvError('Debes tomar el control primero');
      return;
    }
    const input = document.getElementById('convInput');
    if (!input) return;
    const texto = input.value.trim();
    if (!texto) return;

    const btn = input.parentElement.querySelector('button');
    if (btn) { btn.disabled = true; btn.textContent = 'Enviando...'; }

    fetch(`/admin/api/conversacion/${this.currentContextoId}/responder`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ texto })
    })
      .then(r => r.json().then(d => ({ ok: r.ok, data: d })))
      .then(({ ok, data }) => {
        if (ok && data.ok) {
          input.value = '';
          this._clearConvError();
          const msgs = document.getElementById('convMessages');
          if (msgs) {
            msgs.innerHTML += `<div style="display:flex;justify-content:flex-end;margin:6px 0">
              <div style="max-width:75%;padding:10px 14px;border-radius:12px;font-size:.85rem;background:#3b82f6;color:white">${texto}</div>
            </div>`;
            msgs.scrollTop = msgs.scrollHeight;
          }
          setTimeout(() => this._refreshConversation(), 1000);
        } else {
          const msg = data.error === 'twilio_error' ? `Error Twilio: ${data.detail || 'desconocido'}` :
                      data.error === 'texto_requerido' ? 'Escribe un mensaje.' :
                      `Error: ${data.error || 'desconocido'}`;
          this._showConvError(msg);
        }
      })
      .catch(err => {
        this._showConvError('Error de conexión: ' + err.message);
      })
      .finally(() => {
        if (btn) { btn.disabled = false; btn.textContent = 'Enviar'; }
      });
  },

  _showConvError(msg) {
    const el = document.getElementById('convError');
    if (el) { el.textContent = msg; el.style.display = 'block'; }
  },

  _clearConvError() {
    const el = document.getElementById('convError');
    if (el) { el.style.display = 'none'; }
  },
};

document.addEventListener('DOMContentLoaded', () => AdminApp.init());
