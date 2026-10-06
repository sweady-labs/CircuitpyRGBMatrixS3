"""Snake: a computer snake hunts apples on a 32 x 16 field and grows with every bite.

The snake takes the shortest way to the apple (breadth first search), but only if it could still
reach its own tail afterwards. Otherwise it follows its tail, the long way round, until a safe way
opens up. So it lives long, but not forever. Whether the tail can be reached is a flood fill in C
(bitmaptools.boundary_fill on a 32 x 16 bitmap); only the search for the way runs in Python, in
the half step without the color update. The snake moves half a cell at a time, which keeps the
motion smooth. Every body cell keeps the palette index of the step in which the head entered it,
and each step the palette maps these indices to a gradient from head to tail: the colors flow
along the body without redrawing it.
"""
import math
import random

import bitmaptools
import displayio

from app import gfx

FPS = 20
PREVIEW_AT = 5.0
COLS, ROWS = 32, 16  # cells of 2 x 2 pixels
CELLS = COLS * ROWS
HALF_STEP = 0.05  # seconds per half cell: 10 cells per second
START_LENGTH = 4
WIN_LENGTH = 200
GREED = 0.03  # chance to go for an apple without checking the way back
MARKS = 240  # palette indices 1..MARKS for body cells, more than the longest snake
APPLE, LEAF, CRUMB = MARKS + 1, MARKS + 2, MARKS + 3
BODY = ((0.0, 0xF4FFA0), (0.12, 0x8CFF4A), (0.55, 0x18C46A), (1.0, 0x0C4466))
GRADIENT = 64
DEAD = 0x8A1020
SCORE = 0x2C3A52


def _neighbors(cell):
    x, y = cell % COLS, cell // COLS
    near = []
    if x > 0:
        near.append(cell - 1)
    if x < COLS - 1:
        near.append(cell + 1)
    if y > 0:
        near.append(cell - COLS)
    if y < ROWS - 1:
        near.append(cell + COLS)
    return tuple(near)


NEIGHBORS = tuple(_neighbors(cell) for cell in range(CELLS))


class Scene:
    def __init__(self, group, settings):
        self.group = group
        # the score lies under the field, the snake crawls over it
        self.score_label = gfx.Label(group, "0", SCORE, 59, 1)
        self.bitmap, self.pal = gfx.canvas(group, [0] * (CRUMB + 1), transparent=(0,))
        self.pal[LEAF] = 0x3CC23C
        self.pal[CRUMB] = 0xFFD0A0
        # ring that flashes up around an apple when it is eaten
        self.ring = displayio.Bitmap(64, 32, 2)
        self.ring_pal = gfx.Pal([0, 0], transparent=(0,))
        group.append(displayio.TileGrid(self.ring, pixel_shader=self.ring_pal.palette))
        self.ring_at = None
        self.ring_time = 0.0
        # game over: big score, record below
        self.big = displayio.Group(scale=2)
        group.append(self.big)
        self.big_label = None
        self.best_label = None

        self.gradient = gfx.gradient(BODY, GRADIENT)
        self.prev = [0] * CELLS
        self.room = displayio.Bitmap(COLS, ROWS, 3)  # for flood fills: 0 free, 1 body, 2 reaches the tail
        self.best = 0
        self.phase = 0.0
        self.new_game()

    # --- Game -------------------------------------------------------------------------

    def new_game(self):
        self.bitmap.fill(0)
        y = random.randrange(3, ROWS - 3)
        x = random.randrange(2, 8)
        self.body = [y * COLS + x + i for i in range(START_LENGTH)]  # tail first, head last
        self.blocked = bytearray(CELLS)
        self.step = START_LENGTH - 1  # number of the step in which the head entered its cell
        for cell in self.body:
            self.blocked[cell] = 1
        for i, cell in enumerate(self.body):
            self.fill_cell(cell, self.mark(len(self.body) - 1 - i))
        self.colors()
        self.path = []
        self.patience = 0  # steps until the next try to find a safe way to the apple
        self.hungry = 0  # steps since the last apple
        self.state = "play"
        self.clock = 0.0
        self.half = 0
        self.place_apple()
        self.show_score()
        self.target = self.decide()

    def mark(self, k):
        """Palette index of the body cell k steps behind the head."""
        return 1 + (self.step - k) % MARKS

    def colors(self):
        """The gradient from the head (k = 0) to the tail, on the palette indices of the cells."""
        pal, gradient, step = self.pal, self.gradient, self.step
        length = len(self.body)
        stretch = max(1, length - 1)
        for k in range(length):
            pal[1 + (step - k) % MARKS] = gradient[k * (GRADIENT - 1) // stretch]

    def place_apple(self):
        free = CELLS - len(self.body)
        if free <= 0:
            self.apple = None
            return
        for _ in range(40):
            cell = random.randrange(CELLS)
            if not self.blocked[cell]:
                break
        else:  # the field is nearly full: take the first free cell
            cell = 0
            while self.blocked[cell]:
                cell += 1
        self.apple = cell
        x, y = (cell % COLS) * 2, (cell // COLS) * 2
        self.bitmap[x, y] = APPLE
        self.bitmap[x + 1, y] = LEAF
        self.bitmap[x, y + 1] = APPLE
        self.bitmap[x + 1, y + 1] = APPLE

    def show_score(self):
        text = str(len(self.body) - START_LENGTH)
        self.score_label.x = 63 - gfx.text_width(text)
        self.score_label.set(text)

    # --- Way finding ------------------------------------------------------------------

    def search(self, start, goal):
        """Shortest way from start to goal around the body, as a list of cells without start, or None."""
        seen = bytearray(self.blocked)
        seen[start] = 1
        prev = self.prev
        queue = [start]
        push = queue.append
        for cell in queue:  # the list grows while we walk through it: breadth first
            for near in NEIGHBORS[cell]:
                if not seen[near]:
                    seen[near] = 1
                    prev[near] = cell
                    push(near)
            if seen[goal]:
                way = [goal]
                while prev[way[-1]] != start:
                    way.append(prev[way[-1]])
                way.reverse()
                return way
        return None

    def tail_room(self, body):
        """Flood fill from the tail of `body`: afterwards every cell from which the tail can be
        reached has the value 2 in self.room (cell numbers index the bitmap directly)."""
        room = self.room
        room.fill(0)
        for cell in body:
            room[cell] = 1
        tail = body[0]
        room[tail] = 0  # the tail moves on
        bitmaptools.boundary_fill(room, tail % COLS, tail // COLS, 2, 0)
        return room

    def safe_way(self, careful=True):
        """Way to the apple, if the snake can still reach its tail after eating it."""
        way = self.search(self.body[-1], self.apple)
        if way is None or not careful:
            return way
        after = (self.body + way)[-(len(self.body) + 1):]  # the snake after the meal, one longer
        room = self.tail_room(after)
        for near in NEIGHBORS[after[-1]]:
            if room[near] == 2:
                return way
        return None

    def follow_tail(self):
        """No safe way to the apple: a neighbor cell from which the tail can still be reached,
        preferably far from it, so the snake winds along and keeps an exit open."""
        head, tail = self.body[-1], self.body[0]
        room = self.tail_room(self.body)
        tx, ty = tail % COLS, tail // COLS
        best, best_score = None, 0
        for near in NEIGHBORS[head]:
            if self.blocked[near] and near != tail:
                continue
            if room[near] == 2:
                score = abs(near % COLS - tx) + abs(near // COLS - ty)
            else:  # cut off from the tail: only if nothing better comes, by free room around it
                score = -10 + sum(1 for n in NEIGHBORS[near] if not self.blocked[n])
            if near == self.apple:
                score -= CELLS  # eating now would make it tighter
            if best is None or score > best_score:
                best, best_score = near, score
        return best

    def decide(self):
        if not self.path:
            if self.patience <= 0:
                # now and then, and after a long time without food, the snake takes a risk
                careful = self.hungry < 1200 and random.random() > GREED
                self.path = self.safe_way(careful) or []
                if not self.path:
                    self.patience = 4
            else:
                self.patience -= 1
        if self.path:
            return self.path.pop(0)
        return self.follow_tail()

    # --- Moving -----------------------------------------------------------------------

    def fill_cell(self, cell, value):
        x, y = (cell % COLS) * 2, (cell // COLS) * 2
        bitmaptools.fill_region(self.bitmap, x, y, x + 2, y + 2, value)

    def fill_half(self, cell, toward, front, value):
        """The half of a cell at its front (towards the cell `toward`) or at its back."""
        x, y = (cell % COLS) * 2, (cell // COLS) * 2
        d = toward - cell
        if d == 1 or d == -1:
            column = x + (1 if (d > 0) == front else 0)
            bitmaptools.fill_region(self.bitmap, column, y, column + 1, y + 2, value)
        else:
            row = y + (1 if (d > 0) == front else 0)
            bitmaptools.fill_region(self.bitmap, x, row, x + 2, row + 1, value)

    def half_step(self):
        if self.half == 0:
            head, tail, target = self.body[-1], self.body[0], self.target
            if target is None or (self.blocked[target] and target != tail):
                self.die()
                return
            self.grow = target == self.apple
            self.leaving = None if self.grow or target == tail else tail
            self.step += 1
            self.hungry += 1
            if not self.grow:
                self.blocked[tail] = 0
            self.blocked[target] = 1
            self.body.append(target)
            self.colors()
            if self.leaving is not None:
                self.fill_half(tail, self.body[1], False, 0)
            self.fill_half(target, head, True, self.mark(0))  # the half next to the old head
            self.half = 1
        else:
            target = self.body[-1]
            if self.leaving is not None:
                self.fill_half(self.leaving, self.body[1], True, 0)
            self.fill_cell(target, self.mark(0))
            if not self.grow:
                self.body.pop(0)
            else:
                self.eat(target)
            self.half = 0
            if self.state == "play":
                # the next step is planned here; the other half step updates the palette
                self.target = self.decide()

    def eat(self, cell):
        self.hungry = 0
        self.path = []
        self.show_score()
        self.ring_at = ((cell % COLS) * 2 + 1, (cell // COLS) * 2 + 1)
        self.ring_time = 0.0
        if len(self.body) >= WIN_LENGTH:
            self.die(won=True)
        else:
            self.place_apple()
            if self.apple is None:
                self.die(won=True)

    def die(self, won=False):
        self.state = "won" if won else "dying"
        self.clock = 0.0
        self.dead_colors = [self.pal[self.mark(k)] for k in range(len(self.body))]
        self.crumbled = 0
        self.crumbs = []

    # --- Frames -----------------------------------------------------------------------

    def frame(self, dt):
        self.phase += dt
        self.clock += dt
        if self.state == "play":
            steps = 0
            while self.clock >= HALF_STEP and steps < 2 and self.state == "play":
                self.clock -= HALF_STEP
                steps += 1
                self.half_step()
            self.clock = min(self.clock, HALF_STEP)
        elif self.state in ("dying", "won"):
            self.game_over()
        elif self.state == "score" and self.clock > 3.5:
            self.big_label.set("")
            self.best_label.set("")
            self.new_game()

        if self.apple is not None and self.state == "play":
            pulse = 0.5 + 0.5 * math.sin(self.phase * 5.0)
            self.pal[APPLE] = gfx.mix(0xC8102A, 0xFF5A3A, pulse)
        self.draw_ring(dt)

    def game_over(self):
        """The snake turns red (or golden after a win), then crumbles away from the head."""
        t = self.clock
        length = len(self.body)
        if t < 0.6:
            color = 0xFFC830 if self.state == "won" else DEAD
            for k in range(length):
                self.pal[self.mark(k)] = gfx.mix(self.dead_colors[k], color, t / 0.6)
            return
        # about one second for the whole body; a crumbling cell lights up for one frame
        for cell in self.crumbs:
            self.fill_cell(cell, 0)
        self.crumbs = []
        due = min(length, int((t - 0.6) * max(20, length)) + 1)
        while self.crumbled < due:
            cell = self.body[length - 1 - self.crumbled]
            self.fill_cell(cell, CRUMB)
            self.crumbs.append(cell)
            self.crumbled += 1
        if due >= length and t > 0.6 + 1.2:
            self.bitmap.fill(0)
            self.show_result()

    def show_result(self):
        score = len(self.body) - START_LENGTH
        record = score > self.best
        self.best = max(self.best, score)
        text = str(score)
        if self.big_label is None:
            self.big_label = gfx.Label(self.big, text, 0, 0, 1)
            self.best_label = gfx.Label(self.group, "", 0, 0, 22)
        self.big_label.x = (32 - gfx.text_width(text)) // 2
        self.big_label.set(text, 0xFFE070 if record else 0x8CFF4A)
        line = "Rekord!" if record and score else "Rekord %d" % self.best
        self.best_label.x = (64 - gfx.text_width(line)) // 2
        self.best_label.set(line, 0xFFB030 if record else 0x5A6A80)
        self.score_label.set("")
        self.state = "score"
        self.clock = 0.0

    def draw_ring(self, dt):
        if self.ring_at is None:
            return
        self.ring_time += dt
        self.ring.fill(0)  # also wipes a ring that a quick second apple cut short
        radius = 1 + int(self.ring_time * 16)
        if radius > 5:
            self.ring_at = None
            return
        self.ring_pal[1] = gfx.mix(0xFFE0B0, 0xFF5030, radius / 5) if radius < 5 else 0x802010
        bitmaptools.draw_circle(self.ring, self.ring_at[0], self.ring_at[1], radius, 1)
