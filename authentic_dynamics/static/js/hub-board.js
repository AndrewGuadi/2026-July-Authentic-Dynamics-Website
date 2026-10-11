/* Server-confirmed board moves; the form remains available for keyboard users. */
(() => {
  const board = document.querySelector('.hub-board');
  if (!board) return;
  let dragged = null;
  let saving = false;
  const status = document.querySelector('#board-status');
  board.addEventListener('dragstart', (event) => {
    const card = event.target.closest('.hub-card[draggable]');
    if (!card || saving) { event.preventDefault(); return; }
    dragged = card;
    event.dataTransfer.setData('text/plain', card.dataset.id);
    event.dataTransfer.effectAllowed = 'move';
  });
  board.addEventListener('dragend', () => { dragged = null; });
  board.addEventListener('dragover', (event) => {
    if (dragged && !saving && event.target.closest('.hub-lane')) event.preventDefault();
  });
  board.addEventListener('drop', async (event) => {
    const lane = event.target.closest('.hub-lane');
    if (!lane || !dragged || saving) return;
    event.preventDefault();
    const card = dragged;
    const form = card.querySelector('form');
    const select = form.querySelector('select');
    const data = new FormData(form);
    data.set(select.name, lane.dataset.lane);
    saving = true;
    status.textContent = 'Saving move…';
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: data, credentials: 'same-origin',
        headers: {Accept: 'application/json'}
      });
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
        throw new Error('Save failed');
      }
      const result = await response.json();
      if (!result.ok) throw new Error('Save failed');
      lane.append(card);
      select.value = lane.dataset.lane;
      status.textContent = 'Move saved.';
    } catch {
      status.textContent = 'The move was not confirmed. Reload to check the saved position and your login, then try again.';
    } finally { saving = false; dragged = null; }
  });
})();
