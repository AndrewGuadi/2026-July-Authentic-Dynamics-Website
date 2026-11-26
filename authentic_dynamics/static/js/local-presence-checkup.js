(() => {
  const root = document.querySelector('[data-local-presence-checkup]');
  if (!root) return;

  const checks = [...root.querySelectorAll('[data-presence-check]')];
  const businessType = root.querySelector('#presence-business-type');
  const typeGuidance = root.querySelector('#presence-type-guidance');
  const locationCopy = root.querySelector('[data-presence-location-copy]');
  const heading = root.querySelector('#presence-summary-heading');
  const progressCopy = root.querySelector('#presence-progress-copy');
  const progress = root.querySelector('[role="progressbar"]');
  const progressBar = root.querySelector('[data-presence-progress-bar]');
  const actions = root.querySelector('[data-presence-actions]');
  const enhanced = root.querySelector('[data-presence-enhanced]');
  const fallback = document.querySelector('[data-presence-fallback]');
  const remember = root.querySelector('#presence-remember');
  const status = root.querySelector('#presence-status');
  const download = root.querySelector('#presence-download');
  const print = root.querySelector('#presence-print');
  const reset = root.querySelector('#presence-reset');
  const storageKey = 'authentic-dynamics.local-presence-checkup.v1';
  const total = checks.length;

  const locationGuidance = {
    storefront: {
      note: 'If customers visit a staffed location, show its real address and keep any customer-facing hours accurate.',
      item: 'If customers visit a staffed location, show its real address and keep any customer-facing hours accurate.'
    },
    'service-area': {
      note: 'If customers do not visit your work address, hide it and list only the areas you genuinely serve. Do not use an unstaffed virtual office.',
      item: 'If customers do not visit your base, hide that address and list only the areas you genuinely serve.'
    },
    hybrid: {
      note: 'Show your staffed customer-facing location and add realistic service areas for work you perform elsewhere.',
      item: 'Show your staffed customer-facing location and set service areas for work you actually perform elsewhere.'
    }
  };

  function setStatus(message) {
    status.textContent = message;
  }

  function updateLocationGuidance() {
    const guidance = locationGuidance[businessType.value] || locationGuidance.storefront;
    typeGuidance.textContent = guidance.note;
    locationCopy.textContent = guidance.item;
  }

  function remainingItems() {
    return checks.filter(check => !check.checked).map(check => ({
      title: check.closest('[data-presence-item]').querySelector('strong').textContent.trim(),
      action: check.closest('[data-presence-item]').dataset.action
    }));
  }

  function render() {
    for (const check of checks) {
      check.closest('[data-presence-item]').classList.toggle('is-checked', check.checked);
    }
    const ready = checks.filter(check => check.checked).length;
    const remaining = remainingItems();
    heading.textContent = ready + ' of ' + total + ' checks marked ready';
    progress.setAttribute('aria-valuenow', String(ready));
    progressBar.style.width = (total ? ready / total * 100 : 0) + '%';
    progressCopy.textContent = remaining.length
      ? 'Start with: ' + remaining[0].title
      : 'All checks are marked ready. Revisit after a change to your hours, services, service area or website.';
    actions.replaceChildren();
    if (remaining.length) {
      for (const item of remaining.slice(0, 3)) {
        const li = document.createElement('li');
        const title = document.createElement('strong');
        const detail = document.createElement('p');
        title.textContent = item.title;
        detail.textContent = item.action;
        li.append(title, detail);
        actions.append(li);
      }
      if (remaining.length > 3) {
        const more = document.createElement('li');
        more.textContent = (remaining.length - 3) + ' more actions are included in the download.';
        actions.append(more);
      }
    } else {
      const li = document.createElement('li');
      li.textContent = 'All checks are marked ready. Keep this list and revisit it when your business details change.';
      actions.append(li);
    }
    download.disabled = false;
  }

  function saveIfRequested() {
    if (!remember.checked) return;
    try {
      const state = {
        version: 1,
        businessType: businessType.value,
        checks: Object.fromEntries(checks.map(check => [check.value, check.checked]))
      };
      localStorage.setItem(storageKey, JSON.stringify(state));
      setStatus('Progress saved on this device. No business or customer details are stored.');
    } catch {
      setStatus('This browser blocked local saving. The checkup still works until you leave the page.');
    }
  }

  function removeSavedProgress() {
    try {
      localStorage.removeItem(storageKey);
      return true;
    } catch {
      setStatus('This browser did not allow saved progress to be removed.');
      return false;
    }
  }

  function reportText() {
    const ready = checks.filter(check => check.checked).length;
    const remaining = remainingItems();
    const date = new Intl.DateTimeFormat('en-US', {dateStyle: 'long'}).format(new Date());
    const lines = [
      'AUTHENTIC DYNAMICS — LOCAL PRESENCE CHECKUP',
      'Prepared: ' + date,
      'Business type: ' + businessType.options[businessType.selectedIndex].text,
      'Checks marked ready: ' + ready + '/' + total,
      '',
      'NEXT ACTIONS',
      ...(remaining.length ? remaining.flatMap((item, index) => [
        (index + 1) + '. ' + item.title,
        '   ' + item.action
      ]) : ['All checks are marked ready. Revisit after business details change.']),
      '',
      'This is a manual checklist, not a Google score, ranking test or guarantee.',
      'Google Business Profile guidelines: https://support.google.com/business/answer/3038177?hl=en'
    ];
    return lines.join('\n');
  }

  for (const check of checks) {
    check.addEventListener('change', () => {
      render();
      saveIfRequested();
    });
  }

  businessType.addEventListener('change', () => {
    updateLocationGuidance();
    render();
    saveIfRequested();
  });

  remember.addEventListener('change', () => {
    if (remember.checked) {
      saveIfRequested();
    } else if (removeSavedProgress()) {
      setStatus('Saved progress removed. Your current selections remain until you leave this page.');
    }
  });

  download.addEventListener('click', () => {
    const blob = new Blob([reportText()], {type: 'text/plain;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'local-presence-checkup-' + new Date().toLocaleDateString('en-CA') + '.txt';
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    setStatus('Your action list was prepared for download. Review each item before making profile changes.');
  });

  print.addEventListener('click', () => window.print());

  reset.addEventListener('click', () => {
    checks.forEach(check => { check.checked = false; });
    businessType.value = 'storefront';
    remember.checked = false;
    removeSavedProgress();
    updateLocationGuidance();
    render();
    setStatus('Checkup reset. Nothing was sent or stored.');
  });

  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (saved?.version === 1 && saved.checks && typeof saved.checks === 'object') {
      if (locationGuidance[saved.businessType]) businessType.value = saved.businessType;
      checks.forEach(check => { check.checked = saved.checks[check.value] === true; });
      remember.checked = true;
      setStatus('Your saved checkup was restored from this device.');
    }
  } catch {
    setStatus('Saved progress is unavailable in this browser. You can still use and download the checkup.');
  }

  updateLocationGuidance();
  render();
  enhanced.hidden = false;
  fallback.hidden = true;
})();