/* A card moves only after server confirmation. Native forms work without JS. */
(() => {
  const board = document.querySelector('.hub-board');
  if (!board) return;
  const status = document.querySelector('#board-status');
  let dragged = null;
  let saving = false;
  const clearTargets = () => board.querySelectorAll('.is-drop-target').forEach(lane => lane.classList.remove('is-drop-target'));
  async function move(card, lane, initiator) {
    if (saving || !lane) return;
    const originalLane = card.closest('.hub-lane');
    const form = card.querySelector('form');
    const select = form.querySelector('select');
    if (lane === originalLane) {
      select.value = originalLane.dataset.lane;
      status.textContent = 'This card is already in that column.';
      return;
    }
    const data = new FormData(form);
    data.set(select.name, lane.dataset.lane);
    const controls = [...board.querySelectorAll('select, button')].map(control => [control, control.disabled]);
    saving = true;
    controls.forEach(([control]) => { control.disabled = true; });
    card.setAttribute('aria-busy', 'true');
    clearTargets();
    status.textContent = 'Saving move… The card stays in its current column until confirmed.';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: data, credentials: 'same-origin',
        headers: {Accept: 'application/json'}, signal: controller.signal
      });
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('Save failed');
      const result = await response.json();
      if (!result.ok) throw new Error('Save failed');
      lane.append(card);
      select.value = lane.dataset.lane;
      card.classList.remove('move-confirmed');
      card.classList.add('move-confirmed');
      status.textContent = `Move saved. Now in ${lane.querySelector('h2').textContent}.`;
    } catch {
      select.value = originalLane.dataset.lane;
      status.textContent = 'The move was not confirmed. The card stays here. Reload to check the saved position and your login before retrying.';
    } finally {
      clearTimeout(timeout);
      card.removeAttribute('aria-busy');
      controls.forEach(([control, disabled]) => { control.disabled = disabled; });
      saving = false;
      dragged = null;
      if (initiator?.isConnected) initiator.focus({preventScroll: true});
    }
  }
  board.addEventListener('submit', event => {
    const form = event.target.closest('.hub-card form');
    if (!form) return;
    event.preventDefault();
    const selected = form.querySelector('select').value;
    const lane = [...board.querySelectorAll('.hub-lane')].find(item => item.dataset.lane === selected);
    move(form.closest('.hub-card'), lane, event.submitter || form.querySelector('select'));
  });
  board.addEventListener('dragstart', event => {
    const card = event.target.closest('.hub-card[draggable]');
    if (!card || saving) { event.preventDefault(); return; }
    dragged = card;
    event.dataTransfer.setData('text/plain', card.dataset.id);
    event.dataTransfer.effectAllowed = 'move';
  });
  board.addEventListener('dragend', () => { dragged = null; clearTargets(); });
  board.addEventListener('dragover', event => {
    const lane = event.target.closest('.hub-lane');
    if (dragged && !saving && lane) {
      event.preventDefault();
      clearTargets();
      lane.classList.add('is-drop-target');
    }
  });
  board.addEventListener('drop', event => {
    const lane = event.target.closest('.hub-lane');
    if (!lane || !dragged || saving) return;
    event.preventDefault();
    move(dragged, lane);
  });
  board.addEventListener('animationend', event => event.target.classList.remove('move-confirmed'));
})();
