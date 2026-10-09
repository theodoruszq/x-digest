(() => {
  const root = document.documentElement;
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} },
  };

  /* theme: follows the OS unless overridden */
  const mq = matchMedia('(prefers-color-scheme: dark)');
  const effective = () => root.dataset.theme || (mq.matches ? 'dark' : 'light');
  const themeBtn = document.querySelector('[data-toggle-theme]');
  const themeLabel = document.querySelector('[data-theme-label]');
  const syncTheme = () => {
    const dark = effective() === 'dark';
    if (themeLabel) themeLabel.textContent = dark ? 'Light' : 'Dark';
    themeBtn?.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
  };
  themeBtn?.addEventListener('click', () => {
    const next = effective() === 'dark' ? 'light' : 'dark';
    if (next === (mq.matches ? 'dark' : 'light')) { delete root.dataset.theme; store.set('xdigest.theme', null); }
    else { root.dataset.theme = next; store.set('xdigest.theme', next); }
    syncTheme();
  });
  mq.addEventListener?.('change', syncTheme);
  syncTheme();

  /* post timestamps: UTC in the HTML (no-JS fallback), viewer's local time via Intl */
  try {
    const short = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
    const full = new Intl.DateTimeFormat(undefined, { dateStyle: 'full', timeStyle: 'long' });
    document.querySelectorAll('time.ts[datetime]').forEach((el) => {
      const d = new Date(el.getAttribute('datetime'));
      if (isNaN(d)) return;
      el.textContent = short.format(d);
      el.title = full.format(d);
    });
  } catch { /* keep the UTC fallback */ }

  /* Chinese glosses & notes: one toggle, remembered */
  const zhBtn = document.querySelector('[data-toggle-zh]');
  const zhLabel = document.querySelector('[data-zh-label]');
  const syncZh = () => {
    const on = root.classList.contains('show-zh');
    zhBtn?.setAttribute('aria-pressed', String(on));
    if (zhLabel) zhLabel.textContent = on ? 'Hide Chinese glosses & notes' : 'Show Chinese glosses & notes';
  };
  zhBtn?.addEventListener('click', () => {
    root.classList.toggle('show-zh');
    store.set('xdigest.zh', root.classList.contains('show-zh') ? '1' : null);
    syncZh();
  });
  syncZh();
})();
