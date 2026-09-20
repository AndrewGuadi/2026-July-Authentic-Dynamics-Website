// Simulation is independent of the DOM so movement and game rules can be tested.
export const MAZE = [
  '###################',
  '#o.......#.......o#',
  '#.##.###.#.###.##.#',
  '#.................#',
  '#.##.#.#####.#.##.#',
  '#....#...#...#....#',
  '####.###.#.###.####',
  '#....#.......#....#',
  '#.##.#.##.##.#.##.#',
  '#......#   #......#',
  '#.##.#.#   #.#.##.#',
  '#....#.......#....#',
  '#.##.###.#.###.##.#',
  '#........#........#',
  '#.##.###.#.###.##.#',
  '#o.#..... .....#.o#',
  '##.#.#.#####.#.#.##',
  '#....#...#...#....#',
  '#.######.#.######.#',
  '#.................#',
  '###################',
];
export const DIRECTIONS = {up: [0, -1], left: [-1, 0], down: [0, 1], right: [1, 0]};
const opposite = {up: 'down', down: 'up', left: 'right', right: 'left'};
export const key = (x, y) => `${x},${y}`;
export function walkable(x, y) { return Boolean(MAZE[y]?.[x] && MAZE[y][x] !== '#'); }
function actor(x, y, direction = 'left') { return {x, y, px: x, py: y, direction, timer: 0, duration: .14}; }

export class MazeGame {
  constructor(random = Math.random) { this.random = random; this.reset(); }
  reset() {
    this.score = 0; this.lives = 3; this.level = 1; this.state = 'ready';
    this.message = 'Ready to play.'; this.loadLevel();
  }
  loadLevel() {
    this.dots = new Map();
    MAZE.forEach((row, y) => [...row].forEach((cell, x) => {
      if (cell === '.' || cell === 'o') this.dots.set(key(x, y), cell);
    }));
    this.resetActors();
  }
  resetActors() {
    this.player = actor(9, 15); this.nextDirection = 'left';
    this.ghosts = [[8, 9], [9, 9], [10, 9], [9, 10]].map(([x, y], index) => ({...actor(x, y, 'up'), index, wait: index * .8 + 1.5}));
    this.power = 0; this.combo = 0; this.elapsed = 0;
  }
  start() {
    if (this.state === 'over') this.reset();
    if (this.state === 'ready' || this.state === 'paused') { this.state = 'playing'; this.message = 'Clear the dots. Watch the corners.'; }
  }
  pause() { if (this.state === 'playing') { this.state = 'paused'; this.message = 'Paused. Your maze can wait.'; } }
  steer(direction) { if (DIRECTIONS[direction]) this.nextDirection = direction; }
  canMove(entity, direction) { const [dx, dy] = DIRECTIONS[direction]; return walkable(entity.x + dx, entity.y + dy); }
  move(entity, direction, duration) {
    entity.px = entity.x; entity.py = entity.y; entity.direction = direction;
    const [dx, dy] = DIRECTIONS[direction]; entity.x += dx; entity.y += dy;
    entity.duration = duration; entity.timer += duration;
  }
  collect() {
    const position = key(this.player.x, this.player.y), dot = this.dots.get(position);
    if (!dot) return;
    this.dots.delete(position); this.score += dot === 'o' ? 50 : 10;
    if (dot === 'o') { this.power = Math.max(3, 7 - this.level * .3); this.combo = 0; this.message = 'Power up! Chase the striped blue ghosts.'; }
    if (!this.dots.size) {
      this.level++; this.loadLevel(); this.state = 'ready';
      this.message = `Level ${this.level}! A fresh maze, a faster chase.`;
    }
  }
  collide() {
    for (const ghost of this.ghosts) {
      if (ghost.wait > 0 || ghost.x !== this.player.x || ghost.y !== this.player.y) continue;
      if (this.power > 0) {
        const bonus = 200 * 2 ** Math.min(this.combo++, 3); this.score += bonus;
        Object.assign(ghost, actor(9, 9, 'up'), {wait: 3});
        this.message = `Ghost caught! +${bonus} points.`;
      } else {
        this.lives--; this.resetActors(); this.state = this.lives ? 'ready' : 'over';
        this.message = this.lives ? `${this.lives} ${this.lives === 1 ? 'life' : 'lives'} left. You’ve got this.` : `Game over. Final score: ${this.score}.`;
        return;
      }
    }
  }
  distances(targetX, targetY) {
    // Find shortest paths through corridors, rather than letting ghosts cross walls.
    if (!walkable(targetX, targetY)) { targetX = this.player.x; targetY = this.player.y; }
    const distances = new Map([[key(targetX, targetY), 0]]), queue = [[targetX, targetY]];
    for (let i = 0; i < queue.length; i++) {
      const [x, y] = queue[i];
      for (const [dx, dy] of Object.values(DIRECTIONS)) {
        const nx = x + dx, ny = y + dy, id = key(nx, ny);
        if (walkable(nx, ny) && !distances.has(id)) { distances.set(id, distances.get(key(x, y)) + 1); queue.push([nx, ny]); }
      }
    }
    return distances;
  }
  ghostDirection(ghost) {
    let choices = Object.keys(DIRECTIONS).filter(direction => this.canMove(ghost, direction));
    if (choices.length > 1) choices = choices.filter(direction => direction !== opposite[ghost.direction]);
    if (!choices.length) return null;
    if (this.power > 0) return choices[Math.floor(this.random() * choices.length)];
    const corners = [[1, 1], [17, 1], [1, 19], [17, 19]];
    const scatter = this.elapsed % 24 < 6;
    let target = scatter ? corners[ghost.index] : [this.player.x, this.player.y];
    if (!scatter && ghost.index === 1) {
      const [dx, dy] = DIRECTIONS[this.player.direction];
      target = [this.player.x + dx * 3, this.player.y + dy * 3];
    }
    if (!scatter && ghost.index === 3 && Math.abs(ghost.x - this.player.x) + Math.abs(ghost.y - this.player.y) < 5) target = corners[3];
    const distances = this.distances(...target);
    return choices.sort((a, b) => {
      const da = DIRECTIONS[a], db = DIRECTIONS[b];
      return (distances.get(key(ghost.x + da[0], ghost.y + da[1])) ?? 999) - (distances.get(key(ghost.x + db[0], ghost.y + db[1])) ?? 999);
    })[0];
  }
  tick(dt) {
    if (this.state !== 'playing') return;
    dt = Math.min(Math.max(dt, 0), .05); this.elapsed += dt;
    const hadPower = this.power > 0; this.power = Math.max(0, this.power - dt);
    if (hadPower && !this.power) this.message = 'Power ended. Dodge the ghosts!';
    this.player.timer -= dt;
    if (this.player.timer <= 0) {
      const direction = this.canMove(this.player, this.nextDirection) ? this.nextDirection : this.player.direction;
      if (this.canMove(this.player, direction)) this.move(this.player, direction, Math.max(.095, .145 - (this.level - 1) * .006));
      else { this.player.timer = 0; this.player.px = this.player.x; this.player.py = this.player.y; }
      this.collect();
      if (this.state !== 'playing') return;
      this.collide();
      if (this.state !== 'playing') return;
    }
    for (const ghost of this.ghosts) {
      if (ghost.wait > 0) { ghost.wait -= dt; continue; }
      ghost.timer -= dt;
      if (ghost.timer <= 0) {
        const direction = this.ghostDirection(ghost);
        if (direction) this.move(ghost, direction, this.power > 0 ? .26 : Math.max(.12, .195 - (this.level - 1) * .008));
        this.collide();
        if (this.state !== 'playing') return;
      }
    }
  }
}
