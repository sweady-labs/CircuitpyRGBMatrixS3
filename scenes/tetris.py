"""Tetris: the computer plays, line after line, faster with every level, until the stack tops out.

For every new piece it tries all rotations and columns and rates the stack each would leave
(height, holes, bumpiness, cleared lines), one rotation per frame so that no frame gets long.
Then it turns and shifts the piece there like a player would, while gravity pulls it down; a
dim ghost shows where it is aiming. Gravity grows with the level but the hands of the computer
do not get faster, so at some point it cannot reach its spot in time, the stack grows and the
game starts over.
"""
import random

import bitmaptools
import displayio

from app import gfx

FPS = 30
PREVIEW_AT = 5.0
COLS, ROWS = 10, 16
FULL = (1 << COLS) - 1
FIELD_X = 22  # the playfield is in the middle, cells are 2 x 2 pixels
ACTION = 0.075  # seconds per turn or shift of the computer player
SOFT_DROP = 32.0  # rows per second once the piece is above its spot

PIECES = (  # color, size of the rotation box, cells of the first rotation
    (0x00E5FF, 4, ((0, 1), (1, 1), (2, 1), (3, 1))),  # I
    (0xFFD200, 2, ((0, 0), (1, 0), (0, 1), (1, 1))),  # O
    (0xB44CFF, 3, ((1, 0), (0, 1), (1, 1), (2, 1))),  # T
    (0x38F04A, 3, ((1, 0), (2, 0), (0, 1), (1, 1))),  # S
    (0xFF2D3D, 3, ((0, 0), (1, 0), (1, 1), (2, 1))),  # Z
    (0x2F6BFF, 3, ((0, 0), (0, 1), (1, 1), (2, 1))),  # J
    (0xFF8A1C, 3, ((2, 0), (0, 1), (1, 1), (2, 1))),  # L
)
# tiles of 2 x 2 pixels: 0 empty, 1-7 the pieces, 8-14 their ghosts, 15 flash, 16 grey
GHOST, FLASH, GREY = 7, 15, 16
SCORES = (0, 1, 3, 5, 8)  # per level for 1, 2, 3 or 4 lines at once
WELL = COLS - 1  # column kept free for I pieces while the stack is low
CALM = 9  # stack height up to which the computer builds for four lines at once (minus level / 2)
WELL_LINES = (0.0, -1.0, -0.5, 1.0, 8.0)  # value of 0-4 cleared lines while it is calm

FRAME, LABEL = 1, 2  # colors of the HUD canvas
HUD = (0, 0x26324E, 0x303C5C)
VALUE = 0xC8D4F4

# tables for rows stored as 10 bit numbers: filled cells in a row, and its lowest filled column
POP = bytearray(1 << COLS)
LOW = bytearray(1 << COLS)
for _i in range(1, 1 << COLS):
    POP[_i] = POP[_i >> 1] + (_i & 1)
    LOW[_i] = 0 if _i & 1 else LOW[_i >> 1] + 1


def _rotations(size, cells):
    """All four rotations inside the box, plus for each: its lowest cell per column."""
    states = []
    for _ in range(4):
        bottoms = {}
        for x, y in cells:
            bottoms[x] = max(bottoms.get(x, -1), y)
        states.append((tuple(cells), tuple(bottoms.items()), min(y for x, y in cells)))
        cells = tuple((size - 1 - y, x) for x, y in cells)
    return states


ROTATIONS = tuple(_rotations(size, cells) for color, size, cells in PIECES)


def _distinct(states):
    """Rotations that give different shapes (an O is the same in all four), for the search."""
    seen = []
    keep = []
    for r, (cells, bottoms, top) in enumerate(states):
        mx, my = min(x for x, y in cells), min(y for x, y in cells)
        shape = sorted((x - mx, y - my) for x, y in cells)
        if shape not in seen:
            seen.append(shape)
            keep.append(r)
    return tuple(keep)


SEARCH = tuple(_distinct(states) for states in ROTATIONS)


def rate(rows, lines, calm):
    """How good a stack is (higher is better). The weights for height, holes and bumpiness are
    the well known ones found with a genetic algorithm. While it is calm (the stack is low), the
    computer keeps the right column free and waits for an I piece to clear four lines at once:
    more spectacular than clearing every single line. Otherwise any cleared line is welcome."""
    covered = 0
    holes = 0
    heights = [0] * COLS
    height = ROWS
    for row in rows:
        new = row & ~covered
        while new:  # columns whose top is in this row
            heights[LOW[new]] = height
            new &= new - 1
        holes += POP[covered & ~row]
        covered |= row
        height -= 1
    bumps = 0
    for i in range(WELL - 1):
        bumps += abs(heights[i] - heights[i + 1])
    score = -0.51 * sum(heights) - 0.36 * holes - 0.18 * bumps
    if not calm:
        return score + 0.76 * lines - 0.18 * abs(heights[WELL - 1] - heights[WELL])
    # a cleared line lowers the stack by a whole row; take that gain back, so the table decides
    score += -0.51 * COLS * lines + WELL_LINES[lines] - 0.8 * heights[WELL]
    # but no second deep well somewhere else, only I pieces could fill it
    left = ROWS
    for i in range(WELL):
        right = heights[i + 1] if i + 1 < WELL else ROWS
        depth = min(left, right) - heights[i]
        if depth > 2:
            score -= 0.6 * (depth - 2)
        left = heights[i]
    return score


class Scene:
    def __init__(self, group, settings):
        # frame around the field and the labels left and right of it
        self.hud, self.hud_pal = gfx.canvas(group, HUD)
        bitmaptools.fill_region(self.hud, FIELD_X - 1, 0, FIELD_X, 32, FRAME)
        bitmaptools.fill_region(self.hud, FIELD_X + 2 * COLS, 0, FIELD_X + 2 * COLS + 1, 32, FRAME)
        for text, x, y in (("next", 0, 0), ("level", 0, 17), ("lines", 43, 0), ("score", 43, 17)):
            gfx.draw_text(self.hud, text, x + (21 - gfx.text_width(text)) // 2, y, LABEL)

        self.tile_pal = gfx.Pal(self.tile_colors())
        sheet = displayio.Bitmap(2 * (GREY + 1), 2, len(self.tile_pal))
        for tile in range(1, GREY + 1):
            for (dx, dy), shade in zip(((0, 0), (1, 0), (0, 1), (1, 1)), self.tile_shades(tile)):
                sheet[2 * tile + dx, dy] = shade
        self.grid = displayio.TileGrid(sheet, pixel_shader=self.tile_pal.palette, width=COLS, height=ROWS,
                                       tile_width=2, tile_height=2, x=FIELD_X, y=0)
        group.append(self.grid)
        self.preview = displayio.TileGrid(sheet, pixel_shader=self.tile_pal.palette, width=4, height=2,
                                          tile_width=2, tile_height=2, x=6, y=10)
        group.append(self.preview)
        self.values = [gfx.Label(group, "", VALUE, 0, y) for y in (25, 8, 25)]  # level, lines, score

        self.bag = []
        self.party = 0.0  # seconds left of the frame glowing after four lines at once
        self.new_game()

    # --- Looks ------------------------------------------------------------------------

    def tile_colors(self):
        """Palette: 0 black, 1-21 light, base and dark of each piece, 22-28 the ghosts,
        29 the flash, 30-32 grey."""
        colors = [0]
        for color, size, cells in PIECES:
            colors += [gfx.mix(color, 0xFFFFFF, 0.45), color, gfx.scale(color, 0.5)]
        colors += [gfx.scale(color, 0.2) for color, size, cells in PIECES]
        colors += [0xC8E6FF, 0x6A7284, 0x50586A, 0x2E323C]
        return colors

    def tile_shades(self, tile):
        """Palette index of the four pixels of a tile: top left light, bottom right dark."""
        if tile < GHOST + 1:
            light, base, dark = 3 * tile - 2, 3 * tile - 1, 3 * tile
            return light, base, base, dark
        if tile < FLASH:
            return (21 + tile - GHOST,) * 4
        if tile == FLASH:
            return (29,) * 4
        return 30, 31, 31, 32

    # --- Game -------------------------------------------------------------------------

    def new_game(self):
        self.rows = [0] * ROWS
        self.colors = bytearray(COLS * ROWS)
        self.lines = 0
        self.score = 0
        self.level = 1
        self.redraw()
        self.next = self.from_bag()
        self.show_values()
        self.drawn = []
        self.spawn()

    def from_bag(self):
        """All seven pieces in random order, then the next seven: no long droughts."""
        if not self.bag:
            self.bag = list(range(len(PIECES)))
            for i in range(len(self.bag) - 1, 0, -1):
                j = random.randrange(i + 1)
                self.bag[i], self.bag[j] = self.bag[j], self.bag[i]
        return self.bag.pop()

    def spawn(self):
        self.kind = self.next
        self.next = self.from_bag()
        self.show_next()
        self.rot = 0
        self.px = 4 if PIECES[self.kind][1] == 2 else 3
        self.py = -ROTATIONS[self.kind][0][2]  # top cell in the first row
        self.tops = self.column_tops()
        if not self.fits(self.rot, self.px, self.py):
            self.start_game_over()
            return
        self.best_move = None
        self.searched = 0
        self.dropping = False
        self.action_time = 0.0
        self.fall_time = 0.0
        self.state = "think"
        self.draw_piece()

    def fits(self, rot, px, py):
        rows = self.rows
        for x, y in ROTATIONS[self.kind][rot][0]:
            x += px
            y += py
            if x < 0 or x >= COLS or y >= ROWS or (y >= 0 and rows[y] >> x & 1):
                return False
        return True

    def column_tops(self):
        """Row of the highest filled cell in every column (ROWS if empty)."""
        tops = [ROWS] * COLS
        covered = 0
        for y, row in enumerate(self.rows):
            new = row & ~covered
            while new:
                tops[LOW[new]] = y
                new &= new - 1
            covered |= row
        return tops

    def landing(self, rot, px):
        """y where the piece ends when dropped straight down from above."""
        tops = self.tops
        return min(tops[px + x] - 1 - bottom for x, bottom in ROTATIONS[self.kind][rot][1])

    # --- Computer player --------------------------------------------------------------

    def think(self):
        """Rates every column for one rotation; the piece waits meanwhile, one frame per rotation."""
        rot = SEARCH[self.kind][self.searched]
        cells, bottoms, top = ROTATIONS[self.kind][rot]
        calm = ROWS - min(self.tops) <= CALM - self.level // 2
        xs = [x for x, y in cells]
        for px in range(-min(xs), COLS - max(xs)):
            py = self.landing(rot, px)
            if py + top < 0:
                continue  # would stick out at the top
            rows = self.rows[:]
            for x, y in cells:
                rows[py + y] |= 1 << (px + x)
            full = [row for row in rows if row == FULL]
            if full:
                rows = [0] * len(full) + [row for row in rows if row != FULL]
            score = rate(rows, len(full), calm)
            if self.best_move is None or score > self.best_move[0]:
                self.best_move = (score, rot, px)
        self.searched += 1
        if self.searched == len(SEARCH[self.kind]):
            self.state = "move"

    def act(self):
        """One turn or shift towards the chosen spot; drops when there, or when blocked."""
        if self.best_move is None:
            self.dropping = True
            return
        score, rot, px = self.best_move
        if self.rot != rot:
            new = (self.rot + 1) & 3
            for kick in (0, -1, 1, -2, 2):
                if self.fits(new, self.px + kick, self.py):
                    self.rot = new
                    self.px += kick
                    return
            self.dropping = True
        elif self.px != px:
            step = 1 if px > self.px else -1
            if self.fits(self.rot, self.px + step, self.py):
                self.px += step
            else:
                self.dropping = True
        else:
            self.dropping = True

    def play(self, dt):
        moved = False
        if not self.dropping:
            self.action_time += dt
            if self.action_time >= ACTION:
                self.action_time -= ACTION
                self.act()
                moved = True
        self.fall_time += dt
        interval = 1 / SOFT_DROP if self.dropping else 1 / self.gravity()
        while self.fall_time >= interval:
            self.fall_time -= interval
            if self.fits(self.rot, self.px, self.py + 1):
                self.py += 1
                moved = True
            else:
                self.lock()
                return
        if moved:
            self.draw_piece()

    def gravity(self):
        return min(40.0, 0.9 * 1.42 ** (self.level - 1))  # rows per second

    def lock(self):
        self.erase_piece()
        cells = ROTATIONS[self.kind][self.rot][0]
        for x, y in cells:
            x += self.px
            y += self.py
            if y < 0:
                self.start_game_over()
                return
            self.rows[y] |= 1 << x
            self.colors[y * COLS + x] = self.kind + 1
            self.grid[x, y] = self.kind + 1
        self.full = [y for y in range(ROWS) if self.rows[y] == FULL]
        if self.full:
            for y in self.full:
                for x in range(COLS):
                    self.grid[x, y] = FLASH
            self.state = "clear"
            self.clock = 0.0
        else:
            self.spawn()

    # --- Animations -------------------------------------------------------------------

    def clearing(self, dt):
        """Full rows flash white, then vanish from the middle outwards, then the rest falls."""
        self.clock += dt
        gone = int((self.clock - 0.12) / 0.045)
        for k in range(min(gone, COLS // 2)):
            for y in self.full:
                self.grid[COLS // 2 - 1 - k, y] = 0
                self.grid[COLS // 2 + k, y] = 0
        if gone >= COLS // 2 + 1:
            count = len(self.full)
            keep = [y for y in range(ROWS) if y not in self.full]
            self.rows = [0] * count + [self.rows[y] for y in keep]
            colors = bytearray(COLS * count)
            for y in keep:
                colors += self.colors[y * COLS:(y + 1) * COLS]
            self.colors = colors
            self.redraw()
            self.lines += count
            self.score += SCORES[count] * self.level
            if count == 4:
                self.party = 1.6
            self.level = 1 + self.lines // 10
            self.show_values()
            self.spawn()

    def start_game_over(self):
        self.state = "over"
        self.clock = 0.0
        self.greyed = 0
        self.wiped = 0

    def game_over(self, dt):
        """The stack turns grey from the bottom up, waits, and is wiped away from the top."""
        self.clock += dt
        t = self.clock
        if t < 3.0:
            due = min(ROWS, int(t / 0.06) + 1)
            while self.greyed < due:
                y = ROWS - 1 - self.greyed
                for x in range(COLS):
                    if self.grid[x, y]:
                        self.grid[x, y] = GREY
                self.greyed += 1
        else:
            due = min(ROWS, int((t - 3.0) / 0.04) + 1)
            while self.wiped < due:
                for x in range(COLS):
                    self.grid[x, self.wiped] = 0
                self.wiped += 1
            if t > 3.0 + ROWS * 0.04 + 0.4:
                self.new_game()

    # --- Drawing ----------------------------------------------------------------------

    def redraw(self):
        grid = self.grid
        colors = self.colors
        for y in range(ROWS):
            for x in range(COLS):
                grid[x, y] = colors[y * COLS + x]

    def erase_piece(self):
        for x, y in self.drawn:
            self.grid[x, y] = self.colors[y * COLS + x]
        self.drawn = []

    def draw_piece(self):
        """Ghost at the landing spot, then the piece itself."""
        self.erase_piece()
        cells = ROTATIONS[self.kind][self.rot][0]
        ghost_y = self.py
        while self.fits(self.rot, self.px, ghost_y + 1):
            ghost_y += 1
        for py, tile in ((ghost_y, GHOST + self.kind + 1), (self.py, self.kind + 1)):
            for x, y in cells:
                x += self.px
                y += py
                if 0 <= y < ROWS:
                    self.grid[x, y] = tile
                    self.drawn.append((x, y))

    def show_next(self):
        cells = ROTATIONS[self.next][0][0]
        for x in range(4):
            for y in range(2):
                self.preview[x, y] = 0
        top = min(y for x, y in cells)
        width = max(x for x, y in cells) + 1
        for x, y in cells:
            self.preview[x, y - top] = self.next + 1
        self.preview.x = (21 - 2 * width) // 2

    def show_values(self):
        for label, value, x in zip(self.values, (self.level, self.lines, self.score), (0, 43, 43)):
            text = str(value)
            label.x = x + (21 - gfx.text_width(text)) // 2
            label.set(text)

    def frame(self, dt):
        if self.state == "think":
            self.think()
        elif self.state == "move":
            self.play(dt)
        elif self.state == "clear":
            self.clearing(dt)
        else:
            self.game_over(dt)
        if self.party > 0:
            # four lines at once: a rainbow runs through the frame, then it calms down again
            self.party = max(0.0, self.party - dt)
            fade = min(1.0, self.party / 0.5)
            self.hud_pal[FRAME] = gfx.mix(HUD[FRAME], gfx.hsv(self.party * 1.5), fade)
