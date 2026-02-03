// Minimal auth UI (ported from predecessor)
(function () {
  function $(id) { return document.getElementById(id); }

  let authMode = 'login'; // login | register

  window.showAuthModal = function () {
    const modal = $('auth-modal');
    if (modal) modal.classList.remove('hidden');
  };

  window.hideAuthModal = function () {
    const modal = $('auth-modal');
    if (modal) modal.classList.add('hidden');
  };

  window.switchAuthMode = function (mode) {
    authMode = mode;
    const tabLogin = $('tab-login');
    const tabReg = $('tab-register');
    const btn = $('btn-auth-submit');
    const err = $('auth-error');
    if (tabLogin && tabReg) {
      tabLogin.className = mode === 'login'
        ? 'flex-1 py-2 rounded text-sm font-medium bg-indigo-600 text-white'
        : 'flex-1 py-2 rounded text-sm font-medium text-slate-300 hover:text-white';
      tabReg.className = mode === 'register'
        ? 'flex-1 py-2 rounded text-sm font-medium bg-indigo-600 text-white'
        : 'flex-1 py-2 rounded text-sm font-medium text-slate-300 hover:text-white';
    }
    if (btn) btn.textContent = mode === 'login' ? '登录' : '注册';
    if (err) err.textContent = '';
  };

  window.submitAuth = async function () {
    const u = $('auth-username')?.value || '';
    const p = $('auth-password')?.value || '';
    const errEl = $('auth-error');
    if (!u || !p) {
      if (errEl) errEl.textContent = '请输入用户名和密码';
      return;
    }
    if (errEl) errEl.textContent = '正在处理...';

    try {
      if (authMode === 'login') {
        const formData = new FormData();
        formData.append('username', u);
        formData.append('password', p);
        const r = await fetch('/token', { method: 'POST', body: formData });
        if (!r.ok) throw new Error('用户名或密码错误');
        const data = await r.json();
        localStorage.setItem('access_token', data.access_token);
        window.hideAuthModal();
        location.reload();
      } else {
        const r = await fetch('/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: u, password: p })
        });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(d.detail || d.error || '注册失败');
        alert('注册成功，请登录');
        window.switchAuthMode('login');
      }
    } catch (e) {
      if (errEl) errEl.textContent = e.message || String(e);
    }
  };

  window.checkAuth = async function () {
    const token = localStorage.getItem('access_token');
    if (!token) {
      window.showAuthModal();
      return false;
    }
    try {
      const r = await fetch('/users/me', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (!r.ok) throw new Error('Session expired');
      return true;
    } catch {
      localStorage.removeItem('access_token');
      window.showAuthModal();
      return false;
    }
  };

  window.logout = function () {
    localStorage.removeItem('access_token');
    location.reload();
  };

  // Auto-check once loaded
  window.addEventListener('load', () => {
    if (window.ROX_SKIP_AUTH_ON_LOAD) return;
    window.checkAuth().catch(() => {});
  });
})();

