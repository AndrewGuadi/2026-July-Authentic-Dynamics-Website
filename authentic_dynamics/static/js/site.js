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
