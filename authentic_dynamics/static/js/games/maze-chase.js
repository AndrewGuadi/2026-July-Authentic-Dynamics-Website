import {MazeGame, MAZE} from './maze-core.js';

const game = new MazeGame();
const $ = id => document.getElementById(`game-${id}`);
const canvas = document.getElementById('maze'), ctx = canvas.getContext('2d');
const arcade = document.getElementById('arcade');
const tile = 30, storageKey = 'ad-maze-chase-best';
let best = 0, storedBest = 0, storageAvailable = true, previousState, previousMessage, lastTime = 0;
let touchStart = null;
try {
  const saved = Number(localStorage.getItem(storageKey));
  if (Number.isSafeInteger(saved) && saved >= 0) best = storedBest = saved;
} catch { storageAvailable = false; }
function storageNote() { $('storage').textContent = storageAvailable ? 'Best score is saved on this device only.' : 'Browser storage is unavailable. Your best score lasts for this visit.'; }
storageNote();

function saveBest() {
  if (best <= storedBest || !storageAvailable) return;
  try { localStorage.setItem(storageKey, String(best)); storedBest = best; }
  catch { storageAvailable = false; storageNote(); }
}

const wallLayer = document.createElement('canvas'); wallLayer.width = 570; wallLayer.height = 630;
const wallCtx = wallLayer.getContext('2d');
wallCtx.fillStyle = '#080f1e'; wallCtx.fillRect(0, 0, 570, 630);
MAZE.forEach((row, y) => [...row].forEach((cell, x) => {
  if (cell !== '#') return;
  wallCtx.fillStyle = '#142549'; wallCtx.strokeStyle = '#4e77c9'; wallCtx.lineWidth = 1.5;
  wallCtx.beginPath(); wallCtx.roundRect(x * tile + 3, y * tile + 3, tile - 6, tile - 6, 5); wallCtx.fill(); wallCtx.stroke();
}));

function position(entity) {
  const progress = Math.max(0, Math.min(1, 1 - entity.timer / entity.duration));
  return [(entity.px + (entity.x - entity.px) * progress + .5) * tile, (entity.py + (entity.y - entity.py) * progress + .5) * tile];
}

function draw(time) {
  ctx.drawImage(wallLayer, 0, 0);
  for (const [id, type] of game.dots) {
    const [x, y] = id.split(',').map(Number);
    ctx.fillStyle = type === 'o' ? '#b8ff63' : '#f4deb1';
    ctx.beginPath(); ctx.arc((x + .5) * tile, (y + .5) * tile, type === 'o' ? 6 : 2.2, 0, Math.PI * 2); ctx.fill();
    if (type === 'o') { ctx.strokeStyle = '#587340'; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc((x + .5) * tile, (y + .5) * tile, 9, 0, Math.PI * 2); ctx.stroke(); }
  }
  const [x, y] = position(game.player);
  const angle = {right: 0, down: Math.PI / 2, left: Math.PI, up: -Math.PI / 2}[game.player.direction];
  const mouth = game.state === 'playing' ? .16 + Math.abs(Math.sin(time / 95)) * .37 : .3;
  ctx.save(); ctx.translate(x, y); ctx.rotate(angle); ctx.fillStyle = '#b8ff63';
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, 11.5, mouth, Math.PI * 2 - mouth); ctx.closePath(); ctx.fill(); ctx.restore();
  for (const ghost of game.ghosts) {
    const [gx, gy] = position(ghost), scared = game.power > 0 && ghost.wait <= 0;
    ctx.save(); ctx.translate(gx, gy); ctx.globalAlpha = ghost.wait > 0 ? .4 : 1;
    ctx.fillStyle = scared ? '#77aaff' : ['#ff7496', '#7fe3dd', '#d3a0ff', '#ffb469'][ghost.index];
    ctx.beginPath(); ctx.arc(0, -1, 11, Math.PI, 0); ctx.lineTo(11, 11); ctx.lineTo(6, 7); ctx.lineTo(1, 11); ctx.lineTo(-4, 7); ctx.lineTo(-11, 11); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#fff';
    for (const eyeX of [-4, 4]) { ctx.beginPath(); ctx.ellipse(eyeX, -2, 3, 4, 0, 0, Math.PI * 2); ctx.fill(); }
    ctx.fillStyle = '#112543';
    for (const eyeX of [-4, 4]) { ctx.beginPath(); ctx.arc(eyeX + (ghost.direction === 'right' ? 1 : ghost.direction === 'left' ? -1 : 0), -2 + (ghost.direction === 'down' ? 1 : ghost.direction === 'up' ? -1 : 0), 1.6, 0, Math.PI * 2); ctx.fill(); }
    if (scared) {
      ctx.strokeStyle = '#112543'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-7, 5); ctx.lineTo(-3, 3); ctx.lineTo(0, 5); ctx.lineTo(3, 3); ctx.lineTo(7, 5); ctx.stroke();
      ctx.strokeStyle = '#fff'; ctx.beginPath(); ctx.moveTo(-7, -9); ctx.lineTo(7, -9); ctx.stroke();
    }
    ctx.restore();
  }
}

function updateUI() {
  best = Math.max(best, game.score);
  for (const [id, value] of Object.entries({score: game.score, best, level: game.level, lives: game.lives})) {
    const text = value.toLocaleString(); if ($(id).textContent !== text) $(id).textContent = text;
  }
  $('power').textContent = game.power > 0 ? `POWER · ${Math.ceil(game.power)}s` : `${game.dots.size} dots left`;
  if (previousMessage !== game.message) { $('status').textContent = game.message; previousMessage = game.message; }
  if (previousState === game.state) return;
  previousState = game.state;
  const playing = game.state === 'playing';
  $('overlay').hidden = playing;
  $('pause').disabled = game.state === 'ready' || game.state === 'over';
  $('pause').textContent = game.state === 'paused' ? 'Resume' : 'Pause';
  if (!playing) {
    saveBest();
    $('overlay-title').textContent = game.state === 'paused' ? 'Take your time.' : game.state === 'over' ? 'That was a good run.' : game.level > 1 ? `Level ${game.level}` : game.lives < 3 ? 'Back for another bite.' : 'The dots await.';
    $('overlay-message').textContent = game.message;
    $('start').textContent = game.state === 'paused' ? 'Resume game →' : game.state === 'over' ? 'Play again →' : game.lives < 3 || game.level > 1 ? 'Continue →' : 'Start game →';
  }
}

function start() { game.start(); lastTime = 0; updateUI(); canvas.focus({preventScroll: true}); }
function pause() { if (game.state === 'paused') start(); else { game.pause(); updateUI(); } }
function newGame() {
  game.pause(); updateUI();
  if (game.score > 0 && !window.confirm('Start a new game? Your current run will end.')) return;
  game.reset(); previousState = null; updateUI(); draw(0);
}
$('start').addEventListener('click', start);
$('pause').addEventListener('click', pause);
$('restart').addEventListener('click', newGame);
$('clear-best').addEventListener('click', () => {
  if (!window.confirm('Clear your saved best score on this device?')) return;
  best = storedBest = game.score;
  try { localStorage.removeItem(storageKey); if (best) localStorage.setItem(storageKey, String(best)); }
  catch { storageAvailable = false; }
  storageNote(); updateUI();
});

const keys = {ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right', w: 'up', a: 'left', s: 'down', d: 'right'};
arcade.addEventListener('keydown', event => {
  // Buttons retain their normal Space/Enter behavior; game shortcuts require canvas focus.
  if (event.target !== canvas || event.altKey || event.ctrlKey || event.metaKey) return;
  const direction = keys[event.key] || keys[event.key.toLowerCase()];
  if (direction) { event.preventDefault(); game.steer(direction); }
  else if (event.key.toLowerCase() === 'p' || event.key === ' ') { event.preventDefault(); if (!event.repeat) pause(); }
  else if (event.key === 'Enter' && game.state !== 'playing') { event.preventDefault(); start(); }
});
document.querySelectorAll('[data-direction]').forEach(button => {
  button.addEventListener('pointerdown', event => { event.preventDefault(); game.steer(button.dataset.direction); canvas.focus({preventScroll: true}); });
  button.addEventListener('click', () => game.steer(button.dataset.direction));
});
canvas.addEventListener('pointerdown', event => { touchStart = {x: event.clientX, y: event.clientY, id: event.pointerId}; canvas.setPointerCapture(event.pointerId); });
canvas.addEventListener('pointerup', event => {
  if (!touchStart || touchStart.id !== event.pointerId) return;
  const dx = event.clientX - touchStart.x, dy = event.clientY - touchStart.y;
  if (Math.max(Math.abs(dx), Math.abs(dy)) >= 12) game.steer(Math.abs(dx) > Math.abs(dy) ? dx > 0 ? 'right' : 'left' : dy > 0 ? 'down' : 'up');
  touchStart = null;
});
canvas.addEventListener('pointercancel', () => { touchStart = null; });
function autoPause() { game.pause(); updateUI(); saveBest(); lastTime = 0; }
document.addEventListener('visibilitychange', () => { if (document.hidden) autoPause(); });
window.addEventListener('blur', autoPause);
window.addEventListener('pagehide', autoPause);
function frame(time) {
  game.tick(lastTime ? Math.min((time - lastTime) / 1000, .05) : 0);
  lastTime = time; draw(game.state === 'playing' ? time : 0); updateUI(); requestAnimationFrame(frame);
}
updateUI(); draw(0); requestAnimationFrame(frame);
