import math
import random
from ursina import *

# Initialize Ursina app
app = Ursina(title="Robodrone Flight Simulator", vsync=True)
window.borderless = False
window.show_ursina_splash = False

# ==========================================
# SIMULATION / PHYSICS CONSTANTS
# ==========================================
GRAVITY = 9.81
MAX_THROTTLE = 22.0
PITCH_SPEED = 45.0
ROLL_SPEED = 45.0
YAW_SPEED = 60.0
DRAG_COEFF = 1.2
MAX_DESCENT_SPEED = 4.5
MAX_LANDING_TILT = 15.0

# Procedural Mesh Fallbacks
CYLINDER_MESH = Cylinder(resolution=16, start=0, height=1)
TORUS_MESH = Pipe(path=(Vec3(0, 0, 0), Vec3(0, 0.1, 0)), thicknesses=((1.8, 2.0), (1.8, 2.0)))

# ==========================================
# WORLD SETUP (Light Environment, Dark Shadows)
# ==========================================
# Bright grass ground
Entity(model='plane', scale=(300, 1, 300), color=color.rgb(200, 230, 180), texture='white_cube', texture_scale=(100, 100))

# Atmosphere & Direct Light (Dark crisp shadows)
Sky(color=color.rgb(180, 220, 255))
sun = DirectionalLight(y=4, x=2, z=-2, shadows=True)
sun.shadow_map_resolution = (2048, 2048)
sun.color = color.white

# Ambient Fill Light so shadows stay readable
AmbientLight(color=color.rgb(120, 130, 150))

# Landing Pads (Light Bright Colors)
home_pad = Entity(model=CYLINDER_MESH, scale=(8, 0.1, 8), position=(0, 0.05, 0), color=color.rgb(255, 215, 0))
Entity(model='circle', scale=(7, 7), rotation_x=90, position=(0, 0.11, 0), color=color.rgb(230, 230, 230), parent=home_pad)

pad_b = Entity(model=CYLINDER_MESH, scale=(8, 0.1, 8), position=(80, 0.05, 80), color=color.rgb(175, 238, 238))
Entity(model='circle', scale=(7, 7), rotation_x=90, position=(80, 0.11, 80), color=color.rgb(230, 230, 230), parent=pad_b)

# Procedural Buildings (30 Obstacles - Light Off-White/Pastel Colors)
buildings = []
random.seed(42)
for _ in range(30):
    bx = random.uniform(-120, 120)
    bz = random.uniform(-120, 120)
    if math.hypot(bx, bz) < 15 or math.hypot(bx - 80, bz - 80) < 15:
        continue
    bw, bh, bd = random.uniform(6, 14), random.uniform(10, 35), random.uniform(6, 14)
    # Light warm gray / white building facade
    b = Entity(
        model='cube', 
        position=(bx, bh / 2, bz), 
        scale=(bw, bh, bd), 
        color=color.rgb(235, 240, 245), 
        collider='box'
    )
    buildings.append(b)

# Practice Rings
rings = []
ring_positions = [
    (10, 5, 20), (-20, 8, 40), (30, 12, 60), (60, 15, 30),
    (75, 10, 60), (40, 7, -30), (-40, 10, -20), (-10, 6, 60)
]
for pos in ring_positions:
    ring = Entity(model=TORUS_MESH, position=pos, scale=(2, 2, 2), color=color.orange, collider='box')
    ring.passed = False
    rings.append(ring)

# ==========================================
# DRONE ENTITY (Dark Jet Black Color)
# ==========================================
class Drone(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        DARK_DRONE_COLOR = color.rgb(20, 20, 25)  # Pitch/Charcoal Black
        
        # Visible Parts Container
        self.visual_parts = []
        
        # Model Components
        self.body = Entity(parent=self, model='cube', scale=(1.2, 0.2, 1.2),  color=color.black)
        self.arm1 = Entity(parent=self, model='cube', scale=(2.2, 0.1, 0.2), color=color.black)
        self.arm2 = Entity(parent=self, model='cube', scale=(0.2, 0.1, 2.2), color=color.black)
        self.nose = Entity(parent=self, model='sphere', scale=(0.3, 0.3, 0.3), position=(0, 0.1, 0.6), color=color.red)

        self.props = [
            Entity(parent=self, model=CYLINDER_MESH, scale=(0.8, 0.02, 0.8), position=(1.0, 0.15, 1.0), color=DARK_DRONE_COLOR),
            Entity(parent=self, model=CYLINDER_MESH, scale=(0.8, 0.02, 0.8), position=(-1.0, 0.15, 1.0), color=DARK_DRONE_COLOR),
            Entity(parent=self, model=CYLINDER_MESH, scale=(0.8, 0.02, 0.8), position=(1.0, 0.15, -1.0), color=DARK_DRONE_COLOR),
            Entity(parent=self, model=CYLINDER_MESH, scale=(0.8, 0.02, 0.8), position=(-1.0, 0.15, -1.0), color=DARK_DRONE_COLOR)
        ]

        self.visual_parts = [self.body, self.arm1, self.arm2, self.nose] + self.props
        
        self.collider = 'box'
        self.reset_state()

    def set_visibility(self, visible: bool):
        """Toggle drone mesh visibility based on camera mode"""
        for part in self.visual_parts:
            part.enabled = visible

    def reset_state(self):
        self.position = (0, 0.5, 0)
        self.rotation = (0, 0, 0)
        self.velocity = Vec3(0, 0, 0)
        self.throttle = 0.0
        self.is_crashed = False
        self.score = 0
        for r in rings:
            r.passed = False
            r.color = color.orange

    def update(self):
        if self.is_crashed:
            return

        # ==========================================
        # Dynamic Throttle Logic (Hold SPACE to rise)
        # ==========================================
        if held_keys['space']:
            # Ramp throttle up quickly to lift off
            self.throttle = min(self.throttle + 1.5 * time.dt, 1.0)
        elif held_keys['left shift']:
            # Active descent
            self.throttle = max(self.throttle - 1.5 * time.dt, 0.0)
        else:
            # Drop throttle to 0 naturally so gravity takes over
            self.throttle = max(self.throttle - 2.0 * time.dt, 0.0)

        # Rotor animations
        for prop in self.props:
            prop.rotation_y += self.throttle * 2000 * time.dt

        # Control Handling
        pitch_input = (held_keys['w'] - held_keys['s'])
        roll_input = (held_keys['d'] - held_keys['a'])
        yaw_input = (held_keys['e'] - held_keys['q'])

        self.rotation_x = lerp(self.rotation_x, pitch_input * 25.0, time.dt * 4)
        self.rotation_z = lerp(self.rotation_z, -roll_input * 25.0, time.dt * 4)
        self.rotation_y += yaw_input * YAW_SPEED * time.dt

        # Physics Calculations
        total_thrust = self.throttle * MAX_THROTTLE
        up_vector = self.up
        thrust_vector = up_vector * total_thrust

        gravity_vector = Vec3(0, -GRAVITY, 0)
        drag_vector = -self.velocity * DRAG_COEFF
        acceleration = thrust_vector + gravity_vector + drag_vector

        self.velocity += acceleration * time.dt
        self.position += self.velocity * time.dt

        # Ground Landing / Crash Detection
        if self.y <= 0.3:
            self.y = 0.3
            descent_speed = abs(self.velocity.y)
            tilt_angle = math.sqrt(self.rotation_x**2 + self.rotation_z**2)

            if descent_speed > MAX_DESCENT_SPEED or tilt_angle > MAX_LANDING_TILT:
                self.crash("Hard Landing / Heavy Tilt Landing!")
            else:
                self.velocity = Vec3(0, 0, 0)
                if math.hypot(self.x - 80, self.z - 80) < 4.0:
                    self.score += 500

        # Collision with buildings
        hit_info = self.intersects()
        if hit_info.hit and hit_info.entity in buildings:
            self.crash("Building Collision!")

        # Ring passage detection
        for ring in rings:
            if not ring.passed and distance(self.position, ring.position) < 3.0:
                ring.passed = True
                ring.color = color.green
                self.score += 100

    def crash(self, reason):
        self.is_crashed = True
        self.velocity = Vec3(0, 0, 0)
        hud_status.text = f"CRASHED: {reason} [Press 'R' to Reset]"
        hud_status.color = color.red

drone = Drone()

# ==========================================
# CAMERA & HUD SETUP
# ==========================================
camera_mode = 0  # 0: Chase, 1: FPV, 2: High Orbit

def update_camera():
    if camera_mode == 0:  # Chase Cam
        drone.set_visibility(True)
        camera.parent = None
        target_pos = drone.position - drone.forward * 8 + Vec3(0, 3, 0)
        camera.position = lerp(camera.position, target_pos, time.dt * 6)
        camera.look_at(drone.position + Vec3(0, 1, 0))

    elif camera_mode == 1:  # FPV Cam (Hide Drone)
        drone.set_visibility(False)
        camera.parent = drone
        camera.position = Vec3(0, 0.2, 0.5)
        camera.rotation = Vec3(0, 0, 0)

    elif camera_mode == 2:  # High Orbit Cam
        drone.set_visibility(True)
        camera.parent = None
        camera.position = drone.position + Vec3(0, 25, -25)
        camera.look_at(drone.position)

# HUD Overlay Text
hud_info = Text(text='', position=(-0.85, 0.45), scale=1.1, color=color.black)
hud_status = Text(text='', position=(-0.25, 0.0), scale=1.5, color=color.red)
hud_help = Text(
    text="CONTROLS:\nSpace (HOLD): Throttle Up\nShift (HOLD): Throttle Down\nRelease Space: Natural Gravity Fall\nW/S: Pitch | A/D: Roll | Q/E: Yaw\nC: Cam | R: Reset | H: Toggle Help",
    position=(0.4, 0.45), scale=0.8, color=color.rgb(40, 40, 40), enabled=True
)

def input(key):
    global camera_mode
    if key == 'c':
        camera_mode = (camera_mode + 1) % 3
    if key == 'r':
        drone.reset_state()
        hud_status.text = ""
    if key == 'h':
        hud_help.enabled = not hud_help.enabled

def update():
    drone.update()
    update_camera()

    speed = drone.velocity.length()
    hud_info.text = (
        f"Altitude: {drone.y - 0.3:.1f} m\n"
        f"Speed:    {speed:.1f} m/s\n"
        f"Throttle: {int(drone.throttle * 100)}%\n"
        f"Score:    {drone.score}"
    )

app.run()