'use strict';

const form = document.querySelector('#review-request-form');

if (form) {
  const business = form.querySelector('#review-business');
  const reviewLink = form.querySelector('#review-link');
  const customer = form.querySelector('#review-customer');
  const service = form.querySelector('#review-service');
  const tone = form.querySelector('#review-tone');
  const remember = form.querySelector('#review-remember');
  const subjectWrap = document.querySelector('#review-subject-wrap');
  const subject = document.querySelector('#review-subject');
  const message = document.querySelector('#review-message');
  const count = document.querySelector('#review-count');
  const status = document.querySelector('#review-status');
  const copy = document.querySelector('#review-copy');
  const clear = document.querySelector('#review-clear');
  const storageKey = 'authentic-dynamics.review-request.v1';

  function chosenChannel() {
    return form.querySelector('[name="channel"]:checked').value;
  }

  function setStatus(text, isError = false) {
    status.textContent = text;
    status.classList.toggle('is-error', isError);
  }

  function validateLink() {
    reviewLink.setCustomValidity('');
    if (!reviewLink.value) return;
    try {
      const url = new URL(reviewLink.value);
      if (url.protocol !== 'https:') throw new Error('HTTPS required');
    } catch {
      reviewLink.setCustomValidity('Enter the full secure review link beginning with https://.');
    }
  }

  function parts() {
    const businessName = business.value.trim();
    const firstName = customer.value.trim();
    const work = service.value.trim();
    return {
      businessName,
      greeting: firstName ? `Hi ${firstName},` : 'Hi there,',
      workPhrase: work ? ` with ${work}` : '',
      link: reviewLink.value.trim(),
    };
  }

  function textRequest(values) {
    const templates = {
      warm: `${values.greeting} thank you for choosing ${values.businessName}${values.workPhrase}. If you have a moment, would you share an honest Google review about your experience? Your feedback helps other local customers know what to expect: ${values.link}\n\nThank you — ${values.businessName}`,
      direct: `${values.greeting} thanks for choosing ${values.businessName}${values.workPhrase}. Would you leave an honest Google review about your experience? ${values.link} — ${values.businessName}`,
      neighborly: `${values.greeting} it was great helping you${values.workPhrase}. If you have a minute, an honest Google review would help neighbors considering ${values.businessName}: ${values.link}\n\nWe appreciate your feedback!`,
    };
    return templates[tone.value];
  }

  function emailRequest(values) {
    const openings = {
      warm: `Thank you for choosing ${values.businessName}${values.workPhrase}. We appreciate the opportunity to help.`,
      direct: `Thank you for choosing ${values.businessName}${values.workPhrase}.`,
      neighborly: `It was great helping you${values.workPhrase}. Local word of mouth means a great deal to our team.`,
    };
    const closing = tone.value === 'neighborly' ? 'Thank you for supporting a local business,' : 'Thank you,';
    return `${values.greeting}\n\n${openings[tone.value]}\n\nIf you have a moment, would you share an honest Google review about your experience? Your feedback helps other customers know what to expect.\n\n${values.link}\n\n${closing}\n${values.businessName}`;
  }

  function savePreference() {
    try {
      if (remember.checked) {
        localStorage.setItem(storageKey, JSON.stringify({business: business.value.trim(), link: reviewLink.value.trim()}));
      } else {
        localStorage.removeItem(storageKey);
      }
    } catch {
      setStatus('Request built. This browser could not save your reusable details.');
    }
  }

  function resetOutput() {
    subject.value = '';
    message.value = '';
    count.textContent = '0 characters';
    copy.disabled = true;
    subjectWrap.hidden = true;
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    validateLink();
    if (!form.checkValidity()) {
      form.reportValidity();
      setStatus('Check the required fields and secure review link.', true);
      return;
    }
    const values = parts();
    const channel = chosenChannel();
    subject.value = `A quick question from ${values.businessName}`;
    message.value = channel === 'email' ? emailRequest(values) : textRequest(values);
    subjectWrap.hidden = channel !== 'email';
    count.textContent = `${message.value.length.toLocaleString('en-US')} characters`;
    copy.disabled = false;
    setStatus(`${channel === 'email' ? 'Email' : 'Text message'} ready. Review it before sending.`);
    savePreference();
  });

  copy.addEventListener('click', async () => {
    const content = subjectWrap.hidden ? message.value : `${subject.value}\n\n${message.value}`;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(content);
      setStatus('Copied. Paste it into your messaging or email app.');
    } catch {
      message.focus();
      message.select();
      setStatus('Automatic copying is unavailable. The message is selected; use your device’s Copy command.');
    }
  });

  clear.addEventListener('click', () => {
    form.reset();
    resetOutput();
    try { localStorage.removeItem(storageKey); } catch { /* Storage may be unavailable. */ }
    setStatus('Cleared, including remembered business details.');
    business.focus();
  });

  reviewLink.addEventListener('input', validateLink);
  form.addEventListener('input', event => {
    if (event.target.matches('[name="channel"], #review-tone, #review-business, #review-link, #review-customer, #review-service')) {
      resetOutput();
      setStatus('Details changed. Build a fresh request.');
    }
  });

  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (saved?.business && saved?.link) {
      business.value = saved.business;
      reviewLink.value = saved.link;
      remember.checked = true;
      setStatus('Your saved business details are ready. Add this customer’s information.');
    }
  } catch {
    try { localStorage.removeItem(storageKey); } catch { /* Storage may be unavailable. */ }
  }
}
