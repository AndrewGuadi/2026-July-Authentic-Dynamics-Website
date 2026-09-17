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
}

document.addEventListener('click', event => {
  const link = event.target.closest('[data-interest]');
  const interest = document.querySelector('#interest');
  if (link && interest) interest.value = link.dataset.interest;
});

const contactForm = document.querySelector('#contact-form');
if (contactForm) {
  const firstError = contactForm.querySelector('[aria-invalid="true"]');
  if (firstError) firstError.focus();
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
