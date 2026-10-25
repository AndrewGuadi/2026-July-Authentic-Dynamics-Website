(() => {
  const controls = document.querySelector('[data-tool-filters]');
  if (!controls) return;
  const cards = [...document.querySelectorAll('[data-tool-job]')];
  const count = document.querySelector('[data-tool-count]');
  controls.hidden = false;
  controls.addEventListener('click', (event) => {
    const button = event.target.closest('[data-tool-filter]');
    if (!button) return;
    const job = button.dataset.toolFilter;
    for (const option of controls.querySelectorAll('button')) {
      option.setAttribute('aria-pressed', String(option === button));
    }
    let visible = 0;
    for (const card of cards) {
      card.hidden = job !== 'all' && !card.dataset.toolJob.split(' ').includes(job);
      if (!card.hidden) visible += 1;
    }
    count.textContent = `${visible} ${visible === 1 ? 'tool' : 'tools'} · ${button.textContent}`;
  });
})();
