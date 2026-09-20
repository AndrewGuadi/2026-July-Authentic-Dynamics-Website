import assert from 'node:assert/strict';
import {MazeGame, MAZE, walkable, key} from '../authentic_dynamics/static/js/games/maze-core.js';

const game = new MazeGame(() => .25);
assert.ok(MAZE.every(row => row.length === 19));
const reachable = game.distances(9, 15);
MAZE.forEach((row, y) => [...row].forEach((cell, x) => {
  if (cell !== '#') assert.ok(reachable.has(key(x, y)), `Unreachable tile ${x},${y}`);
}));
assert.equal([...game.dots.values()].filter(dot => dot === 'o').length, 4);
game.start(); game.tick(.02);
assert.equal(game.player.x, 8); assert.equal(game.score, 10);
game.pause(); const stopped = JSON.stringify(game.player); game.tick(.05);
assert.equal(JSON.stringify(game.player), stopped);
game.start();
// Buffered turns stay pending when blocked and take effect at the next open tile.
Object.assign(game.player, {x: 7, y: 15, px: 7, py: 15, direction: 'left', timer: 0});
game.steer('up'); game.tick(.01); assert.equal(game.player.x, 6); assert.equal(game.player.y, 15);
game.player.timer = 0; game.tick(.01); assert.equal(game.player.x, 5);
game.player.timer = 0; game.tick(.01); assert.equal(game.player.x, 4);
game.player.timer = 0; game.tick(.01); assert.equal(game.player.y, 14);
assert.equal(game.player.x, 4);
// Power pellets, frightened captures, and chain scoring.
Object.assign(game.player, {x: 1, y: 1}); game.collect(); assert.ok(game.power > 0);
const before = game.score;
Object.assign(game.ghosts[0], {x: 1, y: 1, wait: 0}); game.collide(); assert.equal(game.score, before + 200);
Object.assign(game.ghosts[1], {x: 1, y: 1, wait: 0}); game.collide(); assert.equal(game.score, before + 600);
assert.equal(game.lives, 3); assert.ok(game.ghosts[0].wait > 0);
// Death resets actors but preserves collected dots and score; three hits end a run.
game.power = 0; const remaining = game.dots.size;
for (let i = 0; i < 3; i++) {
  game.start(); Object.assign(game.ghosts[0], {x: game.player.x, y: game.player.y, wait: 0}); game.collide();
}
assert.equal(game.state, 'over'); assert.equal(game.lives, 0); assert.equal(game.dots.size, remaining);
game.start(); assert.equal(game.lives, 3); assert.equal(game.score, 0); assert.equal(game.state, 'playing');
// Completing a maze advances the level while keeping score and remaining lives.
game.lives = 2; game.dots = new Map([[key(game.player.x, game.player.y), '.']]); game.collect();
assert.equal(game.level, 2); assert.equal(game.state, 'ready'); assert.equal(game.lives, 2); assert.ok(game.dots.size > 100);
// All autonomous movement remains in corridors throughout repeated simulated rounds.
for (let i = 0; i < 15000; i++) {
  if (game.state !== 'playing') game.start();
  if (i % 19 === 0) game.steer(['up', 'right', 'down', 'left'][Math.floor(i / 19) % 4]);
  game.tick(1 / 60);
  for (const entity of [game.player, ...game.ghosts]) assert.ok(walkable(entity.x, entity.y));
}
console.log('Maze simulation checks passed: reachability, turns, scoring, power, lives, levels, ghost movement.');
