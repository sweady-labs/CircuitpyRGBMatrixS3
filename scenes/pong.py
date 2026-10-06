"""Pong: two computer players rally a ball with a glowing trail; 7 points win the set.

The players are good but not perfect on purpose. Each one guesses where the ball will arrive,
refines the guess while the ball comes closer and keeps a small error that grows with the speed of
the ball; the paddles also have a top speed. So the rallies get faster until somebody misses.
The ball takes the color of the paddle that hit it last.
"""
import math
import random

import displayio
import vectorio

from app import gfx

FPS = 40
PREVIEW_AT = 2.2
WIN = 7  # points that win a set
SIZE = 2  # the ball is SIZE x SIZE pixels
PADDLE = 7  # paddle height, the paddles are 2 pixels wide
LEFT_X, RIGHT_X = 1, 61
LEFT_FACE, RIGHT_FACE = LEFT_X + 2, RIGHT_X - SIZE  # ball x where it touches a paddle
PADDLE_SPEED = 34.0  # pixels per second
START_SPEED, MAX_SPEED = 32.0, 74.0  # ball, pixels per second
TRAIL = 6
TOP = 32 - SIZE  # lowest y of the ball

COLORS = (0x00D8FF, 0xFF3C8E)  # left, right
NET = 0x2E3346
DASH, GOAL_LEFT, GOAL_RIGHT = 1, 2, 3  # canvas palette, 0 is black

# paddles: the side facing the field is lighter, the ends are darker, so they look rounded
PADDLE_ART = ("ss",) + ("bl",) * (PADDLE - 2) + ("ss",)
PADDLE_KEYS = {".": 0, "b": 1, "l": 2, "s": 3}


class Scene:
    def __init__(self, group, settings):
        # net and the two goal lines, which glow up when a point is scored
        self.bitmap, self.pal = gfx.canvas(group, [0, NET, 0, 0])
        for y in range(0, 32, 4):
            for x, dy in ((31, 0), (32, 0), (31, 1), (32, 1)):
                self.bitmap[x, y + dy] = DASH
        for y in range(32):
            self.bitmap[0, y] = GOAL_LEFT
            self.bitmap[63, y] = GOAL_RIGHT

        self.labels = (gfx.Label(group, "0", 0, 26, 1), gfx.Label(group, "0", 0, 35, 1))

        # the trail behind the ball: one square per trail step, darker and darker
        self.trail_pal = gfx.Pal([0] * (TRAIL + 1))
        self.trail = []
        for i in range(TRAIL):
            square = vectorio.Rectangle(pixel_shader=self.trail_pal.palette, width=SIZE, height=SIZE,
                                        x=-10, y=0, color_index=TRAIL - i)
            group.append(square)
            self.trail.append(square)

        self.paddle_pals = []
        self.paddles = []
        for side, x in ((0, LEFT_X), (1, RIGHT_X)):
            rows = PADDLE_ART if side == 0 else ["".join(reversed(row)) for row in PADDLE_ART]
            pal = gfx.Pal([0, 0, 0, 0], transparent=(0,))
            grid = displayio.TileGrid(gfx.art_bitmap(rows, PADDLE_KEYS), pixel_shader=pal.palette, x=x, y=12)
            group.append(grid)
            self.paddle_pals.append(pal)
            self.paddles.append(grid)
        self.ball_pal = gfx.Pal([0, 0xFFFFFF])
        self.ball = vectorio.Rectangle(pixel_shader=self.ball_pal.palette, width=SIZE, height=SIZE, x=-10, y=0,
                                       color_index=1)
        group.append(self.ball)

        self.paddle_y = [12.5, 12.5]
        self.flash = [0.0, 0.0]  # paddle lights up when it hits the ball
        self.score = [0, 0]
        self.glow = [0.0, 0.0]  # goal line glow per side, 1.0 right after a point
        self.history = []
        self.hitter = random.randrange(2)
        self.winner = None
        self.phase = 0.0
        for side in (0, 1):
            self.paint_paddle(side, 0.0)
        self.trail_colors()
        self.serve(self.hitter)
        self.show_scores()

    # --- Rules ------------------------------------------------------------------------

    def serve(self, toward):
        """Ball waits in the middle, then starts towards the player `toward` (0 left, 1 right)."""
        self.x = 31.0
        self.y = random.uniform(8, 22)
        angle = random.uniform(-0.45, 0.45)
        self.speed = START_SPEED
        self.vx = math.cos(angle) * self.speed * (-1 if toward == 0 else 1)
        self.vy = math.sin(angle) * self.speed
        self.wait = 1.4
        self.history = []
        self.new_guess()

    def new_guess(self):
        """How the player the ball is coming to will misjudge it: a wobble that fades out while the
        ball comes closer, and an aim that stays. The aim is mostly on purpose (hitting the ball with
        the edge of the paddle gives an angle), the rest is error that grows with the ball speed."""
        fast = (self.speed - START_SPEED) / (MAX_SPEED - START_SPEED)
        self.wobble = random.uniform(-9.0, 9.0)
        self.aim = random.uniform(-2.4, 2.4) + random.uniform(-1.0, 1.0) * (1.0 + 5.5 * fast)
        if random.random() < 0.06:  # now and then a player misjudges completely, so some points come early
            self.aim += random.choice((-1, 1)) * random.uniform(4.0, 7.0)

    def arrival(self, face):
        """y of the ball when it reaches x = face, bouncing off top and bottom."""
        y = self.y + self.vy * (face - self.x) / self.vx
        y = y % (2 * TOP)
        return 2 * TOP - y if y > TOP else y

    def hit(self, side, ball_y):
        top = int(self.paddle_y[side] + 0.5)
        y = int(ball_y + 0.5)
        return y + SIZE > top and y < top + PADDLE

    def bounce(self, side, ball_y):
        # where the ball meets the paddle decides the angle: the edges send it away steeply
        offset = (ball_y + SIZE / 2 - self.paddle_y[side] - PADDLE / 2) / (PADDLE / 2 + SIZE / 2)
        angle = max(-1.0, min(1.0, offset)) * 0.9 + random.uniform(-0.12, 0.12)
        self.speed = min(MAX_SPEED, self.speed * 1.07)
        self.vx = math.cos(angle) * self.speed * (1 if side == 0 else -1)
        self.vy = math.sin(angle) * self.speed
        self.hitter = side
        self.flash[side] = 1.0
        self.trail_colors()
        self.new_guess()

    def point(self, side):
        self.score[side] += 1
        self.glow[1 - side] = 1.0
        self.show_scores()
        if self.score[side] >= WIN:
            self.winner = side
            self.wait = 5.0
        else:
            self.serve(1 - side)

    # --- Frames -----------------------------------------------------------------------

    def frame(self, dt):
        self.phase += dt
        if self.wait > 0:
            self.wait -= dt
            if self.wait <= 0 and self.winner is not None:
                self.new_set()
        else:
            self.move_ball(dt)
        self.move_paddles(dt)
        self.draw(dt)

    def new_set(self):
        winner = self.winner
        self.winner = None
        self.score = [0, 0]
        self.paint_paddle(winner, 0.0)
        self.show_scores()
        self.serve(random.randrange(2))

    def move_ball(self, dt):
        x = self.x + self.vx * dt
        y = self.y + self.vy * dt
        if y < 0:
            y, self.vy = -y, -self.vy
        elif y > TOP:
            y, self.vy = 2 * TOP - y, -self.vy
        if self.vx < 0 and self.x >= LEFT_FACE > x and self.hit(0, y):
            x = 2 * LEFT_FACE - x
            self.bounce(0, y)
        elif self.vx > 0 and self.x <= RIGHT_FACE < x and self.hit(1, y):
            x = 2 * RIGHT_FACE - x
            self.bounce(1, y)
        self.x, self.y = x, y
        if x < -SIZE - 3:
            self.point(1)
        elif x > 64 + 3:
            self.point(0)

    def move_paddles(self, dt):
        for side in (0, 1):
            coming = self.wait <= 0 and (self.vx < 0) == (side == 0)
            if coming:
                face = LEFT_FACE if side == 0 else RIGHT_FACE
                distance = abs(face - self.x)
                guess = self.arrival(face) + self.aim + self.wobble * min(1.0, distance / 56)
                target = guess + SIZE / 2 - PADDLE / 2
                speed = PADDLE_SPEED
            else:
                target = 16 - PADDLE / 2  # back to the middle, without hurry
                speed = PADDLE_SPEED * 0.35
            step = max(-speed * dt, min(speed * dt, target - self.paddle_y[side]))
            self.paddle_y[side] = max(0.0, min(32.0 - PADDLE, self.paddle_y[side] + step))

    def draw(self, dt):
        for side in (0, 1):
            self.paddles[side].y = int(self.paddle_y[side] + 0.5)
            if self.flash[side] > 0:
                self.flash[side] = max(0.0, self.flash[side] - dt * 5)
                self.paint_paddle(side, self.flash[side] * 0.7)
        ball_visible = self.winner is None and (self.wait <= 0 or self.wait < 0.8 and self.wait % 0.4 > 0.15)
        bx, by = int(self.x + 0.5), int(self.y + 0.5)
        self.ball.x = bx if ball_visible else -10
        self.ball.y = by

        # trail: a position every 2 pixels of the way, so it looks the same at every speed
        if self.wait <= 0:
            last = self.history[-1] if self.history else (-99, 0)
            if abs(bx - last[0]) + abs(by - last[1]) >= 2:
                self.history.append((bx, by))
                if len(self.history) > TRAIL:
                    self.history.pop(0)
        for i, square in enumerate(self.trail):
            k = len(self.history) - 1 - i
            if k >= 0 and ball_visible:
                square.x, square.y = self.history[k]
            else:
                square.x = -10

        # goal lines fade out after a point
        for side, index in ((0, GOAL_LEFT), (1, GOAL_RIGHT)):
            if self.glow[side] > 0:
                self.glow[side] = max(0.0, self.glow[side] - dt * 1.2)
                self.pal[index] = gfx.scale(COLORS[1 - side], self.glow[side] ** 2)

        # the winner of a set pulses until the next set starts
        if self.winner is not None:
            pulse = 0.5 + 0.5 * math.cos(self.phase * 4.0)
            self.paint_paddle(self.winner, pulse * 0.6)
            self.labels[self.winner].set(str(self.score[self.winner]),
                                         gfx.mix(COLORS[self.winner], 0xFFFFFF, pulse * 0.6))

    def paint_paddle(self, side, white):
        color = gfx.mix(COLORS[side], 0xFFFFFF, white)
        pal = self.paddle_pals[side]
        pal[1] = color
        pal[2] = gfx.mix(color, 0xFFFFFF, 0.4)
        pal[3] = gfx.scale(color, 0.6)

    def trail_colors(self):
        color = COLORS[self.hitter]
        self.ball_pal[1] = gfx.mix(0xFFFFFF, color, 0.25)
        for i in range(1, TRAIL + 1):
            self.trail_pal[i] = gfx.scale(color, (i / (TRAIL + 1)) ** 1.6 * 0.9)

    def show_scores(self):
        for side in (0, 1):
            text = str(self.score[side])
            label = self.labels[side]
            label.x = 30 - gfx.text_width(text) if side == 0 else 35
            label.set(text, gfx.scale(COLORS[side], 0.6))
