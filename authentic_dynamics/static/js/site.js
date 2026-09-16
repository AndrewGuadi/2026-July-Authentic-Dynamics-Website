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
    if (event.key === 'Escape') closeMenu();
  });
}

document.addEventListener('click', event => {
  const link = event.target.closest('[data-interest]');
  const interest = document.querySelector('#interest');
  if (link && interest) interest.value = link.dataset.interest;
});

const contactForm = document.querySelector('#contact-form');
if (contactForm) {
  contactForm.addEventListener('submit', event => {
    event.preventDefault();
    const data = new FormData(contactForm);
    const body = `Hi Andrew,\n\nMy name is ${data.get('name')}.\nBusiness / organization: ${data.get('business') || 'Not provided'}\nEmail: ${data.get('email')}\nInterested in: ${data.get('interest')}\n\n${data.get('message')}\n\nThanks,\n${data.get('name')}`;
    const subject = encodeURIComponent('Let’s talk: ' + data.get('interest'));
    window.location.href = `mailto:hello@authenticdynamics.com?subject=${subject}&body=${encodeURIComponent(body)}`;
    const status = document.querySelector('#contact-status');
    if (status) status.textContent = 'Your email app should open with your draft. Nothing has been sent yet. If it doesn’t open, email hello@authenticdynamics.com directly.';
  });
}
