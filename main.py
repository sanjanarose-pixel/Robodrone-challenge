import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageChops, ImageFilter, ImageOps
from ursina import *
from ursina.shaders import lit_with_shadows_shader, unlit_shader

# ==========================================
# HELPERS
# ==========================================
def C(r, g, b, a=255):
    """0-255 colour helper (works on every Ursina version)."""
    return Color(r / 255, g / 255, b / 255, a / 255)


# ==========================================
# PROCEDURAL TEXTURE GENERATION (runs once, saves PNGs to ./textures)
# ==========================================
TEX_DIR = Path(__file__).resolve().parent / 'textures'
TEX_DIR.mkdir(exist_ok=True)


def _noise(size, cell, sigma=60):
    small = Image.effect_noise((max(2, size // cell), max(2, size // cell)), sigma)
    return small.resize((size, size), Image.BICUBIC)


def _rand_color(lo, hi):
    return tuple(random.randint(a, b) for a, b in zip(lo, hi))


def gen_grass(path, size=512):
    base = Image.blend(_noise(size, 32), _noise(size, 2, 50), 0.35)
    base = ImageOps.autocontrast(base)
    img = ImageOps.colorize(base, (62, 112, 48), (140, 188, 92)).convert('RGB')
    d = ImageDraw.Draw(img)
    for _ in range(4000):
        x, y = random.randint(0, size - 1), random.randint(0, size - 1)
        l = random.randint(3, 7)
        col = _rand_color((50, 110, 40), (160, 210, 100))
        d.line((x, y, x + random.randint(-2, 2), y - l), fill=col)
    img.save(path)


def gen_concrete(path, size=256, lo=(140, 140, 142), hi=(205, 205, 205)):
    base = ImageOps.autocontrast(Image.blend(_noise(size, 16), _noise(size, 1, 40), 0.5))
    img = ImageOps.colorize(base, lo, hi).convert('RGB')
    d = ImageDraw.Draw(img)
    for _ in range(300):
        x, y = random.randint(0, size - 1), random.randint(0, size - 1)
        g = random.randint(110, 220)
        d.point((x, y), fill=(g, g, g))
    img.save(path)


def gen_road(path, size=256):
    base = ImageOps.autocontrast(Image.blend(_noise(size, 8), _noise(size, 1, 50), 0.5))
    img = ImageOps.colorize(base, (38, 38, 44), (84, 84, 92)).convert('RGB')
    d = ImageDraw.Draw(img)
    d.rectangle((6, 0, 10, size), fill=(225, 225, 225))               # edge lines
    d.rectangle((size - 11, 0, size - 7, size), fill=(225, 225, 225))
    d.rectangle((size // 2 - 4, 0, size // 2 + 3, size // 2 - 20), fill=(235, 200, 40))  # dashes
    img.save(path)


def gen_facade(path, wall, glass_top, glass_bot, lit_chance=0.25, size=256):
    base = ImageOps.autocontrast(Image.blend(_noise(size, 16), _noise(size, 1, 40), 0.4))
    img = ImageOps.colorize(base, tuple(int(c * 0.88) for c in wall), wall).convert('RGB')
    d = ImageDraw.Draw(img)
    n, cell = 4, size // 4
    for r in range(n):
        for c in range(n):
            x0, y0 = c * cell + 12, r * cell + 10
            x1, y1 = (c + 1) * cell - 12, (r + 1) * cell - 14
            d.rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), fill=(70, 74, 82))   # frame
            if random.random() < lit_chance:
                d.rectangle((x0, y0, x1, y1), fill=(255, 228, 150))
                continue
            for y in range(y0, y1 + 1):                                        # glass gradient
                t = (y - y0) / max(1, y1 - y0)
                col = tuple(int(a + (b - a) * t) for a, b in zip(glass_top, glass_bot))
                d.line((x0, y, x1, y), fill=col)
            d.line((x0, y0, x0 + 14, y0 + 14), fill=(230, 240, 250))           # glint
        d.rectangle((0, (r + 1) * cell - 6, size, (r + 1) * cell - 3), fill=tuple(int(c * 0.75) for c in wall))
    img.save(path)


def gen_pad(path, ring_col, mark='H', size=512):
    base = ImageOps.autocontrast(Image.blend(_noise(size, 16), _noise(size, 1, 40), 0.4))
    img = ImageOps.colorize(base, (120, 122, 126), (176, 178, 182)).convert('RGB')
    d = ImageDraw.Draw(img)
    m = size // 2
    d.rectangle((6, 6, size - 7, size - 7), outline=ring_col, width=10)          # border
    d.ellipse((40, 40, size - 41, size - 41), outline=(245, 245, 245), width=14)
    d.ellipse((60, 60, size - 61, size - 61), outline=ring_col, width=8)
    if mark == 'H':
        w = 22
        d.rectangle((m - 80, m - 105, m - 80 + w, m + 105), fill=(245, 245, 245))
        d.rectangle((m + 80 - w, m - 105, m + 80, m + 105), fill=(245, 245, 245))
        d.rectangle((m - 80, m - w // 2, m + 80, m + w // 2), fill=(245, 245, 245))
    else:  # target
        for i, rad in enumerate((110, 75, 40)):
            d.ellipse((m - rad, m - rad, m + rad, m + rad), fill=(245, 245, 245) if i % 2 == 0 else ring_col)
    img.save(path)


def gen_blob(path, size=128):
    g = ImageOps.invert(Image.radial_gradient('L').resize((size, size)))
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    img.putalpha(g.point(lambda v: int(v * 0.65)).filter(ImageFilter.GaussianBlur(2)))
    img.save(path)


def build_textures():
    random.seed(7)
    jobs = {
        'grass.png': lambda p: gen_grass(p),
        'concrete.png': lambda p: gen_concrete(p),
        'road.png': lambda p: gen_road(p),
        'facade_glass.png': lambda p: gen_facade(p, (214, 220, 230), (80, 125, 170), (170, 205, 235)),
        'facade_warm.png': lambda p: gen_facade(p, (226, 205, 178), (55, 70, 90), (110, 135, 160), 0.18),
        'pad_home.png': lambda p: gen_pad(p, (240, 190, 20), 'H'),
        'pad_b.png': lambda p: gen_pad(p, (40, 170, 190), 'T'),
        'blob.png': lambda p: gen_blob(p),
    }
    for name, fn in jobs.items():
        if not (TEX_DIR / name).exists():
            fn(TEX_DIR / name)


build_textures()


def tex(name):
    return Texture(TEX_DIR / name)


# ==========================================
# APP + CONSTANTS
# ==========================================
app = Ursina(title="Robodrone Flight Simulator", vsync=True)
window.borderless = False
window.show_ursina_splash = False
Texture.default_filtering = 'mipmap'
camera.clip_plane_far = 700

GRAVITY = 9.81
MAX_THROTTLE = 22.0
YAW_SPEED = 60.0
DRAG_COEFF = 1.2
MAX_DESCENT_SPEED = 4.5
MAX_LANDING_TILT = 15.0
PAD_B = (80, 80)

CYL = Cylinder(resolution=16, start=0, height=1)

# Shadows + lighting
Entity.default_shader = lit_with_shadows_shader
sun = DirectionalLight()
sun.shadow_map_resolution = (4096, 4096)
sun.look_at(Vec3(1, -1.2, -0.6))
sun.color = C(255, 244, 225)
AmbientLight(color=C(125, 135, 155))

# ==========================================
# WORLD
# ==========================================
T_GRASS, T_CONC, T_ROAD = tex('grass.png'), tex('concrete.png'), tex('road.png')
T_GLASS, T_WARM = tex('facade_glass.png'), tex('facade_warm.png')

Entity(model='plane', scale=(800, 1, 800), texture=T_GRASS, texture_scale=(200, 200), color=C(255, 255, 255))

# Road connecting the two pads
road_len = math.hypot(*PAD_B)
Entity(model='plane', position=(PAD_B[0] / 2, 0.02, PAD_B[1] / 2), rotation_y=45,
       scale=(8, 1, road_len), texture=T_ROAD, texture_scale=(1, road_len / 12))

# Landing pads
for pos, name in (((0, 0), 'pad_home.png'), (PAD_B, 'pad_b.png')):
    Entity(model='cube', position=(pos[0], 0.08, pos[1]), scale=(11, 0.16, 11), texture=tex(name))

obstacles = []   # (x, z, half_x, half_z, height)
random.seed(42)

# Buildings
placed = []
for _ in range(60):
    if len(placed) >= 30:
        break
    bx, bz = random.uniform(-130, 130), random.uniform(-130, 130)
    if math.hypot(bx, bz) < 18 or math.hypot(bx - PAD_B[0], bz - PAD_B[1]) < 18:
        continue
    if abs(bx - bz) / 1.414 < 12 and -10 < bx < 90:            # keep the road clear
        continue
    if any(math.hypot(bx - px, bz - pz) < 20 for px, pz in placed):
        continue
    bw, bh, bd = random.uniform(7, 14), random.uniform(10, 38), random.uniform(7, 14)
    placed.append((bx, bz))
    Entity(model='cube', position=(bx, bh / 2, bz), scale=(bw, bh, bd),
           texture=random.choice((T_GLASS, T_WARM)),
           texture_scale=(max(1, round(bw / 6)), max(1, round(bh / 6))),
           color=random.choice((C(255, 255, 255), C(245, 238, 230), C(232, 240, 252))))
    Entity(model='cube', position=(bx, bh + 0.15, bz), scale=(bw + 0.5, 0.3, bd + 0.5),
           texture=T_CONC, texture_scale=(bw / 4, bd / 4), color=C(200, 200, 205))
    Entity(model='cube', position=(bx + random.uniform(-2, 2), bh + 1, bz + random.uniform(-2, 2)),
           scale=(2.2, 1.6, 2.2), color=C(150, 155, 160))
    obstacles.append((bx, bz, bw / 2 + 0.8, bd / 2 + 0.8, bh + 0.3))

# Trees
for _ in range(120):
    tx, tz = random.uniform(-160, 160), random.uniform(-160, 160)
    if math.hypot(tx, tz) < 12 or math.hypot(tx - PAD_B[0], tz - PAD_B[1]) < 12:
        continue
    if abs(tx - tz) / 1.414 < 7 and -10 < tx < 90:
        continue
    if any(abs(tx - o[0]) < o[2] + 3 and abs(tz - o[1]) < o[3] + 3 for o in obstacles):
        continue
    s = random.uniform(0.9, 1.7)
    trunk_h = 2.2 * s
    Entity(model=CYL, position=(tx, 0, tz), scale=(0.5 * s, trunk_h, 0.5 * s), color=C(105, 75, 48))
    g = random.randint(0, 40)
    Entity(model='sphere', position=(tx, trunk_h + 1.2 * s, tz), scale=(3.4 * s, 3.0 * s, 3.4 * s),
           color=C(40 + g, 120 + g, 55))
    Entity(model='sphere', position=(tx, trunk_h + 2.6 * s, tz), scale=(2.4 * s, 2.2 * s, 2.4 * s),
           color=C(55 + g, 140 + g, 65))
    obstacles.append((tx, tz, 1.5 * s, 1.5 * s, trunk_h + 3.6 * s))


# Rings (procedural torus)
def make_torus(R=1.0, r=0.07, seg=40, sides=10):
    verts, uvs, norms, tris = [], [], [], []
    for i in range(seg + 1):
        a = i / seg * 2 * math.pi
        ca, sa = math.cos(a), math.sin(a)
        for j in range(sides + 1):
            b = j / sides * 2 * math.pi
            cb, sb = math.cos(b), math.sin(b)
            verts.append(((R + r * cb) * ca, (R + r * cb) * sa, r * sb))
            norms.append((cb * ca, cb * sa, sb))
            uvs.append((i / seg, j / sides))
    for i in range(seg):
        for j in range(sides):
            a, b = i * (sides + 1) + j, (i + 1) * (sides + 1) + j
            tris += [a, b, b + 1, a, b + 1, a + 1]
    return Mesh(vertices=verts, triangles=tris, uvs=uvs, normals=norms, mode='triangle')


TORUS = make_torus()
RING_COLOR = C(255, 150, 20)
ring_positions = [
    (10, 5, 20), (-20, 8, 40), (30, 12, 60), (60, 15, 30),
    (75, 10, 60), (40, 7, -30), (-40, 10, -20), (-10, 6, 60)
]
rings = []
for i, pos in enumerate(ring_positions):
    nxt = ring_positions[(i + 1) % len(ring_positions)]
    yaw = math.degrees(math.atan2(nxt[0] - pos[0], nxt[2] - pos[2]))
    r = Entity(model=TORUS, position=pos, scale=4, rotation_y=yaw, color=RING_COLOR,
               shader=unlit_shader, double_sided=True)
    r.passed = False
    rings.append(r)

# Shadow bounds have to be fit before the giant sky sphere exists
try:
    sun.update_bounds(entity=scene)
except Exception:
    pass

sky = Sky()
try:
    sky.setFogOff(1)
except Exception:
    pass
scene.fog_color = C(205, 228, 246)
scene.fog_density = (90, 380)

# ==========================================
# DRONE
# ==========================================
class Drone(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        BLACK, DARK, GREY = C(22, 22, 26), C(38, 38, 44), C(70, 72, 80)
        self.parts = []
        self.t = 0.0

        def part(**kw):
            e = Entity(parent=self, **kw)
            self.parts.append(e)
            return e

        # Fuselage
        part(model='cube', scale=(0.85, 0.2, 1.3), color=BLACK)
        part(model='cube', scale=(0.6, 0.16, 0.95), position=(0, 0.16, -0.05), color=DARK)
        part(model='cube', scale=(0.5, 0.12, 0.6), position=(0, -0.15, -0.1), color=GREY)   # battery
        part(model='cube', scale=(0.12, 0.05, 0.3), position=(0, 0.26, 0.15), color=C(230, 60, 40))  # stripe
        # Camera gimbal
        part(model='sphere', scale=0.3, position=(0, -0.12, 0.6), color=BLACK)
        part(model='sphere', scale=0.13, position=(0, -0.12, 0.74), color=C(60, 130, 220), shader=unlit_shader)
        # Landing legs
        for sx in (-1, 1):
            part(model='cube', scale=(0.06, 0.06, 1.0), position=(sx * 0.45, -0.42, 0), color=BLACK)
            for sz in (-1, 1):
                part(model='cube', scale=(0.06, 0.35, 0.06), position=(sx * 0.45, -0.25, sz * 0.4),
                     rotation_z=sx * -12, color=BLACK)

        # Arms, motors, propellers, LEDs
        self.spinners, self.discs, self.leds = [], [], []
        for sx in (-1, 1):
            for sz in (-1, 1):
                yaw = math.degrees(math.atan2(sx, sz))
                part(model='cube', scale=(0.16, 0.08, 1.4), position=(sx * 0.5, 0, sz * 0.5),
                     rotation_y=yaw, color=DARK)
                part(model=CYL, scale=(0.24, 0.16, 0.24), position=(sx, 0.02, sz), color=GREY)
                spin = part(position=(sx, 0.2, sz))
                for ang in (0, 90):
                    Entity(parent=spin, model='cube', scale=(1.05, 0.015, 0.09), rotation_y=ang, color=C(210, 210, 215))
                Entity(parent=spin, model='sphere', scale=0.12, color=C(230, 60, 40) if sz > 0 else C(230, 230, 230))
                self.spinners.append(spin)
                disc = part(model=CYL, scale=(1.1, 0.004, 1.1), position=(sx, 0.21, sz),
                            color=Color(0.8, 0.8, 0.8, 0), shader=unlit_shader)
                self.discs.append(disc)
                led = part(model='sphere', scale=0.09, position=(sx * 1.05, -0.05, sz * 1.05),
                           color=C(255, 40, 40) if sz > 0 else C(60, 255, 90), shader=unlit_shader)
                self.leds.append(led)

        self.reset_state()

    def set_visibility(self, visible):
        for p in self.parts:
            p.enabled = visible

    def reset_state(self):
        self.position = (0, 0.3, 0)
        self.rotation = (0, 0, 0)
        self.velocity = Vec3(0, 0, 0)
        self.throttle = 0.0
        self.is_crashed = False
        self.score = 0
        self.bonus_taken = False
        for r in rings:
            r.passed = False
            r.color = RING_COLOR

    def update(self):
        self.t += time.dt
        blink = 1.0 if math.sin(self.t * 9) > 0 else 0.25
        for led in self.leds:
            led.alpha = blink
        if self.is_crashed:
            return

        # Throttle
        if held_keys['space']:
            self.throttle = min(self.throttle + 1.5 * time.dt, 1.0)
        elif held_keys['left shift']:
            self.throttle = max(self.throttle - 1.5 * time.dt, 0.0)
        else:
            self.throttle = max(self.throttle - 2.0 * time.dt, 0.0)

        # Rotor animation (blades fade into a blurred disc as speed rises)
        for i, s in enumerate(self.spinners):
            s.rotation_y += self.throttle * 2200 * time.dt * (1 if i % 2 else -1)
            for child in s.children:
                if child.model and child.scale_x > 0.5:
                    child.alpha = max(0.25, 1 - self.throttle * 0.8)
            self.discs[i].alpha = self.throttle * 0.35

        # Attitude
        pitch_input = held_keys['w'] - held_keys['s']
        roll_input = held_keys['d'] - held_keys['a']
        yaw_input = held_keys['e'] - held_keys['q']
        self.rotation_x = lerp(self.rotation_x, pitch_input * 25.0, time.dt * 4)
        self.rotation_z = lerp(self.rotation_z, -roll_input * 25.0, time.dt * 4)
        self.rotation_y += yaw_input * YAW_SPEED * time.dt

        # Physics
        thrust = self.up * (self.throttle * MAX_THROTTLE)
        acc = thrust + Vec3(0, -GRAVITY, 0) - self.velocity * DRAG_COEFF
        self.velocity += acc * time.dt
        self.position += self.velocity * time.dt

        # Ground
        if self.y <= 0.3:
            self.y = 0.3
            tilt = math.sqrt(self.rotation_x ** 2 + self.rotation_z ** 2)
            if abs(self.velocity.y) > MAX_DESCENT_SPEED or tilt > MAX_LANDING_TILT:
                self.crash("Hard Landing / Heavy Tilt Landing!")
                return
            self.velocity = Vec3(0, 0, 0)
            if not self.bonus_taken and math.hypot(self.x - PAD_B[0], self.z - PAD_B[1]) < 5.0:
                self.bonus_taken = True
                self.score += 500
                hud_status.text = "Perfect landing on Pad B!  +500"
                hud_status.color = C(30, 140, 60)

        # Obstacles (buildings + trees)
        for ox, oz, hx, hz, h in obstacles:
            if abs(self.x - ox) < hx + 0.8 and abs(self.z - oz) < hz + 0.8 and self.y < h:
                self.crash("Collision!")
                return

        # Rings
        for ring in rings:
            if not ring.passed and distance(self.position, ring.position) < 3.3:
                ring.passed = True
                ring.color = C(60, 230, 90)
                self.score += 100

    def crash(self, reason):
        self.is_crashed = True
        self.velocity = Vec3(0, 0, 0)
        for s in self.discs:
            s.alpha = 0
        hud_status.text = f"CRASHED: {reason}  [Press R to reset]"
        hud_status.color = C(220, 40, 40)


drone = Drone()

# Soft blob shadow under the drone (readable at any altitude)
blob = Entity(model='quad', texture=tex('blob.png'), rotation_x=90, scale=4, y=0.2,
              shader=unlit_shader, double_sided=True)

# ==========================================
# CAMERA
# ==========================================
camera_mode = 0   # 0 chase, 1 FPV, 2 high orbit


def set_camera_mode(mode):
    global camera_mode
    camera_mode = mode
    drone.set_visibility(mode != 1)
    if mode == 1:
        camera.parent = drone
        camera.position = Vec3(0, 0.2, 0.6)
        camera.rotation = Vec3(0, 0, 0)
        camera.fov = 100
    else:
        camera.parent = scene
        camera.fov = 80
    crosshair.enabled = (mode == 1)


def update_camera():
    if camera_mode == 0:
        yaw = math.radians(drone.rotation_y)
        back = Vec3(math.sin(yaw), 0, math.cos(yaw))
        target = drone.position - back * 9 + Vec3(0, 3.5, 0)
        camera.position = lerp(camera.position, target, min(1, time.dt * 5))
        camera.look_at(drone.position + Vec3(0, 1, 0))
    elif camera_mode == 2:
        camera.position = drone.position + Vec3(0, 28, -28)
        camera.look_at(drone.position)


# ==========================================
# HUD
# ==========================================
def panel(x, y, w, h):
    return Entity(parent=camera.ui, model='quad', position=(x, y, 1), scale=(w, h), color=C(10, 15, 25, 150))


panel(-0.68, 0.385, 0.34, 0.2)
panel(0.60, 0.33, 0.46, 0.31)
hud_info = Text(text='', position=(-0.84, 0.47), scale=1.1, color=color.white)
hud_status = Text(text='', origin=(0, 0), position=(0, 0.25), scale=1.6, color=color.red)
hud_help = Text(
    text="CONTROLS\nSpace (hold): Throttle Up\nShift (hold): Throttle Down\nW/S: Pitch   A/D: Roll   Q/E: Yaw\nC: Camera   R: Reset   H: Hide Help\n\nFly the rings, then land softly on the cyan pad.",
    position=(0.38, 0.47), scale=0.75, color=color.white)
crosshair = Text(text='+', origin=(0, 0), scale=2, color=C(255, 255, 255, 180))
set_camera_mode(0)


def input(key):
    if key == 'c':
        set_camera_mode((camera_mode + 1) % 3)
    if key == 'r':
        drone.reset_state()
        hud_status.text = ""
    if key == 'h':
        hud_help.enabled = not hud_help.enabled


def update():
    update_camera()
    blob.position = (drone.x, 0.2, drone.z)
    blob.scale = 3.5 + drone.y * 0.12
    blob.alpha = max(0.15, 1 - drone.y / 45)

    done = sum(r.passed for r in rings)
    if done == len(rings) and not drone.is_crashed and not hud_status.text:
        hud_status.text = "All rings cleared! Land on the cyan pad."
        hud_status.color = C(30, 140, 60)
    hud_info.text = (
        f"Altitude: {max(0, drone.y - 0.3):.1f} m\n"
        f"Speed:    {drone.velocity.length():.1f} m/s\n"
        f"Throttle: {int(drone.throttle * 100)}%\n"
        f"Rings:    {done}/{len(rings)}\n"
        f"Score:    {drone.score}"
    )


app.run()
