const tabs = [...document.querySelectorAll('[role="tab"][data-language]')];
function activate(tab) {
  tabs.forEach(item => {
    const selected = item === tab;
    item.setAttribute('aria-selected', String(selected));
    item.tabIndex = selected ? 0 : -1;
    document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
  });
  document.querySelectorAll('input[name="language"], select[name="language"]').forEach(input => { input.value = tab.dataset.language; });
  const url = new URL(location.href);
  url.searchParams.set('language', tab.dataset.language);
  history.replaceState(null, '', url);
  // Keep the selected language when moving to another date or archive page.
  document.querySelectorAll('.calendar-date-nav a, .calendar-pagination a, .calendar-archive-filters a, .calendar-table th a').forEach(link => {
    const target = new URL(link.href); target.searchParams.set('language', tab.dataset.language); link.href = target;
  });
}
tabs.forEach((tab, i) => {
  tab.tabIndex = tab.getAttribute('aria-selected') === 'true' ? 0 : -1;
  tab.addEventListener('click', event => { event.preventDefault(); activate(tab); });
  tab.addEventListener('keydown', event => {
    if (event.key === ' ' || event.key === 'Enter') { event.preventDefault(); activate(tab); return; }
    const target = event.key === 'ArrowRight' ? tabs[(i + 1) % tabs.length]
      : event.key === 'ArrowLeft' ? tabs[(i - 1 + tabs.length) % tabs.length]
      : event.key === 'Home' ? tabs[0] : event.key === 'End' ? tabs[tabs.length - 1] : null;
    if (target) { event.preventDefault(); target.focus(); }
  });
});
const root = document.querySelector('[data-calendar-today]');
function refreshToday() {
  if (!root || new URL(location.href).searchParams.has('date') || document.visibilityState !== 'visible') return;
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
  const value = type => parts.find(part => part.type === type).value;
  if (`${value('year')}-${value('month')}-${value('day')}` !== root.dataset.calendarToday) location.reload();
}
if (root) {
  setInterval(refreshToday, 60000);
  document.addEventListener('visibilitychange', refreshToday);
  window.addEventListener('pageshow', event => { if (event.persisted) refreshToday(); });
}
