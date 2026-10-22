'use strict';

const menuButton = document.querySelector('.menu');
const navigation = document.querySelector('#nav');

if (menuButton && navigation) {
  const mobileBreakpoint = window.matchMedia('(max-width: 1050px)');

  const setMenuOpen = (open) => {
    // Keep the visible state and the accessible state in sync.
    navigation.classList.toggle('open', open);
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  };

  const closeMenu = () => setMenuOpen(false);

  menuButton.addEventListener('click', event => {
    const opening = menuButton.getAttribute('aria-expanded') !== 'true';
    setMenuOpen(opening);

    // Move focus for keyboard activation, but do NOT steal it from a touch tap.
    // iOS Safari can fire a focusout before it dispatches a tapped link's click.
    if (opening && event.detail === 0) {
      navigation.querySelector('a[href]')?.focus({ preventScroll: true });
    }
  });

  navigation.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!link || !navigation.contains(link)) return;

    // Never hide a tapped link synchronously. Let the browser perform its
    // native link action first (including hash navigation on the same page).
    window.setTimeout(closeMenu, 0);
  });

  const closeWhenOutside = event => {
    if (menuButton.getAttribute('aria-expanded') !== 'true') return;
    if (!navigation.contains(event.target) && !menuButton.contains(event.target)) {
      closeMenu();
    }
  };

  // On iOS Safari, taps on non-interactive areas do not always synthesize
  // a click. pointerdown fires for touch targets outside the menu.
  document.addEventListener('pointerdown', closeWhenOutside);
  document.addEventListener('click', closeWhenOutside);

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') {
      closeMenu();
      menuButton.focus({ preventScroll: true });
    }
  });

  // Do not close the menu on focusout: touch and assistive technology can
  // temporarily produce relatedTarget=null while a link is being activated.
  mobileBreakpoint.addEventListener('change', closeMenu);
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
