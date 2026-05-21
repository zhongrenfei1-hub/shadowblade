// Loads the shared sidebar fragment and marks the active route.
// Lets every page stay a single, self-contained HTML file while reusing the shell.

(async function bootShell() {
  const slot = document.querySelector('[data-shell="sidebar"]');
  if (!slot) return;
  try {
    const res = await fetch('components/shell.html', { cache: 'no-store' });
    slot.outerHTML = await res.text();
  } catch (err) {
    console.warn('[shadowblade] shell load failed', err);
    return;
  }
  const route = document.body.dataset.route;
  if (!route) return;
  document
    .querySelectorAll(`.sb-nav__item[data-route="${route}"]`)
    .forEach((el) => el.classList.add('sb-nav__item--active'));
})();

document.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    const search = document.querySelector('.sb-topbar__search input');
    if (search) search.focus();
  }
});
