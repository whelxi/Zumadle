import pygame
import math
import random
import string
import os
import requests  # <-- NEW: For downloading files
import sys       # <-- NEW: For exiting script on failure

# --- Helper Function for Downloading ---
def download_file(url, local_path):
    """Downloads a file from a URL to a local path."""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            print(f"Successfully downloaded {local_path}")
            return True
        else:
            print(f"Error: Got status code {response.status_code} for {url}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        return False

# --- Asset Setup and Download ---
ASSET_PATH = 'data'
BASE_GITHUB_URL = "https://raw.githubusercontent.com/whelxi/Zumadle/main/Data/"
REQUIRED_FILES = [
    "background.png", 
    "cannon.png", 
    "keypress.mp3", 
    "pop.mp3", 
    "word_list_5.txt"
]

# 1. Check if 'data' folder exists
if not os.path.exists(ASSET_PATH):
    try:
        os.makedirs(ASSET_PATH)
        print(f"Created directory: {ASSET_PATH}")
    except OSError as e:
        print(f"Error creating directory {ASSET_PATH}: {e}")
        sys.exit() # Can't continue if we can't make the folder

# 2. Check and download each file
all_files_present = True
for filename in REQUIRED_FILES:
    local_path = os.path.join(ASSET_PATH, filename)
    if not os.path.exists(local_path):
        print(f"File not found: {filename}. Attempting download...")
        file_url = BASE_GITHUB_URL + filename
        if not download_file(file_url, local_path):
            all_files_present = False
            print(f"Failed to download required file: {filename}.")
    
if not all_files_present:
    print("One or more required files failed to download. Please check your internet connection or the GitHub URL.")
    sys.exit() # Exit if any file failed

print("All required files are present. Starting game...")
# --- End of Download Logic ---

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
pygame.display.set_caption("Zuma Wordle Clone - Faster Speed")
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
WIN_SCREEN_BG = (0, 0, 30) # Dark Blue

COLOR_DEFAULT = WHITE
COLOR_WORD_5 = (255, 200, 255) # Light Purple

# --- NEW: Color scheme for 4-letter spawn groups ---
COLOR_GROUP_1 = (255, 180, 180) # Light Red
COLOR_GROUP_2 = (180, 255, 180) # Light Green
COLOR_GROUP_3 = (180, 180, 255) # Light Blue
COLOR_GROUP_4 = (255, 255, 180) # Light Yellow
COLOR_GROUP_5 = (255, 180, 255) # Light Magenta
COLOR_GROUP_6 = (180, 255, 255) # Light Cyan
SPAWN_GROUP_COLORS = [COLOR_GROUP_1, COLOR_GROUP_2, COLOR_GROUP_3, COLOR_GROUP_4, COLOR_GROUP_5, COLOR_GROUP_6]
current_spawn_color_index = 0


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
    prefix_set_all = set() # For coloring (2, 3, 4 letters)
    prefix_set_4 = set()   # For spawning (4 letters only)
    file_path = os.path.join(path, filename)

    try:
        with open(file_path, 'r', encoding="utf-8") as f:
            for line in f:
                word = line.strip().upper()
                if len(word) == 5:
                    word_set.add(word)
                    prefix_set_all.add(word[0:2])
                    prefix_set_all.add(word[0:3])
                    prefix_set_all.add(word[0:4])
                    prefix_set_4.add(word[0:4]) 

        print(f"Successfully loaded {len(word_set)} 5-letter words.")
        print(f"Successfully generated {len(prefix_set_all)} 2,3,4-letter prefixes (for coloring).")
        print(f"Successfully generated {len(prefix_set_4)} 4-letter prefixes (for spawning).")


    except FileNotFoundError:
        print(f"Warning: '{filename}' not found in '{path}' folder.")
        print("Using a small fallback word list.")
        word_set = {"PYTHON", "GAMES", "ZUMAS", "HELLO", "WORLD", "SCORE", "POINT", "CHAIN", "BLAST", "MOUSE", "CLICK", "WORDS", "EPICS", "WHALE"}
        prefix_set_all = {"PY", "PYT", "PYTH", "GA", "GAM", "GAME", "WHAL", "EPIC"}
        prefix_set_4 = {"PYTH", "GAME", "WHAL", "EPIC"}

    return word_set, prefix_set_all, prefix_set_4

VALID_WORDS, PREFIX_SET, PREFIX_SET_4 = load_word_list(ASSET_PATH, 'word_list_5.txt')
SCORE = 0
spawn_queue = [] # Will now store (letter, color) tuples

def random_letter():
    """DEPRECATED"""
    return random.choice(string.ascii_uppercase)

def get_next_spawn_data():
    """
    Pulls data from a queue populated by random 4-LETTER prefixes.
    Returns: (letter, color) tuple
    """
    global spawn_queue, current_spawn_color_index
    if not spawn_queue:
        try:
            # Queue is empty, refill it
            new_prefix = random.choice(list(PREFIX_SET_4)) 
            
            # Get the next color from the scheme
            color = SPAWN_GROUP_COLORS[current_spawn_color_index % len(SPAWN_GROUP_COLORS)]
            current_spawn_color_index += 1 # Increment for next time
            
            # Populate queue with (letter, color) tuples
            for letter in new_prefix:
                spawn_queue.append((letter, color))

        except IndexError:
            # Fallback if PREFIX_SET_4 is empty
            return (random.choice(string.ascii_uppercase), COLOR_DEFAULT)
    
    # Return the next (letter, color) tuple from the front of the queue
    return spawn_queue.pop(0)

# --- Game Variables (all based on BASE_RESOLUTION) ---
BALL_RADIUS_BASE = 30
BALL_DIAMETER_BASE = BALL_RADIUS_BASE * 2
HITBOX_SCALE_FACTOR_SHOT = 0.7 # For shot balls

BALL_RADIUS = scale_value(BALL_RADIUS_BASE)
BALL_DIAMETER = scale_value(BALL_DIAMETER_BASE)

GAME_FONT = pygame.font.SysFont('Arial', scale_value(45))
SMALL_GAME_FONT = pygame.font.SysFont('Arial', scale_value(15))

LAUNCHER_POS_BASE = (BASE_RESOLUTION_WIDTH // 2, BASE_RESOLUTION_HEIGHT // 2)
LAUNCHER_POS = scale_point(LAUNCHER_POS_BASE)

# --- Path and Speed Settings ---
CHAIN_SPEED = 0.3 
PATH_POINT_SPACING = 8
BALL_SPACING_ON_PATH = BALL_DIAMETER_BASE / PATH_POINT_SPACING
CATCH_UP_SPEED_FACTOR = 0.03
MAX_EXTRA_SPEED = 0.3
GAME_OVER = False
GAME_WON = False # Game Win state
STARTING_BALLS = 100

CHAIN_DECELERATION = 0.0002
MIN_CHAIN_SPEED = 0.08

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
    def __init__(self, letter, path_index, initial_color=WHITE):
        super().__init__()
        self.letter = letter
        self.base_color = initial_color  # The color it should be normally
        self.color = self.base_color     # The color currently displayed
        self.path_index = float(path_index)

        self.image = pygame.Surface((BALL_DIAMETER, BALL_DIAMETER), pygame.SRCALPHA)
        self.re_render_image()

        self.x_base, self.y_base = 0, 0
        self.rect = self.image.get_rect()
        
        self.hitbox_size = int(BALL_RADIUS * 0.8) 
        self.hitbox_offset = int(BALL_RADIUS * 0.75) 
        self.front_hitbox = pygame.Rect(0, 0, self.hitbox_size, self.hitbox_size)
        self.back_hitbox = pygame.Rect(0, 0, self.hitbox_size, self.hitbox_size)
        
        self.collision_radius = scale_value(BALL_RADIUS_BASE * HITBOX_SCALE_FACTOR_SHOT)
        shot_hitbox_size = int(self.collision_radius * 2)
        self.shot_hitbox = pygame.Rect(0, 0, shot_hitbox_size, shot_hitbox_size)
        
        self.set_pos_from_path_index()
        self.dx, self.dy, self.speed = 0, 0, 0

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
            # Don't set GAME_OVER if we won
            if not GAME_WON:
                GAME_OVER = True
        elif idx < 0:
            self.x_base, self.y_base = PATH_POINTS_BASE[0]
        else:
            self.x_base, self.y_base = PATH_POINTS_BASE[idx]

        self.rect.center = scale_point((int(self.x_base), int(self.y_base)))
        self.shot_hitbox.center = self.rect.center

        p1_idx = max(0, idx - int(BALL_SPACING_ON_PATH))
        p2_idx = min(len(PATH_POINTS_BASE) - 1, idx + int(BALL_SPACING_ON_PATH))

        if p1_idx >= p2_idx:
            p1_idx = max(0, len(PATH_POINTS_BASE) - 2)
            p2_idx = len(PATH_POINTS_BASE) - 1
            if p1_idx >= p2_idx: 
                p1_idx = 0; p2_idx = 0;

        p1 = scale_point(PATH_POINTS_BASE[p1_idx])
        p2 = scale_point(PATH_POINTS_BASE[p2_idx])
        
        dir_x = p2[0] - p1[0]
        dir_y = p2[1] - p1[1]
        
        dist = math.hypot(dir_x, dir_y)
        ux, uy = 0, 0
        if dist > 0:
            ux = dir_x / dist
            uy = dir_y / dist
        
        front_center_x = self.rect.centerx + ux * self.hitbox_offset
        front_center_y = self.rect.centery + uy * self.hitbox_offset
        
        back_center_x = self.rect.centerx - ux * self.hitbox_offset
        back_center_y = self.rect.centery - uy * self.hitbox_offset
        
        self.front_hitbox.center = (int(front_center_x), int(front_center_y))
        self.back_hitbox.center = (int(back_center_x), int(back_center_y))

    def update(self):
        if self.speed > 0:
            self.rect.x += self.dx
            self.rect.y += self.dy
            self.shot_hitbox.center = self.rect.center
            
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

def custom_collide_circle(sprite1, sprite2):
    dist_sq = (sprite1.rect.center[0] - sprite2.rect.center[0])**2 + \
              (sprite1.rect.center[1] - sprite2.rect.center[1])**2
    return dist_sq < (sprite1.collision_radius + sprite2.collision_radius)**2

def check_matches(chain):
    """
    Checks the ENTIRE chain for the FIRST 5-letter word.
    """
    if not chain or len(chain) < 5:
        return 0, -1, -1

    i = 0
    while i <= len(chain) - 5: 
        word = "".join([chain[j].letter for j in range(i, i + 5)])

        if word in VALID_WORDS:
            global SCORE
            SCORE += 100
            print(f"Word Found: {word}! Score: {SCORE}")
            pop_sound.play()
            return 5, i, i + 4 

        i += 1 

    return 0, -1, -1

def update_chain_colors(chain):
    """
    Iterates through the chain.
    Sets 5-letter words to purple.
    Resets all other balls to their base_color.
    """
    # First, reset all balls to their base color
    for ball in chain:
        ball.set_color(ball.base_color)

    # Now, iterate and find 5-letter words to override the color
    i = 0
    while i < len(chain):
        match_len = 1
        color_to_set = None # Signal "no change"
 
        if i + 5 <= len(chain):
            word = "".join([chain[j].letter for j in range(i, i + 5)])
            if word in VALID_WORDS:
                match_len = 5
                color_to_set = COLOR_WORD_5
 
        if color_to_set: # If we found a 5-letter word
            for j in range(i, i + match_len):
                chain[j].set_color(color_to_set)
 
        i += match_len


def shift_chain(chain, from_index, shift_amount_base):
    for i in range(from_index, len(chain)):
        chain[i].path_index -= shift_amount_base
        chain[i].set_pos_from_path_index()

def create_gap(chain, at_index, gap_size_base):
    half_gap = gap_size_base / 2.0
    
    for i in range(at_index):
        chain[i].path_index += half_gap
    
    for i in range(at_index, len(chain)):
        chain[i].path_index -= half_gap

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
for i in range(STARTING_BALLS): # <-- This is now 20
    index = start_index + (i * BALL_SPACING_ON_PATH)
    letter, color = get_next_spawn_data()
    new_ball = Ball(letter, index, color) 
    all_sprites.add(new_ball)
    chain_ball_sprites.add(new_ball)
    chain_list.append(new_ball)

SPAWN_DELAY = int((BALL_DIAMETER_BASE / (CHAIN_SPEED * PATH_POINT_SPACING)) * (1000 / FPS))
last_spawn_time = pygame.time.get_ticks()

# update_chain_colors(chain_list) # Keep initial chain its base color


while running:
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            
            if event.key >= pygame.K_a and event.key <= pygame.K_z:
                if not GAME_OVER and not GAME_WON:
                    keypress_sound.play()
                    letter = pygame.key.name(event.key).upper()
                    mouse_pos = pygame.mouse.get_pos()
                    angle = get_angle(LAUNCHER_POS, mouse_pos)
                    # <-- **SHOT SPEED INCREASED** -->
                    new_shot = Ball(letter, 0) 
                    new_shot.rect.center = LAUNCHER_POS
                    new_shot.shoot(angle, 35) # <-- Was 20
                    all_sprites.add(new_shot)

    # --- Handle Win Screen ---
    if GAME_WON:
        screen.fill(WIN_SCREEN_BG)
        win_text = GAME_FONT.render(f"YOU WIN! - Final Score: {SCORE} - Press ESC to quit", True, COLOR_GROUP_2)
        screen.blit(win_text, (WIDTH // 2 - win_text.get_width() // 2, HEIGHT // 2 - win_text.get_height() // 2))
        pygame.display.flip()
        clock.tick(FPS)
        continue

    # --- Handle Game Over Screen ---
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

    # --- Spawning Logic (DISABLED FOR TESTING) ---
    # current_time = pygame.time.get_ticks()
    # current_spawn_delay = int((BALL_DIAMETER_BASE / (CHAIN_SPEED * PATH_POINT_SPACING)) * (1000 / FPS))

    # if current_time - last_spawn_time > current_spawn_delay:
    #     if not chain_list or chain_list[-1].path_index >= BALL_SPACING_ON_PATH:
    #         letter, color = get_next_spawn_data()
    #         new_ball = Ball(letter, 0.0, color)
    #         all_sprites.add(new_ball)
    #         chain_ball_sprites.add(new_ball)
    #         chain_list.append(new_ball)
    #         last_spawn_time = current_time
    #         update_chain_colors(chain_list) 

    # --- Shot Ball Update ---
    shot_balls_list = [s for s in all_sprites if s not in chain_ball_sprites]
    for shot in shot_balls_list:
        shot.update()

    # --- Chain Movement Logic ---
    # Only move the chain if it's not empty
    if chain_list:
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
    for shot in shot_balls_list[:]:
        hit_ball = None
        hit_type = None 

        for ball in chain_ball_sprites:
            if ball.back_hitbox.colliderect(shot.shot_hitbox):
                hit_ball = ball
                hit_type = 'back'
                break
            elif ball.front_hitbox.colliderect(shot.shot_hitbox):
                hit_ball = ball
                hit_type = 'front'
                break
        
        if hit_ball:
            shot.kill()

            try:
                ball_index = chain_list.index(hit_ball)
            except ValueError:
                continue 

            if hit_type == 'back':
                insert_at_index = ball_index + 1
            else: 
                insert_at_index = ball_index 

            if insert_at_index == 0:
                shift_chain(chain_list, 0, BALL_SPACING_ON_PATH) 
                # This check is tricky. Let's assume the first ball's index is > 0
                if chain_list:
                    new_path_index = chain_list[0].path_index + BALL_SPACING_ON_PATH
                else:
                    new_path_index = BALL_SPACING_ON_PATH # Just an emergency fallback
            
            elif insert_at_index == len(chain_list):
                new_path_index = chain_list[-1].path_index - BALL_SPACING_ON_PATH
            
            else:
                create_gap(chain_list, insert_at_index, BALL_SPACING_ON_PATH)
                new_path_index = chain_list[insert_at_index - 1].path_index - BALL_SPACING_ON_PATH

            inserted_ball = Ball(shot.letter, new_path_index, shot.base_color)

            chain_list.insert(insert_at_index, inserted_ball)
            all_sprites.add(inserted_ball)
            chain_ball_sprites.add(inserted_ball)

            # --- Combo Logic ---
            while True:
                count, start_idx, end_idx = check_matches(chain_list)

                if count >= 5:
                    for j in range(start_idx, end_idx + 1):
                        chain_list[j].kill()

                    del chain_list[start_idx : end_idx + 1]
                    
                    # <-- **NEW ROLLBACK LOGIC** ---
                    # Check if a gap was created in the middle of the chain
                    if start_idx > 0 and start_idx < len(chain_list):
                        ball_in_front = chain_list[start_idx - 1] # Last ball of leading chain
                        ball_behind = chain_list[start_idx]   # First ball of trailing chain
                        
                        # Calculate the target position for the ball in front
                        target_path_index = ball_behind.path_index + BALL_SPACING_ON_PATH
                        
                        # Calculate how far back we need to move
                        distance_to_move_back = ball_in_front.path_index - target_path_index
                        
                        if distance_to_move_back > 0:
                            # Move all balls in the leading chain (from 0 to start_idx-1)
                            # backward by this amount instantly.
                            print(f"Rolling back leading chain by {distance_to_move_back} units.")
                            for i in range(start_idx):
                                chain_list[i].path_index -= distance_to_move_back
                                chain_list[i].set_pos_from_path_index() # Update positions
                    # --- **END OF NEW ROLLBACK LOGIC** ---
                else:
                    break 
            
            update_chain_colors(chain_list) 

    # --- Check for Win Condition ---
    if not chain_list:
        # If chain is empty, check if any shot balls are still flying
        shot_balls_list_check = [s for s in all_sprites if s not in chain_ball_sprites]
        if not shot_balls_list_check:
            GAME_WON = True

    # --- Drawing ---
    screen.blit(background_image, (0, 0))

    if len(PATH_POINTS_BASE) > 2:
        scaled_path_points = [scale_point(p) for p in PATH_POINTS_BASE]
        pygame.draw.lines(screen, (80, 80, 80), False, scaled_path_points, scale_value(4))

    all_sprites.draw(screen)

    launcher.draw(screen, chain_ball_sprites)

    score_text = GAME_FONT.render(f"Score: {SCORE}", True, WHITE)
    screen.blit(score_text, scale_point((20, 20)))

    speed_text = GAME_FONT.render(f"Speed: {CHAIN_SPEED:.4f}", True, WHITE)
    screen.blit(speed_text, scale_point((20, 60)))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()