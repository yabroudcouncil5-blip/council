/* Only the lookup result refreshes; no cookies or form resubmission needed. */
(() => {
  let pending = false;
  async function refresh() {
    const root = document.querySelector('.tracking-result[data-reference]');
    if (!root || document.hidden || pending || root.contains(document.activeElement)) return;
    pending = true;
    try {
      const url = new URL('/complaints/track/', window.location.origin);
      url.searchParams.set('reference', root.dataset.reference);
      url.searchParams.set('partial', '1');
      const response = await fetch(url, { cache: 'no-store', credentials: 'omit' });
      if (!response.ok) return;
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const updated = page.querySelector('.tracking-result');
      if (updated && updated.outerHTML !== root.outerHTML) root.replaceWith(updated);
    } catch (_) { /* Keep the current history when the connection is slow. */ }
    finally { pending = false; }
  }
  setInterval(refresh, 30000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
})();
