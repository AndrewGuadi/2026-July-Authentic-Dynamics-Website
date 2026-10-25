/* Decorative motion is optional: no script, reduced motion, or errors show the still. */
(() => {
  'use strict';
  const video = document.getElementById('contact-conversation');
  if (!video) return;
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  let observer;
  let failed = false;
  const sync = () => {
    observer?.disconnect();
    video.pause();
    video.hidden = preference.matches || failed;
    if (video.hidden) return;
    video.muted = true;
    // Start only once on entering view. Native controls can pause without restart.
    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver(entries => {
        if (entries.some(entry => entry.isIntersecting)) {
          observer.disconnect();
          video.play().catch(() => {}); // Browser policy may require pressing Play.
        }
      }, { threshold: 0.25 });
      observer.observe(video);
    }
  };
  video.addEventListener('error', () => { failed = true; sync(); });
  video.querySelector('source').addEventListener('error', () => { failed = true; sync(); });
  preference.addEventListener('change', sync);
  sync();
})();
