"""Strange Things: the alphabet wall with fairy lights from an '80s mystery series.

Letters painted on old wallpaper, a string of colored bulbs above them. One bulb after the other
lights up and spells a word, as if someone from the other side were talking. Between the words
the lights flicker restlessly and the wall glows red. Everything is palette animation: every
letter has its own entries for its bulb, the glow around it and the paint, so lighting a bulb
means a few color changes and no drawing at all.
"""
import math
import random

from app import font, gfx

FPS = 25
PREVIEW_AT = 2.0
WORDS = ("HALLO", "HIER", "LAUF", "RUN", "HILFE", "ICH BIN HIER", "KOMM HEIM")
LETTERS = ("ABCDEFGH", "IJKLMNOPQ", "RSTUVWXYZ")
TOPS = (0, 11, 22)  # y of the wire in each row: wire, two rows of bulb, then the letter
LIT = 0.95  # seconds a letter stays lit while spelling
GAP = 0.45  # dark pause between two letters
SPACE = 1.2  # pause for a space between words

# fairy light colors, in a fixed mixed order along the string
BULBS = (0xFF2A1E, 0x2AE84A, 0x3A6CFF, 0xFFA81E, 0xFF3CA0, 0x22D8D0)
ORDER = (0, 3, 1, 4, 2, 5, 3, 0, 2, 4, 1, 5, 0, 2, 3, 1, 4, 0, 5, 2, 3, 4, 1, 0, 5, 3)
WALL = 0x000000  # the wallpaper is dark, only its pattern shows a little
PATTERN = 0x34320E
PAINT = 0x544C3E  # letters, painted in a dull cream
WIRE = 0x163A18
SOCKET = 0x3A4434
UPSIDE_DOWN = 0x48060A  # the red glow of the other side

# palette: 0 wall, 1 pattern, 2 wire, 3 socket, then four entries per letter
WALL_I, PATTERN_I, WIRE_I, SOCKET_I = 0, 1, 2, 3
PAINT_I, GLASS_I, NEAR_I, FAR_I = 0, 1, 2, 3  # offsets inside the four entries of a letter


def entry(letter, part):
    return 4 + 4 * letter + part


class Scene:
    def __init__(self, group, settings):
        self.bitmap, self.pal = gfx.canvas(group, [0] * (4 + 4 * 26))
        self.draw_wall()
        self.level = [0.0] * 26  # brightness of every bulb, 0 off .. 1 on
        self.target = [0.0] * 26
        self.shown = [-1.0] * 26  # level the palette shows right now
        self.red = 0.0  # red glow of the wall, 0..1
        self.red_target = 0.0
        self.wall_color = WALL
        self.word = ""
        self.phase = "dark"
        self.clock = 1.0  # first word after a second
        self.flicker_time = 0.0
        self.paint_wall()

    # --- The wall ---------------------------------------------------------------------

    def draw_wall(self):
        b = self.bitmap
        # wallpaper: a quiet lattice of small diamonds
        for y in range(1, 32, 4):
            for x in range((y // 4 % 2) * 4 + 1, 64, 8):
                for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                    if 0 <= x + dx < 64 and 0 <= y + dy < 32:
                        b[x + dx, y + dy] = PATTERN_I
        for row, (letters, top) in enumerate(zip(LETTERS, TOPS)):
            slot = 64 / len(letters)
            centers = [int(slot * (i + 0.5)) for i in range(len(letters))]
            # glow rings around the bulbs first, everything else is drawn over them
            for letter_char, cx in zip(letters, centers):
                letter = ord(letter_char) - 65
                gy = top + 1
                for y in range(gy - 3, gy + 5):
                    for x in range(cx - 4, cx + 4):
                        d = math.sqrt((x + 0.5 - cx) ** 2 + (y + 0.5 - gy - 1) ** 2)
                        if 0 <= x < 64 and 0 <= y < 32 and d <= 3.3:
                            b[x, y] = entry(letter, NEAR_I if d <= 2.2 else FAR_I)
            # the wire sags a little between the bulbs
            for x in range(64):
                near = min(abs(x - cx) for cx in centers)
                b[x, top + (1 if near >= 3 else 0)] = WIRE_I
            for letter_char, cx in zip(letters, centers):
                letter = ord(letter_char) - 65
                gy = top + 1
                b[cx - 1, top] = SOCKET_I
                b[cx, top] = SOCKET_I
                for x, y in ((cx - 1, gy), (cx, gy), (cx - 1, gy + 1), (cx, gy + 1)):
                    b[x, y] = entry(letter, GLASS_I)
                width = font.glyph(letter_char)[0]
                gfx.draw_text(b, letter_char, cx - (width + 1) // 2, top + 3, entry(letter, PAINT_I))

    def paint_wall(self):
        """Wall colors with the current red glow; the glow rings of dark bulbs look like wall."""
        self.wall_color = gfx.mix(WALL, UPSIDE_DOWN, self.red)
        self.pal[WALL_I] = self.wall_color
        self.pal[PATTERN_I] = gfx.mix(PATTERN, UPSIDE_DOWN, self.red * 0.8)
        self.pal[WIRE_I] = gfx.mix(WIRE, UPSIDE_DOWN, self.red * 0.5)
        self.pal[SOCKET_I] = gfx.mix(SOCKET, UPSIDE_DOWN, self.red * 0.5)
        self.shown = [-1.0] * 26  # all letters need their glow recomputed

    def paint_letter(self, letter, level):
        color = BULBS[ORDER[letter]]
        pal = self.pal
        glow = level * level  # light looks stronger towards full power
        pal[entry(letter, GLASS_I)] = gfx.mix(gfx.scale(color, 0.3), gfx.mix(color, 0xFFFFFF, 0.25), level)
        pal[entry(letter, NEAR_I)] = gfx.mix(self.wall_color, color, 0.55 * glow)
        pal[entry(letter, FAR_I)] = gfx.mix(self.wall_color, color, 0.25 * glow)
        paint = gfx.mix(PAINT, UPSIDE_DOWN, self.red * 0.4)
        pal[entry(letter, PAINT_I)] = gfx.mix(paint, gfx.mix(color, 0xFFFFFF, 0.3), glow)

    # --- Story ------------------------------------------------------------------------

    def next_word(self):
        word = random.choice(WORDS)
        while word == self.word:
            word = random.choice(WORDS)
        self.word = word
        self.pos = 0
        self.phase = "spell"
        self.clock = 0.0

    def spell(self):
        """One letter after the other: on for LIT seconds, then dark for GAP seconds."""
        char = self.word[self.pos]
        pause = SPACE if char == " " else LIT + GAP
        if char != " ":
            # a lit bulb flutters a little, as if the current came from far away
            self.target[ord(char) - 65] = random.uniform(0.8, 1.0) if self.clock < LIT else 0.0
        if self.clock >= pause:
            self.clock = 0.0
            self.pos += 1
            if self.pos == len(self.word):
                self.phase = "after"

    def flicker(self):
        """Restless lights: every bulb jumps to a random brightness now and then; the red glow
        of the wall wanders."""
        for letter in range(26):
            if random.random() < 0.05:
                self.target[letter] = random.choice((0.0, 0.0, 0.0, 0.3, 0.6, 1.0))
        if random.random() < 0.08:
            self.red_target = random.uniform(0.3, 1.0)

    def frame(self, dt):
        self.clock += dt
        if self.phase == "dark" and self.clock > 1.5:
            self.next_word()
        elif self.phase == "spell":
            self.spell()
        elif self.phase == "after" and self.clock > 1.4:
            self.phase = "flicker"
            self.clock = 0.0
            self.flicker_time = random.uniform(3.5, 6.0)
        elif self.phase == "flicker":
            if self.clock < self.flicker_time:
                self.flicker()
            else:
                self.target = [0.0] * 26
                self.red_target = 0.0
                self.phase = "dark"
                self.clock = 0.0

        # the red glow follows slowly; bulbs come on fast and go out a bit slower, like filaments
        if abs(self.red - self.red_target) > 0.01:
            step = dt * 1.5
            self.red += max(-step, min(step, self.red_target - self.red))
            self.paint_wall()
        for letter in range(26):
            level, target = self.level[letter], self.target[letter]
            if level != target:
                if target > level:
                    level = min(target, level + dt * 10.0)
                else:
                    level = max(target, level - dt * 4.0)
                self.level[letter] = level
            if abs(self.shown[letter] - level) > 0.004:
                self.shown[letter] = level
                self.paint_letter(letter, level)
