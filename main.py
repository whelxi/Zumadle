import pygame
import math
import random
import string
import os

# --- Initialization ---
pygame.init()
pygame.mixer.init()

# --- Base Resolution for Scaling ---
BASE_RESOLUTION_WIDTH = 1920
BASE_RESOLUTION_HEIGHT = 1080

screen_info = pygame.display.Info()
ACTUAL_SCREEN_WIDTH, ACTUAL_SCREEN_HEIGHT = screen_info.current_w, screen_info.current_h

WIDTH, HEIGHT = ACTUAL_SCREEN_WIDTH, ACTUAL_SCREEN_HEIGHT
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Zuma Wordle Clone - 2-Hitbox System")
clock = pygame.time.Clock()
FPS = 60
pygame.font.init()

# --- Scaling Factor Calculation ---
SCALE_FACTOR = min(WIDTH / BASE_RESOLUTION_WIDTH, HEIGHT / BASE_RESOLUTION_HEIGHT)

def scale_value(val):
    return int(val * SCALE_FACTOR)

def scale_point(point):
    return (scale_value(point[0]), scale_value(point[1]))

# --- Colors ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
LASER_COLOR = (255, 0, 0, 150)

COLOR_DEFAULT = WHITE
COLOR_PREFIX_2 = (255, 240, 100) # Bright Yellow
COLOR_PREFIX_3 = (170, 255, 170) # Bright Green
COLOR_PREFIX_4 = (150, 220, 255) # Bright Blue
COLOR_WORD_5 = (255, 200, 255) # Light Purple


# --- Asset Loading ---
ASSET_PATH = 'data'
CANNON_SCALE_FACTOR = 0.3

try:
    background_image = pygame.image.load(os.path.join(ASSET_PATH, 'background.png')).convert()
    background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))

    cannon_base_image = pygame.image.load(os.path.join(ASSET_PATH, 'cannon.png')).convert_alpha()
    cannon_base_image = pygame.transform.scale_by(cannon_base_image, CANNON_SCALE_FACTOR * SCALE_FACTOR)

    keypress_sound = pygame.mixer.Sound(os.path.join(ASSET_PATH, 'keypress.mp3'))
    pop_sound = pygame.mixer.Sound(os.path.join(ASSET_PATH, 'pop.mp3'))

except pygame.error as e:
    print(f"Error loading assets from '{ASSET_PATH}' folder: {e}")
    background_image = pygame.Surface((WIDTH, HEIGHT)); background_image.fill(BLACK)
    cannon_base_image = pygame.Surface((scale_value(30), scale_value(30)), pygame.SRCALPHA); pygame.draw.polygon(cannon_base_image, WHITE, [(scale_value(15),0), (0, scale_value(30)), (scale_value(30), scale_value(30))])
    keypress_sound = pygame.mixer.Sound(pygame.mixer.Sound(buffer=b''))
    pop_sound = pygame.mixer.Sound(pygame.mixer.Sound(buffer=b''))


# --- Word Game Variables ---
def load_word_list(path, filename):
    word_set = set()
    prefix_set = set()
    file_path = os.path.join(path, filename)

    try:
        with open(file_path, 'r') as f:
            for line in f:
                word = line.strip().upper()
                if len(word) == 5:
                    word_set.add(word)
                    prefix_set.add(word[0:2])
                    prefix_set.add(word[0:3])
                    prefix_set.add(word[0:4])

        print(f"Successfully loaded {len(word_set)} 5-letter words.")
        print(f"Successfully generated {len(prefix_set)} 2,3,4-letter prefixes.")

    except FileNotFoundError:
        print(f"Warning: '{filename}' not found in '{path}' folder.")
        print("Using a small fallback word list.")
        word_set = {"PYTHON", "GAMES", "ZUMAS", "HELLO", "WORLD", "SCORE", "POINT", "CHAIN", "BLAST", "MOUSE", "CLICK", "WORDS", "EPICS", "WHALE"}
        prefix_set = {"PY", "PYT", "PYTH", "GA", "GAM", "GAME", "WHAL", "EPIC"}

    return word_set, prefix_set

VALID_WORDS, PREFIX_SET = load_word_list(ASSET_PATH, 'word_list_5.txt')
SCORE = 0

def random_letter():
    return random.choice(string.ascii_uppercase)

# --- Game Variables (all based on BASE_RESOLUTION) ---
BALL_RADIUS_BASE = 30
BALL_DIAMETER_BASE = BALL_RADIUS_BASE * 2
# Note: HITBOX_SCALE_FACTOR is no longer used for chain balls
HITBOX_SCALE_FACTOR_SHOT = 0.7 # For shot balls

BALL_RADIUS = scale_value(BALL_RADIUS_BASE)
BALL_DIAMETER = scale_value(BALL_DIAMETER_BASE)

GAME_FONT = pygame.font.SysFont('Arial', scale_value(45))
SMALL_GAME_FONT = pygame.font.SysFont('Arial', scale_value(15))

LAUNCHER_POS_BASE = (BASE_RESOLUTION_WIDTH // 2, BASE_RESOLUTION_HEIGHT // 2)
LAUNCHER_POS = scale_point(LAUNCHER_POS_BASE)

# --- Path and Speed Settings ---
CHAIN_SPEED = 0.2
PATH_POINT_SPACING = 8
BALL_SPACING_ON_PATH = BALL_DIAMETER_BASE / PATH_POINT_SPACING
CATCH_UP_SPEED_FACTOR = 0.03
MAX_EXTRA_SPEED = 0.3
GAME_OVER = False
STARTING_BALLS = 30

CHAIN_DECELERATION = 0.0001
MIN_CHAIN_SPEED = 0.02

# --- Path Generation Function (uses BASE_RESOLUTION coordinates) ---
def generate_path_points(rough_path_base, spacing_base):
    final_path_base = []
    for i in range(len(rough_path_base) - 1):
        p1 = rough_path_base[i]
        p2 = rough_path_base[i+1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        distance = math.hypot(dx, dy)
        if distance == 0: continue
        ux, uy = dx / distance, dy / distance
        num_points = int(distance / spacing_base)
        for n in range(num_points):
            x = p1[0] + ux * n * spacing_base
            y = p1[1] + uy * n * spacing_base
            final_path_base.append((x, y))
    final_path_base.append(rough_path_base[-1])
    return final_path_base

ROUGH_PATH_BASE = [
    (BASE_RESOLUTION_WIDTH + 200, -100), (BASE_RESOLUTION_WIDTH - 100, 100), (BASE_RESOLUTION_WIDTH - 100, BASE_RESOLUTION_HEIGHT - 100),
    (100, BASE_RESOLUTION_HEIGHT - 100), (100, 200), (BASE_RESOLUTION_WIDTH - 200, 200),
    (BASE_RESOLUTION_WIDTH - 200, BASE_RESOLUTION_HEIGHT // 2 - 100), (BASE_RESOLUTION_WIDTH // 2, BASE_RESOLUTION_HEIGHT // 2 - 100),
    (BASE_RESOLUTION_WIDTH // 2, 300), (BASE_RESOLUTION_WIDTH - 300, 300), (BASE_RESOLUTION_WIDTH - 300, BASE_RESOLUTION_HEIGHT // 2 + 100),
    (BASE_RESOLUTION_WIDTH // 2 + 100, BASE_RESOLUTION_HEIGHT // 2 + 100), (BASE_RESOLUTION_WIDTH // 2 + 100, BASE_RESOLUTION_HEIGHT // 2 - 50),
    (BASE_RESOLUTION_WIDTH // 2, BASE_RESOLUTION_HEIGHT // 2 - 50), (BASE_RESOLUTION_WIDTH // 2, BASE_RESOLUTION_HEIGHT // 2)
]
PATH_POINTS_BASE = generate_path_points(ROUGH_PATH_BASE, PATH_POINT_SPACING)

# --- Ball Sprite Class ---
class Ball(pygame.sprite.Sprite):
    def __init__(self, letter, path_index):
        super().__init__()
        self.letter = letter
        self.color = WHITE
        self.path_index = float(path_index)

        self.image = pygame.Surface((BALL_DIAMETER, BALL_DIAMETER), pygame.SRCALPHA)
        self.re_render_image()

        self.x_base, self.y_base = 0, 0
        self.rect = self.image.get_rect()
        
        # <-- NEW HITBOX LOGIC -->
        # We use the scaled BALL_RADIUS as the base for size/offset
        self.hitbox_size = int(BALL_RADIUS * 0.8) # Hitbox is 80% of ball radius
        self.hitbox_offset = int(BALL_RADIUS * 0.75) # Positioned 75% from center
        
        # These are the two new hitboxes
        self.front_hitbox = pygame.Rect(0, 0, self.hitbox_size, self.hitbox_size)
        self.back_hitbox = pygame.Rect(0, 0, self.hitbox_size, self.hitbox_size)
        
        self.set_pos_from_path_index()

        self.dx, self.dy, self.speed = 0, 0, 0
        # collision_radius is now only used for SHOT balls
        self.collision_radius = scale_value(BALL_RADIUS_BASE * HITBOX_SCALE_FACTOR_SHOT)


    def re_render_image(self):
        self.image.fill((0,0,0,0))
        pygame.draw.circle(self.image, self.color, (BALL_RADIUS, BALL_RADIUS), BALL_RADIUS)
        pygame.draw.circle(self.image, BLACK, (BALL_RADIUS, BALL_RADIUS), BALL_RADIUS, 2)
        letter_surf = GAME_FONT.render(self.letter, True, BLACK)
        letter_rect = letter_surf.get_rect(center=(BALL_RADIUS, BALL_RADIUS))
        self.image.blit(letter_surf, letter_rect)

    def set_color(self, color):
        if self.color == color:
            return
        self.color = color
        self.re_render_image()

    def set_pos_from_path_index(self):
        idx = int(self.path_index)

        if idx >= len(PATH_POINTS_BASE):
            self.x_base, self.y_base = PATH_POINTS_BASE[-1]
            global GAME_OVER
            GAME_OVER = True
        elif idx < 0:
            self.x_base, self.y_base = PATH_POINTS_BASE[0]
        else:
            self.x_base, self.y_base = PATH_POINTS_BASE[idx]

        self.rect.center = scale_point((int(self.x_base), int(self.y_base)))

        # <-- NEW HITBOX UPDATE LOGIC -->
        # Get stable direction vector
        p1_idx = max(0, idx - int(BALL_SPACING_ON_PATH))
        p2_idx = min(len(PATH_POINTS_BASE) - 1, idx + int(BALL_SPACING_ON_PATH))

        if p1_idx >= p2_idx: # Handle edges
            p1_idx = max(0, len(PATH_POINTS_BASE) - 2)
            p2_idx = len(PATH_POINTS_BASE) - 1
            if p1_idx >= p2_idx: # Handle path with < 2 points
                p1_idx = 0; p2_idx = 0;

        p1 = scale_point(PATH_POINTS_BASE[p1_idx])
        p2 = scale_point(PATH_POINTS_BASE[p2_idx])
        
        dir_x = p2[0] - p1[0]
        dir_y = p2[1] - p1[1]
        
        dist = math.hypot(dir_x, dir_y)
        ux, uy = 0, 0
        if dist > 0:
            ux = dir_x / dist # Normalized "forward" X
            uy = dir_y / dist # Normalized "forward" Y
        
        # Calculate hitbox centers
        front_center_x = self.rect.centerx + ux * self.hitbox_offset
        front_center_y = self.rect.centery + uy * self.hitbox_offset
        
        back_center_x = self.rect.centerx - ux * self.hitbox_offset
        back_center_y = self.rect.centery - uy * self.hitbox_offset
        
        # Update rects
        self.front_hitbox.center = (int(front_center_x), int(front_center_y))
        self.back_hitbox.center = (int(back_center_x), int(back_center_y))
        # <-- END NEW HITBOX UPDATE LOGIC -->


    def update(self):
        if self.speed > 0:
            self.rect.x += self.dx
            self.rect.y += self.dy
            if (self.rect.x < -BALL_DIAMETER or self.rect.x > WIDTH + BALL_DIAMETER or
                self.rect.y < -BALL_DIAMETER or self.rect.y > HEIGHT + BALL_DIAMETER):
                self.kill()

    def shoot(self, angle, speed):
        self.speed = scale_value(speed)
        self.dx = math.cos(angle) * self.speed
        self.dy = math.sin(angle) * self.speed

# --- Launcher Class ---
class Launcher:
    def __init__(self, pos_base, image):
        self.pos_base = pos_base
        self.pos = scale_point(pos_base)
        self.base_image = image
        self.rect = self.base_image.get_rect(center=self.pos)

    def draw(self, surface, all_chain_balls):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        rel_x, rel_y = mouse_x - self.pos[0], mouse_y - self.pos[1]
        angle_radians = math.atan2(-rel_y, rel_x) 
        angle_degrees = math.degrees(angle_radians)

        rotated_cannon_image = pygame.transform.rotate(self.base_image, angle_degrees - 90)
        rotated_cannon_rect = rotated_cannon_image.get_rect(center=self.pos)
        surface.blit(rotated_cannon_image, rotated_cannon_rect)

        if pygame.mouse.get_focused():
            dx = math.cos(angle_radians)
            dy = -math.sin(angle_radians)
            laser_start_pos = (self.pos[0] + dx * scale_value(20), self.pos[1] + dy * scale_value(20))
            laser_end_pos = (laser_start_pos[0] + dx * 5000, laser_start_pos[1] + dy * 5000)
            step = scale_value(5)
            max_dist = 5000
            hit_found = False

            for t in range(0, max_dist, step):
                current_x = laser_start_pos[0] + t * dx
                current_y = laser_start_pos[1] + t * dy
                for ball in all_chain_balls:
                    # Laser can hit *either* hitbox
                    if ball.front_hitbox.collidepoint(current_x, current_y) or \
                       ball.back_hitbox.collidepoint(current_x, current_y):
                        laser_end_pos = (current_x, current_y)
                        hit_found = True
                        break
                if hit_found:
                    break

            laser_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(laser_surface, LASER_COLOR, laser_start_pos, laser_end_pos, width=scale_value(3))
            surface.blit(laser_surface, (0, 0))

    def get_new_ball(self):
        pass

# --- Helper Functions ---
def get_angle(pos1, pos2):
    return math.atan2(pos2[1] - pos1[1], pos2[0] - pos1[0])

# This function is no longer used for chain collisions
def custom_collide_circle(sprite1, sprite2):
    dist_sq = (sprite1.rect.center[0] - sprite2.rect.center[0])**2 + \
              (sprite1.rect.center[1] - sprite2.rect.center[1])**2
    return dist_sq < (sprite1.collision_radius + sprite2.collision_radius)**2

def check_matches(chain, start_index):
    """Checks only for 5-letter words for DELETION."""
    if not chain or len(chain) < 5:
        return 0, -1, -1

    # Check words from "WHALE" (i=start_index-4) to "EPICS" (i=start_index)
    for i in range(max(0, start_index - 4), min(start_index + 1, len(chain) - 4)):
        if i + 5 > len(chain):
            continue

        word = ""
        for j in range(i, i + 5):
            word += chain[j].letter

        if word in VALID_WORDS:
            global SCORE
            SCORE += 100
            print(f"Word Found: {word}! Score: {SCORE}")
            pop_sound.play()
            return 5, i, i + 4 # Return the first match found

    return 0, -1, -1


def update_chain_colors(chain): # <-- Takes a single chain
    """Iterates through the chain and colors it."""
    i = 0
    while i < len(chain):
        match_len = 1
        color_to_set = COLOR_DEFAULT

        if i + 5 <= len(chain):
            word = "".join([chain[j].letter for j in range(i, i + 5)])
            if word in VALID_WORDS:
                match_len = 5
                color_to_set = COLOR_WORD_5

        if match_len == 1 and i + 4 <= len(chain):
            word = "".join([chain[j].letter for j in range(i, i + 4)])
            if word in PREFIX_SET:
                match_len = 4
                color_to_set = COLOR_PREFIX_4

        if match_len == 1 and i + 3 <= len(chain):
            word = "".join([chain[j].letter for j in range(i, i + 3)])
            if word in PREFIX_SET:
                match_len = 3
                color_to_set = COLOR_PREFIX_3

        if match_len == 1 and i + 2 <= len(chain):
            word = "".join([chain[j].letter for j in range(i, i + 2)])
            if word in PREFIX_SET:
                match_len = 2
                color_to_set = COLOR_PREFIX_2

        for j in range(i, i + match_len):
            chain[j].set_color(color_to_set)

        i += match_len


def shift_chain(chain, from_index, shift_amount_base):
    """Shifts balls *within* a single chain."""
    for i in range(from_index, len(chain)):
        chain[i].path_index -= shift_amount_base
        chain[i].set_pos_from_path_index()

def create_gap(chain, at_index, gap_size_base):
    """Pushes balls forward and backward from an index to create a gap."""
    half_gap = gap_size_base / 2.0
    
    # Push head segment (0 to at_index-1) FORWARD
    for i in range(at_index):
        chain[i].path_index += half_gap
    
    # Push tail segment (at_index to end) BACKWARD
    for i in range(at_index, len(chain)):
        chain[i].path_index -= half_gap

    # All balls need their screen positions updated after moving
    for ball in chain:
        ball.set_pos_from_path_index()

# --- Sprite Groups ---
all_sprites = pygame.sprite.Group()
chain_ball_sprites = pygame.sprite.Group()

# --- Game Loop Setup ---
running = True
launcher = Launcher(LAUNCHER_POS_BASE, cannon_base_image)

chain_list = []
start_index = 0
for i in range(STARTING_BALLS):
    index = start_index + (i * BALL_SPACING_ON_PATH)
    new_ball = Ball(random_letter(), index)
    all_sprites.add(new_ball)
    chain_ball_sprites.add(new_ball)
    chain_list.append(new_ball)

SPAWN_DELAY = int((BALL_DIAMETER_BASE / (CHAIN_SPEED * PATH_POINT_SPACING)) * (1000 / FPS))
last_spawn_time = pygame.time.get_ticks()

update_chain_colors(chain_list)

while running:
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key >= pygame.K_a and event.key <= pygame.K_z:
                if not GAME_OVER:
                    keypress_sound.play()
                    letter = pygame.key.name(event.key).upper()
                    mouse_pos = pygame.mouse.get_pos()
                    angle = get_angle(LAUNCHER_POS, mouse_pos)
                    new_shot = Ball(letter, 0)
                    new_shot.rect.center = LAUNCHER_POS
                    new_shot.shoot(angle, 20)
                    all_sprites.add(new_shot)

    if GAME_OVER:
        screen.fill(BLACK)
        game_over_text = GAME_FONT.render(f"GAME OVER - Score: {SCORE} - Press ESC to quit", True, RED)
        screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 2 - game_over_text.get_height() // 2))
        pygame.display.flip()
        clock.tick(FPS)
        continue

    # --- Game Logic ---

    if CHAIN_SPEED > MIN_CHAIN_SPEED:
        CHAIN_SPEED -= CHAIN_DECELERATION
    else:
        CHAIN_SPEED = MIN_CHAIN_SPEED

    # --- Spawning Logic ---
    current_time = pygame.time.get_ticks()
    current_spawn_delay = int((BALL_DIAMETER_BASE / (CHAIN_SPEED * PATH_POINT_SPACING)) * (1000 / FPS))

    if current_time - last_spawn_time > current_spawn_delay:
        if not chain_list or chain_list[-1].path_index >= BALL_SPACING_ON_PATH:
            new_letter = random_letter()
            new_ball = Ball(new_letter, 0.0)
            all_sprites.add(new_ball)
            chain_ball_sprites.add(new_ball)
            chain_list.append(new_ball)
            last_spawn_time = current_time
            update_chain_colors(chain_list)

    # --- Shot Ball Update ---
    shot_balls_list = [s for s in all_sprites if s not in chain_ball_sprites]
    for shot in shot_balls_list:
        shot.update()

    # --- Chain Movement Logic ---
    for j, ball in enumerate(chain_list):
        if j == 0:
            ball.path_index += CHAIN_SPEED
        else:
            ball_in_front = chain_list[j-1]
            target_index = ball_in_front.path_index - BALL_SPACING_ON_PATH
            dist = target_index - ball.path_index

            if dist > 0:
                move_speed = CHAIN_SPEED + min(dist * CATCH_UP_SPEED_FACTOR, MAX_EXTRA_SPEED)
                if ball.path_index + move_speed >= target_index:
                    ball.path_index = target_index
                else:
                    ball.path_index += move_speed
            else:
                ball.path_index = target_index

        ball.set_pos_from_path_index()

    # --- Collision and Insertion Logic ---
    # <-- REPLACED DOT-PRODUCT LOGIC WITH 2-HITBOX LOGIC -->
    for shot in shot_balls_list[:]:
        hit_ball = None
        hit_type = None # 'front' or 'back'

        # Manual collision check against our custom hitboxes
        for ball in chain_ball_sprites:
            # Check back hitbox first
            if ball.back_hitbox.colliderect(shot.rect):
                hit_ball = ball
                hit_type = 'back'
                break
            elif ball.front_hitbox.colliderect(shot.rect):
                hit_ball = ball
                hit_type = 'front'
                break
        
        if hit_ball:
            shot.kill()

            try:
                ball_index = chain_list.index(hit_ball)
            except ValueError:
                continue # Ball was already killed, e.g. by a previous shot

            # NEW directional logic based on which box was hit
            if hit_type == 'back':
                insert_at_index = ball_index + 1 # Insert AFTER
            else: # hit_type == 'front'
                insert_at_index = ball_index # Insert BEFORE

            # --- Gap Creation and Insertion (This logic is still good) ---
            half_spacing = BALL_SPACING_ON_PATH / 2.0

            # Case 1: Insert at the very head (index 0)
            if insert_at_index == 0:
                shift_chain(chain_list, 0, BALL_SPACING_ON_PATH) 
                new_path_index = chain_list[0].path_index + BALL_SPACING_ON_PATH 
            
            # Case 2: Insert at the very tail (index len(chain))
            elif insert_at_index == len(chain_list):
                new_path_index = chain_list[-1].path_index - BALL_SPACING_ON_PATH
            
            # Case 3: Insert BETWEEN two balls
            else:
                create_gap(chain_list, insert_at_index, BALL_SPACING_ON_PATH)
                new_path_index = chain_list[insert_at_index - 1].path_index - BALL_SPACING_ON_PATH

            inserted_ball = Ball(shot.letter, new_path_index)

            chain_list.insert(insert_at_index, inserted_ball)
            all_sprites.add(inserted_ball)
            chain_ball_sprites.add(inserted_ball)

            # --- Combo Logic ---
            check_index = insert_at_index

            while True:
                count, start_idx, end_idx = check_matches(chain_list, check_index)

                if count >= 5:
                    for j in range(start_idx, end_idx + 1):
                        chain_list[j].kill()

                    del chain_list[start_idx : end_idx + 1]

                    if start_idx < len(chain_list):
                        check_index = start_idx # Re-check at the snap point
                    else:
                        break # Deleted at end
                else:
                    break # No match found

            update_chain_colors(chain_list)

    # --- Drawing ---
    screen.blit(background_image, (0, 0))

    if len(PATH_POINTS_BASE) > 2:
        scaled_path_points = [scale_point(p) for p in PATH_POINTS_BASE]
        pygame.draw.lines(screen, (80, 80, 80), False, scaled_path_points, scale_value(4))

    all_sprites.draw(screen)


    # Delete 

# --- Drawing ---
    screen.blit(background_image, (0, 0))

    if len(PATH_POINTS_BASE) > 2:
        scaled_path_points = [scale_point(p) for p in PATH_POINTS_BASE]
        pygame.draw.lines(screen, (80, 80, 80), False, scaled_path_points, scale_value(4))

    all_sprites.draw(screen)

    # <-- START DEBUG DRAWING -->
    # <-- UPDATED to show new hitboxes -->
    DEBUG_FRONT_COLOR = (255, 0, 0) # Red
    DEBUG_BACK_COLOR = (0, 0, 255)  # Blue
    DEBUG_HITBOX_WIDTH = 2 # Line thickness
    for ball in chain_ball_sprites:
        pygame.draw.rect(screen, DEBUG_FRONT_COLOR, ball.front_hitbox, DEBUG_HITBOX_WIDTH)
        pygame.draw.rect(screen, DEBUG_BACK_COLOR, ball.back_hitbox, DEBUG_HITBOX_WIDTH)
    
    # for ball in shot_balls_list:
    # 	  pygame.draw.circle(screen, (0, 255, 0), ball.rect.center, ball.collision_radius, 1)
    # <-- END DEBUG DRAWING -->


    launcher.draw(screen, chain_ball_sprites)

    score_text = GAME_FONT.render(f"Score: {SCORE}", True, WHITE)
    screen.blit(score_text, scale_point((20, 20)))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()