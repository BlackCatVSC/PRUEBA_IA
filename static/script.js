const SERVER_URL = '';

function getServerSessionIds() {
    return JSON.parse(localStorage.getItem('serverSessionIds') || '{}');
}

function saveServerSessionIds(ids) {
    localStorage.setItem('serverSessionIds', JSON.stringify(ids));
}

async function sendToServer(message) {
    const ids = getServerSessionIds();
    const user = getSessionUser();
    const body = { message };
    if (user && user.rut) body.rut = user.rut;
    if (ids[currentSessionId]) {
        body.session_id = ids[currentSessionId];
    }
    const res = await fetch(SERVER_URL + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || 'Error del servidor');
    }
    if (data.session_id) {
        ids[currentSessionId] = data.session_id;
        saveServerSessionIds(ids);
    }
    return data.response || '';
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const isHidden = sidebar.classList.contains('-translate-x-full');

    if (isHidden) {
        sidebar.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
        setTimeout(() => overlay.classList.add('opacity-100'), 10);
    } else {
        sidebar.classList.add('-translate-x-full');
        overlay.classList.remove('opacity-100');
        setTimeout(() => overlay.classList.add('hidden'), 300);
    }
}

// ─── Session management ────────────────────────────────────────
function getSessionUser() {
    const raw = localStorage.getItem('sessionUser');
    return raw ? JSON.parse(raw) : null;
}

function saveSessionUser(user) {
    localStorage.setItem('sessionUser', JSON.stringify(user));
}

function clearSession() {
    localStorage.removeItem('sessionUser');
}

function isLoggedIn() {
    return !!getSessionUser();
}

function updateUserGreeting(name) {
    const h2 = document.querySelector('#sidebar h2');
    const greeter = document.getElementById('greeting-bubble');
    if (name) {
        h2.textContent = 'Hola, ' + name + '!';
        if (greeter) greeter.textContent = 'Hola, ' + name + '!';
    } else {
        h2.textContent = 'Hola, Visitante';
        if (greeter) greeter.textContent = 'Hola! En que puedo ayudarte?';
    }
}

function updateChatState() {
    const loggedIn = isLoggedIn();
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chips = document.querySelectorAll('.quick-chips button, .quick-chips a');

    input.disabled = !loggedIn;
    input.placeholder = loggedIn ? 'Escribe aca tu consulta...' : 'Inicia sesion para chatear';
    sendBtn.disabled = !loggedIn;
    chips.forEach(c => { c.style.pointerEvents = loggedIn ? 'auto' : 'none'; c.style.opacity = loggedIn ? '1' : '0.5'; });

    const headerLoginBtn = document.getElementById('header-login-btn');
    if (headerLoginBtn) headerLoginBtn.style.display = loggedIn ? 'none' : 'block';

    const sidebarLogout = document.querySelector('#sidebar .mt-auto button');
    if (sidebarLogout) sidebarLogout.style.display = loggedIn ? 'flex' : 'none';
}

function openLogin() {
    document.getElementById('register-modal-overlay').classList.add('hidden');
    document.getElementById('register-modal-overlay').classList.remove('flex');
    document.getElementById('login-modal-overlay').classList.remove('hidden');
    document.getElementById('login-modal-overlay').classList.add('flex');
    document.getElementById('email-input').focus();
    document.getElementById('login-error').classList.add('hidden');
    document.getElementById('email-input').value = '';
    document.getElementById('password-input').value = '';
}

function closeLogin() {
    document.getElementById('login-modal-overlay').classList.add('hidden');
    document.getElementById('login-modal-overlay').classList.remove('flex');
    document.getElementById('login-error').classList.add('hidden');
    document.getElementById('email-input').value = '';
    document.getElementById('password-input').value = '';
    document.getElementById('login-btn').disabled = false;
    document.getElementById('login-btn-text').classList.remove('hidden');
    document.getElementById('login-spinner').classList.add('hidden');
}

function showLoginError(msg) {
    const err = document.getElementById('login-error');
    err.textContent = msg;
    err.classList.remove('hidden');
}

function showRegister() {
    document.getElementById('login-modal-overlay').classList.add('hidden');
    document.getElementById('login-modal-overlay').classList.remove('flex');
    document.getElementById('register-modal-overlay').classList.remove('hidden');
    document.getElementById('register-modal-overlay').classList.add('flex');
    document.getElementById('reg-name-input').focus();
    document.getElementById('register-error').classList.add('hidden');
}

function closeRegister() {
    document.getElementById('register-modal-overlay').classList.add('hidden');
    document.getElementById('register-modal-overlay').classList.remove('flex');
    document.getElementById('register-error').classList.add('hidden');
    document.getElementById('reg-name-input').value = '';
    document.getElementById('reg-email-input').value = '';
    document.getElementById('reg-password-input').value = '';
    document.getElementById('reg-confirm-input').value = '';
    document.getElementById('register-btn').disabled = false;
    document.getElementById('register-btn-text').classList.remove('hidden');
    document.getElementById('register-spinner').classList.add('hidden');
}

async function handleRegister() {
    const name = document.getElementById('reg-name-input').value.trim();
    const email = document.getElementById('reg-email-input').value.trim();
    const password = document.getElementById('reg-password-input').value.trim();
    const confirmPwd = document.getElementById('reg-confirm-input').value.trim();
    const err = document.getElementById('register-error');
    err.classList.add('hidden');

    if (!name || !email || !password || !confirmPwd) {
        err.textContent = 'Completa todos los campos.';
        err.classList.remove('hidden');
        return;
    }
    if (!email.includes('@') || !email.includes('.')) {
        err.textContent = 'Ingresa un correo electronico valido.';
        err.classList.remove('hidden');
        return;
    }
    if (password.length < 6) {
        err.textContent = 'La contrasena debe tener al menos 6 caracteres.';
        err.classList.remove('hidden');
        return;
    }
    if (password !== confirmPwd) {
        err.textContent = 'Las contrasenas no coinciden.';
        err.classList.remove('hidden');
        return;
    }

    const btn = document.getElementById('register-btn');
    btn.disabled = true;
    document.getElementById('register-btn-text').classList.add('hidden');
    document.getElementById('register-spinner').classList.remove('hidden');

    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();

        if (data.success) {
            saveSessionUser(data.user);
            updateUserGreeting(data.user.name);
            updateChatState();
            closeRegister();
        } else {
            err.textContent = data.error || 'Error al registrar.';
            err.classList.remove('hidden');
            btn.disabled = false;
            document.getElementById('register-btn-text').classList.remove('hidden');
            document.getElementById('register-spinner').classList.add('hidden');
        }
    } catch (e) {
        err.textContent = 'Error de conexion con el servidor.';
        err.classList.remove('hidden');
        btn.disabled = false;
        document.getElementById('register-btn-text').classList.remove('hidden');
        document.getElementById('register-spinner').classList.add('hidden');
    }
}

async function handleLogin() {
    const email = document.getElementById('email-input').value.trim();
    const password = document.getElementById('password-input').value.trim();
    const err = document.getElementById('login-error');
    err.classList.add('hidden');

    if (!email || !password) {
        showLoginError('Por favor ingresa tu correo electronico y contrasena.');
        document.getElementById(!email ? 'email-input' : 'password-input').focus();
        return;
    }

    const btn = document.getElementById('login-btn');
    btn.disabled = true;
    document.getElementById('login-btn-text').classList.add('hidden');
    document.getElementById('login-spinner').classList.remove('hidden');

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();

        if (data.success) {
            saveSessionUser(data.user);
            updateUserGreeting(data.user.name);
            updateChatState();
            closeLogin();
        } else {
            showLoginError(data.error || 'Correo o contrasena incorrectos.');
            btn.disabled = false;
            document.getElementById('login-btn-text').classList.remove('hidden');
            document.getElementById('login-spinner').classList.add('hidden');
        }
    } catch (e) {
        showLoginError('Error de conexion con el servidor.');
        btn.disabled = false;
        document.getElementById('login-btn-text').classList.remove('hidden');
        document.getElementById('login-spinner').classList.add('hidden');
    }
}

let chatSessions = JSON.parse(localStorage.getItem('chatSessions') || '[]');
let currentSessionId = localStorage.getItem('currentSessionId') || null;

function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

function formatTime(ts) {
    const d = new Date(ts);
    return d.toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit' }) + ', ' +
        d.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
}

function getSession(id) {
    return chatSessions.find(s => s.id === id);
}

function saveSessions() {
    localStorage.setItem('chatSessions', JSON.stringify(chatSessions));
    if (currentSessionId) localStorage.setItem('currentSessionId', currentSessionId);
}

function ensureCurrentSession() {
    if (!currentSessionId || !getSession(currentSessionId)) {
        const s = { id: generateId(), title: 'Nuevo Chat', timestamp: Date.now(), messages: [] };
        chatSessions.push(s);
        currentSessionId = s.id;
        saveSessions();
    }
}

function renderHistory() {
    const nav = document.getElementById('history-nav');
    nav.querySelectorAll('.history-entry').forEach(el => el.remove());

    const sorted = [...chatSessions].sort((a, b) => b.timestamp - a.timestamp);
    sorted.forEach(s => {
        const isActive = s.id === currentSessionId;
        const entry = document.createElement('div');
        entry.className = 'history-entry flex items-center gap-2 px-4 py-3 rounded-lg transition-colors group ' +
            (isActive ? 'bg-primary-fixed text-on-primary-fixed-variant font-bold border-l-4 border-primary rounded-r-lg' : 'text-on-surface-variant hover:bg-surface-container-high');

        const link = document.createElement('a');
        link.href = '#';
        link.className = 'flex items-center gap-4 flex-1 min-w-0';
        link.onclick = (e) => { e.preventDefault(); loadSession(s.id); };
        link.innerHTML = '<span class="material-symbols-outlined shrink-0">history</span>' +
            '<div class="flex flex-col min-w-0"><span class="text-body-md truncate max-w-[160px]">' + s.title + '</span>' +
            '<span class="text-xs font-normal opacity-70">' + formatTime(s.timestamp) + '</span></div>';
        entry.appendChild(link);

        const delBtn = document.createElement('button');
        delBtn.className = 'delete-chat-btn shrink-0 w-8 h-8 flex items-center justify-center rounded-full opacity-0 group-hover:opacity-100 hover:bg-surface-container-highest transition-all text-on-surface-variant hover:text-error';
        delBtn.title = 'Eliminar chat';
        delBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">close</span>';
        delBtn.onclick = (e) => { e.stopPropagation(); deleteSession(s.id); };
        entry.appendChild(delBtn);

        nav.appendChild(entry);
    });

    if (chatSessions.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'history-entry text-body-md text-on-surface-variant/50 text-center py-4';
        empty.textContent = 'Sin consultas aun';
        nav.appendChild(empty);
    }
}

function deleteSession(id) {
    const wasActive = id === currentSessionId;

    chatSessions = chatSessions.filter(s => s.id !== id);

    const serverIds = getServerSessionIds();
    delete serverIds[id];
    saveServerSessionIds(serverIds);

    if (chatSessions.length === 0) {
        const s = { id: generateId(), title: 'Nuevo Chat', timestamp: Date.now(), messages: [] };
        chatSessions.push(s);
        currentSessionId = s.id;
        saveSessions();
        renderHistory();
        document.getElementById('chat-messages').innerHTML = renderWelcome();
        return;
    }

    if (wasActive) {
        const sorted = [...chatSessions].sort((a, b) => b.timestamp - a.timestamp);
        currentSessionId = sorted[0].id;
    }

    saveSessions();
    renderHistory();

    if (wasActive) {
        loadSession(currentSessionId);
    }
}

function newChat() {
    if (!isLoggedIn()) { openLogin(); return; }
    const current = getSession(currentSessionId);
    if (current && current.messages.length > 0) {
        current.title = current.messages[0].text.length > 30
            ? current.messages[0].text.slice(0, 30) + '...'
            : current.messages[0].text;
        current.timestamp = Date.now();
    }

    const s = { id: generateId(), title: 'Nuevo Chat', timestamp: Date.now(), messages: [] };
    chatSessions.push(s);
    currentSessionId = s.id;
    saveSessions();
    renderHistory();

    document.getElementById('chat-messages').innerHTML = renderWelcome();
    toggleSidebar();
}

function renderWelcome() {
    const name = document.querySelector('#sidebar h2').textContent.replace('Hola, ', '').replace('!', '');
    return '<div class="flex flex-col items-center text-center py-8" id="welcome-section">' +
        '  <div class="relative flex flex-col items-center mb-3">' +
        '    <div class="absolute -top-24 left-1/2 -translate-x-1/2 md:left-full md:-translate-x-10 md:top-0 w-64 p-5 bg-white rounded-2xl shadow-xl border border-outline-variant/20 text-left z-10">' +
        '      <p class="text-body-lg font-bold text-primary mb-1" id="greeting-bubble">Hola, ' + name + '!</p>' +
        '      <p class="text-body-md text-on-surface-variant">En que puedo ayudarte hoy?</p>' +
        '      <div class="absolute -bottom-2 left-1/2 -translate-x-1/2 md:left-0 md:-left-2 md:top-1/2 md:-translate-y-1/2 w-4 h-4 bg-white border-b border-l border-outline-variant/20 rotate-45 md:-rotate-45"></div>' +
        '    </div>' +
        '    <div class="floating-anim relative w-48 h-48 md:w-72 md:h-72">' +
        '      <img alt="Asistente Virtual" class="w-full h-full object-contain" src="https://lh3.googleusercontent.com/aida-public/AB6AXuA3JnTSxU3qagzTbEqeQpRnKwT5r2JjODuvITqGcD1G-0LC55hNZZ51X9aFyhkMd1GSSfWHBwX6b6duOTmUg1XsF3K2FoRGYPgM_QKka39DUMj3IOhFbfRpnNxs7RTT83Nfk_qReEiW7rX1kqJKPpvepD0Y5IXtZT_aOIVN9hhkNK0oM94gAI5zPCtbxzLamr8u2k0mGZAsQQ9IES-D4gps5J648jEU5XG8NM2zJYg7Q6BJnWT9Zfy7YQX6_zRC9xKWYiNPJFfSyo0">' +
        '    </div>' +
        '  </div>' +
        '</div>';
}

function loadSession(id) {
    const session = getSession(id);
    if (!session) return;
    currentSessionId = id;
    saveSessions();
    renderHistory();

    const container = document.getElementById('chat-messages');
    container.innerHTML = '';

    if (session.messages.length === 0) {
        container.innerHTML = renderWelcome();
        toggleSidebar();
        return;
    }

    session.messages.forEach(m => {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'flex ' + (m.isUser ? 'justify-end' : 'justify-start') + ' animate-in fade-in duration-200';
        const bubble = document.createElement('div');
        bubble.className = 'max-w-[75%] px-4 py-3 rounded-2xl text-body-md ' +
            (m.isUser ? 'bg-primary text-on-primary rounded-br-md' : 'bg-surface-container-high text-on-surface rounded-bl-md');
        bubble.innerHTML = m.text.replace(/\n/g, '<br>');
        msgDiv.appendChild(bubble);
        container.appendChild(msgDiv);
    });
    container.scrollTop = container.scrollHeight;

    toggleSidebar();
}

function showAccountsView() {
    document.querySelectorAll('#history-nav > .history-entry').forEach(el => el.classList.add('hidden'));
    document.getElementById('sidebar-links').classList.add('hidden');
    document.getElementById('soporte-view').classList.add('hidden');
    document.getElementById('accounts-view').classList.remove('hidden');
    loadAccounts();
}

function showSoporteView() {
    document.querySelectorAll('#history-nav > .history-entry').forEach(el => el.classList.add('hidden'));
    document.getElementById('sidebar-links').classList.add('hidden');
    document.getElementById('accounts-view').classList.add('hidden');
    document.getElementById('soporte-view').classList.remove('hidden');
}

function showHistoryView() {
    document.getElementById('accounts-view').classList.add('hidden');
    document.getElementById('soporte-view').classList.add('hidden');
    document.getElementById('sidebar-links').classList.remove('hidden');
    document.querySelectorAll('#history-nav > .history-entry').forEach(el => el.classList.remove('hidden'));
    renderHistory();
}

function loadAccounts() {
    const container = document.getElementById('accounts-content');
    container.innerHTML = '<div class="text-center py-8 text-on-surface-variant/50"><span class="material-symbols-outlined animate-spin inline-block text-[24px]">progress_activity</span></div>';

    const user = getSessionUser();
    const rutParam = (user && user.rut) ? '?rut=' + encodeURIComponent(user.rut) : '';
    fetch('/api/cuentas' + rutParam)
        .then(r => r.json())
        .then(data => {
            if (data.error) { container.innerHTML = '<p class="text-error text-center py-4">' + data.error + '</p>'; return; }

            const cr = data.cuenta_rut;
            const ca = data.cuenta_ahorros;
            const total = cr.saldo + ca.saldo;

            container.innerHTML =
                renderAccountCard(cr) +
                renderAccountCard(ca) +
                '<div class="pt-3 mt-3 border-t border-outline-variant/30 flex justify-between px-4 py-3 bg-surface-container rounded-xl">' +
                '  <span class="text-body-md font-semibold text-on-surface">Total en cuentas</span>' +
                '  <span class="text-body-md font-bold text-primary">$' + total.toLocaleString('es-CL') + '</span>' +
                '</div>';
        })
        .catch(err => {
            container.innerHTML = '<p class="text-error text-center py-4">Error al cargar cuentas: ' + err.message + '</p>';
        });
}

function renderAccountCard(acct) {
    const isRut = acct.tipo === 'CuentaRUT';
    const icon = isRut ? 'account_balance' : 'savings';
    const colorDot = acct.bloqueada ? 'bg-error' : 'bg-green-500';
    const statusText = acct.bloqueada ? 'Bloqueada' : 'Activa';

    return '<div class="bg-surface-container-low rounded-xl p-4 border border-outline-variant/20 space-y-2">' +
        '  <div class="flex items-center justify-between">' +
        '    <div class="flex items-center gap-2">' +
        '      <span class="material-symbols-outlined text-primary text-[22px]">' + icon + '</span>' +
        '      <span class="text-body-md font-bold text-on-surface">' + acct.tipo + '</span>' +
        '    </div>' +
        '    <span class="flex items-center gap-1.5 text-label-md font-medium text-on-surface-variant">' +
        '      <span class="w-2 h-2 rounded-full ' + colorDot + '"></span>' + statusText +
        '    </span>' +
        '  </div>' +
        '  <p class="text-body-md text-on-surface-variant/70">N° ' + acct.numero.slice(-4).padStart(acct.numero.length, '*') + '</p>' +
        '  <div class="flex justify-between items-end pt-1">' +
        '    <div>' +
        '      <p class="text-label-md text-on-surface-variant/60">Saldo</p>' +
        '      <p class="text-headline-sm font-bold text-on-surface">$' + acct.saldo.toLocaleString('es-CL') + '</p>' +
        '    </div>' +
        '    <div class="text-right">' +
        '      <p class="text-label-md text-on-surface-variant/60">Disponible</p>' +
        '      <p class="text-body-md font-semibold text-on-surface-variant">$' + acct.disponible.toLocaleString('es-CL') + '</p>' +
        '    </div>' +
        '  </div>' +
        (acct.tasa_interes ? '  <p class="text-label-md text-on-surface-variant/60 pt-1">Tasa interés: ' + acct.tasa_interes + '% anual</p>' : '') +
        '</div>';
}

function openLogout() {
    document.getElementById('logout-modal-overlay').classList.remove('hidden');
    document.getElementById('logout-modal-overlay').classList.add('flex');
}

function closeLogout() {
    document.getElementById('logout-modal-overlay').classList.add('hidden');
    document.getElementById('logout-modal-overlay').classList.remove('flex');
}

function confirmLogout() {
    clearSession();
    updateUserGreeting('');
    updateChatState();
    closeLogout();

    var container = document.getElementById('chat-messages');
    container.innerHTML = renderWelcome();

    const current = getSession(currentSessionId);
    if (current && current.messages.length > 0) {
        current.title = current.messages[0].text.length > 30
            ? current.messages[0].text.slice(0, 30) + '...'
            : current.messages[0].text;
        current.timestamp = Date.now();
        saveSessions();
    }
}

function logout() {
    openLogout();
}

function typewriter(bubble, text, speed = 20) {
    let i = 0;
    bubble.classList.add('typewriter-cursor');
    function step() {
        if (i < text.length) {
            const chunk = text.slice(i, i + 3);
            const escaped = chunk.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
            if (i === 0) bubble.innerHTML = escaped;
            else bubble.innerHTML += escaped;
            i += 3;
            const container = document.getElementById('chat-messages');
            container.scrollTop = container.scrollHeight;
            setTimeout(step, speed);
        } else {
            bubble.classList.remove('typewriter-cursor');
        }
    }
    step();
}

function addMessage(text, isUser) {
    ensureCurrentSession();
    const session = getSession(currentSessionId);

    session.messages.push({ text, isUser, time: Date.now() });
    if (!isUser) {
        const firstUserMsg = session.messages.find(m => m.isUser);
        if (firstUserMsg && session.title === 'Nuevo Chat') {
            session.title = firstUserMsg.text.length > 30
                ? firstUserMsg.text.slice(0, 30) + '...'
                : firstUserMsg.text;
        }
        session.timestamp = Date.now();
    }
    saveSessions();
    renderHistory();

    const container = document.getElementById('chat-messages');
    const welcome = document.getElementById('welcome-section');
    if (welcome) welcome.remove();

    const msgDiv = document.createElement('div');
    msgDiv.className = 'flex ' + (isUser ? 'justify-end' : 'justify-start') + ' animate-in fade-in slide-in-from-bottom-2 duration-300';

    const bubble = document.createElement('div');
    bubble.className = 'max-w-[75%] px-4 py-3 rounded-2xl text-body-md ' +
        (isUser
            ? 'bg-primary text-on-primary rounded-br-md'
            : 'bg-surface-container-high text-on-surface rounded-bl-md');
    bubble.innerHTML = text.replace(/\n/g, '<br>');

    msgDiv.appendChild(bubble);
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;

    if (!isUser && text.length > 10) {
        const raw = text;
        bubble.innerHTML = '';
        typewriter(bubble, raw, 15);
    }
}

function sendMessage() {
    if (!isLoggedIn()) { openLogin(); return; }
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    addMessage(msg, true);
    input.value = '';

    const btn = document.getElementById('send-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-symbols-outlined animate-spin text-[24px]">progress_activity</span>';
    btn.style.transform = 'scale(0.9)';
    setTimeout(() => btn.style.transform = '', 150);

    sendToServer(msg).then(response => {
        addMessage(response, false);
    }).catch(err => {
        addMessage('Error de conexion con el servidor: ' + err.message, false);
    }).finally(() => {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined text-[24px]">send</span>';
    });
}

function quickMessage(msg) {
    if (!isLoggedIn()) { openLogin(); return; }
    const input = document.getElementById('chat-input');
    input.value = msg;
    input.focus();
}

document.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        if (!document.getElementById('login-modal-overlay').classList.contains('hidden')) {
            handleLogin();
        } else if (!document.getElementById('register-modal-overlay').classList.contains('hidden')) {
            handleRegister();
        } else {
            sendMessage();
        }
    }
});

// ─── Inicializacion ──────────────────────────────────────────
const user = getSessionUser();
if (user) {
    updateUserGreeting(user.name);
    updateChatState();
} else {
    updateUserGreeting('');
    updateChatState();
    setTimeout(() => openLogin(), 200);
}

renderHistory();
if (currentSessionId) {
    const s = getSession(currentSessionId);
    if (s && s.messages.length > 0) loadSession(currentSessionId);
}
ensureCurrentSession();
