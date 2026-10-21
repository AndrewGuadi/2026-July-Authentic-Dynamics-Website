'use strict';

const menuButton = document.querySelector('.menu');
const navigation = document.querySelector('#nav');

if (menuButton && navigation) {
  const closeMenu = () => {
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Open menu');
    navigation.classList.remove('open');
  };

  menuButton.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') !== 'true';
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    navigation.classList.toggle('open', open);
  });
  navigation.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') {
      closeMenu();
      menuButton.focus();
    }
  });
  document.addEventListener('click', event => {
    if (!navigation.contains(event.target) && !menuButton.contains(event.target)) closeMenu();
  });
  menuButton.addEventListener('click', () => {
    if (menuButton.getAttribute('aria-expanded') === 'true') navigation.querySelector('a')?.focus();
  });
  navigation.addEventListener('focusout', event => {
    if (!navigation.contains(event.relatedTarget) && event.relatedTarget !== menuButton) closeMenu();
  });
  window.matchMedia('(max-width: 1050px)').addEventListener('change', closeMenu);
  // Collapse only after all menu behavior is installed; no-JS links remain usable.
  navigation.closest('header').classList.add('nav-enhanced');
}

document.addEventListener('click', event => {
  const link = event.target.closest('[data-interest]');
  const interest = document.querySelector('#interest');
  if (link && interest && [...interest.options].some(option => option.value === link.dataset.interest)) {
    interest.value = link.dataset.interest;
    interest.dispatchEvent(new Event('change', {bubbles: true}));
  }
});

const contactForm = document.querySelector('#contact-form');
if (contactForm) {
  const firstError = contactForm.querySelector('#contact-errors, [aria-invalid="true"]');
  if (firstError) {
    // Native POST fragment navigation happens after deferred scripts. Focus the
    // summary after that navigation so keyboard users land on the errors.
    const focusError = () => requestAnimationFrame(() => firstError.focus());
    if (document.readyState === 'complete') focusError();
    else window.addEventListener('load', focusError, {once: true});
  }
  const submitButton = contactForm.querySelector('button[type="submit"]');
  const originalLabel = submitButton.innerHTML;
  contactForm.addEventListener('submit', () => {
    submitButton.disabled = true;
    submitButton.textContent = 'Sending…';
  });
  window.addEventListener('pageshow', () => {
    submitButton.disabled = false;
    submitButton.innerHTML = originalLabel;
  });
}
