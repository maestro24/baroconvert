// 바로변환 공용 — 테마
const PREF_KEY = 'baro_prefs';
export const prefs = JSON.parse(localStorage.getItem(PREF_KEY) || '{}');
if (!prefs.theme) prefs.theme = window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';

export function initTheme() {
  document.documentElement.dataset.theme = prefs.theme;
  const btn = document.getElementById('btn-theme');
  if (!btn) return;
  btn.textContent = prefs.theme === 'dark' ? '☀' : '☾';
  btn.addEventListener('click', () => {
    prefs.theme = prefs.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
    document.documentElement.dataset.theme = prefs.theme;
    btn.textContent = prefs.theme === 'dark' ? '☀' : '☾';
  });
}
