(() => {
  const byId = (id) => document.getElementById(`photo-menu-${id}`);
  const sample = JSON.parse(byId('sample').textContent);
  const preview = byId('preview');
  const review = byId('review');
  const heading = byId('preview-heading');
  const editor = byId('editor');
  const fields = byId('fields');
  const edit = byId('edit');
  const reset = byId('reset');
  const status = byId('status');
  const form = byId('upload');
  let menu = structuredClone(sample);

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function renderPreview() {
    const masthead = element('header', '', 'photo-menu-masthead');
    if (menu.name) masthead.append(element('p', 'Menu'));
    masthead.append(element('h3', menu.name || 'Menu'));

    const nav = element('nav', '', 'photo-menu-nav');
    nav.setAttribute('aria-label', 'Menu sections');
    const sections = menu.sections.map((section, index) => {
      const id = `photo-menu-section-${index + 1}`;
      const title = section.name || 'Untitled section';
      const link = element('a', title);
      link.href = `#${id}`;
      nav.append(link);

      const category = element('section', '', 'photo-menu-category');
      category.id = id;
      category.append(element('h4', title));
      if (section.note) category.append(element('p', section.note));
      const items = element('ul', '', 'photo-menu-items');
      for (const item of section.items) {
        const row = element('li', '', 'photo-menu-item');
        const description = element('div');
        description.append(element('h5', item.name || 'Untitled item'));
        if (item.description) description.append(element('p', item.description));
        row.append(description);
        const prices = element('ul', '', 'photo-menu-prices');
        prices.setAttribute('aria-label', 'Prices');
        for (const price of item.prices.filter(({ text }) => text)) {
          const quote = element('li');
          if (price.label) quote.append(element('span', price.label), ' ');
          quote.append(price.text);
          prices.append(quote);
        }
        if (prices.childElementCount) row.append(prices);
        items.append(row);
      }
      category.append(items);
      return category;
    });

    preview.replaceChildren(masthead);
    if (sections.length) preview.append(nav, ...sections);
    if (menu.notes.length) {
      const notes = element('footer', '', 'photo-menu-notes');
      notes.append(...menu.notes.map((note) => element('p', note)));
      preview.append(notes);
    }
  }

  function renderReview() {
    const flagged = menu.sections.flatMap(({ items }) => items).filter(({ review_note }) => review_note);
    review.hidden = !menu.warnings.length && !flagged.length;
    review.replaceChildren();
    if (review.hidden) return;
    review.append(element('p', 'Check against the photo'));
    if (menu.warnings.length) {
      const warnings = element('ul');
      warnings.append(...menu.warnings.map((warning) => element('li', warning)));
      review.append(warnings);
    }
    if (flagged.length) {
      const list = element('ul');
      list.append(...flagged.map((item) => element('li', `${item.name || 'Untitled item'} — ${item.review_note}`)));
      review.append(list);
    }
  }

  function field(label, value, maxLength, update, multiline = false) {
    const wrapper = element('label', label);
    const control = element(multiline ? 'textarea' : 'input');
    control.value = value ?? '';
    control.maxLength = maxLength;
    if (multiline) control.rows = 2;
    control.addEventListener('input', () => {
      update(control.value.trim());
      reset.hidden = false;
      renderPreview();
      renderReview();
    });
    wrapper.append(control);
    return wrapper;
  }

  function action(label, change) {
    const button = element('button', label, 'button photo-menu-secondary');
    button.type = 'button';
    button.addEventListener('click', () => {
      const oldButtons = [...fields.querySelectorAll('button')];
      const index = oldButtons.indexOf(button);
      change();
      reset.hidden = false;
      renderEditor();
      renderPreview();
      renderReview();
      const nextButtons = fields.querySelectorAll('button');
      (nextButtons[Math.min(index, nextButtons.length - 1)] || edit).focus();
    });
    return button;
  }

  function group(label, className = 'photo-menu-fields') {
    const container = element('fieldset', '', className);
    container.append(element('legend', label));
    return container;
  }

  function renderItem(item, index, section) {
    const entry = group(`Item ${index + 1}`);
    entry.append(
      field('Item name', item.name, 150, (value) => { item.name = value; }),
      field('Description', item.description, 600, (value) => { item.description = value; }, true),
    );
    if (item.review_note) {
      entry.append(element('p', item.review_note, 'photo-menu-flag'),
        action('Mark item reviewed', () => { item.review_note = null; }));
    }
    for (const [priceIndex, price] of item.prices.entries()) {
      const quote = group(`Price ${priceIndex + 1}`, 'photo-menu-fields photo-menu-price-fields');
      quote.append(
        field('Size or option', price.label, 80, (value) => { price.label = value; }),
        field('Printed price', price.text, 65, (value) => { price.text = value; }),
        action('Remove price', () => item.prices.splice(priceIndex, 1)),
      );
      entry.append(quote);
    }
    entry.append(action('Add price', () => item.prices.push({ label: '', text: '' })),
      action('Remove item', () => section.items.splice(index, 1)));
    return entry;
  }

  function renderEditor() {
    const container = element('div', '', 'photo-menu-fields');
    container.append(
      field('Menu name', menu.name, 140, (value) => { menu.name = value; }),
      field('Menu notes (one per line)', menu.notes.join('\n'), 6000, (value) => {
        menu.notes = value.split('\n').map((note) => note.trim()).filter(Boolean);
      }, true),
    );
    for (const [index, section] of menu.sections.entries()) {
      const category = group(`Section ${index + 1}`);
      category.append(
        field('Section name', section.name, 120, (value) => { section.name = value; }),
        field('Section note', section.note, 500, (value) => { section.note = value; }, true),
        ...section.items.map((item, itemIndex) => renderItem(item, itemIndex, section)),
        action('Add item', () => section.items.push({ name: '', description: '', prices: [] })),
        action('Remove section', () => menu.sections.splice(index, 1)),
      );
      container.append(category);
    }
    container.append(action('Add section', () => menu.sections.push({ name: '', note: '', items: [] })));
    fields.replaceChildren(container);
  }

  function setEditing(open) {
    editor.hidden = !open;
    edit.setAttribute('aria-expanded', String(open));
    edit.textContent = open ? 'Close editor' : 'Edit menu';
    if (open) {
      renderEditor();
      fields.querySelector('input').focus();
    }
  }

  function setStatus(message, isError = false) {
    status.hidden = !message;
    status.classList.toggle('is-error', isError);
    status.textContent = message;
  }

  edit.addEventListener('click', () => setEditing(editor.hidden));
  reset.addEventListener('click', () => {
    menu = structuredClone(sample);
    reset.hidden = true;
    heading.textContent = 'Sample menu';
    if (!editor.hidden) renderEditor();
    renderPreview();
    renderReview();
    setStatus('Sample menu restored.');
    edit.focus();
  });
  byId('edit-actions').hidden = false;

  if (!form) return;
  const camera = byId('camera');
  const file = byId('file');
  const cameraButton = byId('camera-button');
  const fileButton = byId('file-button');
  const source = byId('source-photo');
  const image = byId('image');
  const filename = byId('filename');
  const scan = form.querySelector('[type=submit]');
  let selected = null;
  let imageUrl = '';
  let busy = false;

  function selectPhoto(input) {
    const chosen = input.files[0];
    input.value = '';
    if (!chosen || busy) return;

    if (imageUrl) URL.revokeObjectURL(imageUrl);
    imageUrl = '';
    image.removeAttribute('src');
    selected = null;
    source.hidden = true;
    source.open = false;
    filename.hidden = true;
    scan.disabled = true;

    if (chosen.size > Number(form.dataset.maxBytes)) {
      setStatus('Choose a photo that is 12 MB or smaller.', true);
      return;
    }
    selected = chosen;
    imageUrl = URL.createObjectURL(chosen);
    image.src = imageUrl;
    filename.textContent = chosen.name;
    filename.hidden = false;
    source.hidden = false;
    scan.disabled = false;
    setStatus('');
  }

  function setBusy(value) {
    busy = value;
    for (const button of [cameraButton, fileButton, scan, edit, reset]) button.disabled = value;
    editor.inert = value;
    form.setAttribute('aria-busy', String(value));
    scan.textContent = value ? 'Reading menu…' : 'Read menu';
  }

  cameraButton.addEventListener('click', () => camera.click());
  fileButton.addEventListener('click', () => file.click());
  camera.addEventListener('change', () => selectPhoto(camera));
  file.addEventListener('change', () => selectPhoto(file));
  form.hidden = false;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!selected || busy) return;
    if (!reset.hidden && !window.confirm('Replace the current preview with this photo?')) return;

    const body = new FormData(form);
    body.append('photo', selected);
    setBusy(true);
    setStatus('Reading your menu. This can take a moment.');
    try {
      const response = await fetch(form.action, { method: 'POST', body, headers: { Accept: 'application/json' } });
      if (!response.headers.get('content-type')?.includes('application/json')) {
        const message = response.status === 413 ? 'Choose a photo that is 12 MB or smaller.' :
          response.status === 400 ? 'Reload this page and select your photo again.' :
          'The scanner is unavailable. Try again shortly.';
        throw new Error(message);
      }
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'The menu could not be read. Try another photo.');

      menu = result.menu;
      heading.textContent = 'Imported menu preview';
      reset.hidden = false;
      setEditing(false);
      renderPreview();
      renderReview();
      source.open = true;
      setStatus('Menu ready. Check the items and prices before using it.');
      heading.focus();
    } catch (error) {
      setStatus(error instanceof TypeError ? 'The connection dropped. Try reading the photo again.' : error.message, true);
    } finally {
      setBusy(false);
    }
  });
})();
