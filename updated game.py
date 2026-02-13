import pygame
import sys
import random
import time
import json
import os

pygame.init()

# ================= SETTINGS =================
WIDTH, HEIGHT = 800, 800
GROUND_Y = 650
FPS = 60

WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chaser v5")

clock = pygame.time.Clock()

FONT_BIG = pygame.font.SysFont("consolas", 55, bold=True)
FONT_MED = pygame.font.SysFont("consolas", 32)
FONT_SMALL = pygame.font.SysFont("consolas", 22)

BLACK = (30, 30, 30)
RED = (200, 50, 50)

# ================= HIGH SCORE =================
FILE = "highscore.json"

def load_high():
    if not os.path.exists(FILE):
        with open(FILE, "w") as f:
            json.dump({"distance": 0}, f)
    with open(FILE, "r") as f:
        return json.load(f)

def save_high(distance):
    with open(FILE, "w") as f:
        json.dump({"distance": distance}, f)

highscore = load_high()

# ================= PLAYER =================
class Player:
    def __init__(self, gender="Male"):
        self.x = 150
        self.y = GROUND_Y
        self.vel = 0
        self.gravity = 1.1
        self.jump_power = -20
        self.on_ground = True
        self.invincible = False
        self.inv_time = 0
        self.gender = gender
        self.sprite_width = 50  # Fixed sprite width in pixels
        
        # Load gender-specific sprites
        self.idle_sprite = None
        self.jump_sprite = None
        self._load_sprites()
    
    def _load_sprites(self):
        """Load idle and jump sprites based on gender, scaled to fixed width."""
        gender_map = {
            "Male": "male",
            "Female": "female",
            "Other": "other"
        }
        prefix = gender_map.get(self.gender, "male")
        
        try:
            idle_img = pygame.image.load(f"assets/player/{prefix}_idle.png").convert_alpha()
            jump_img = pygame.image.load(f"assets/player/{prefix}_jump.png").convert_alpha()
            
            # Scale sprites to fixed width while maintaining aspect ratio
            idle_scale = self.sprite_width / idle_img.get_width()
            idle_h = int(idle_img.get_height() * idle_scale)
            self.idle_sprite = pygame.transform.scale(idle_img, (self.sprite_width, idle_h))
            
            jump_scale = self.sprite_width / jump_img.get_width()
            jump_h = int(jump_img.get_height() * jump_scale)
            self.jump_sprite = pygame.transform.scale(jump_img, (self.sprite_width, jump_h))
        except pygame.error:
            # Fallback if sprites not found
            self.idle_sprite = None
            self.jump_sprite = None

    def jump(self):
        if self.on_ground:
            self.vel = self.jump_power
            self.on_ground = False

    def update(self):
        self.vel += self.gravity
        self.y += self.vel

        if self.y >= GROUND_Y:
            self.y = GROUND_Y
            self.vel = 0
            self.on_ground = True

        if self.invincible and time.time() - self.inv_time > 1:
            self.invincible = False

    def _get_display_rect(self):
        """Calculate hitbox that matches rendered sprite exactly."""
        sprite = self.jump_sprite if not self.on_ground else self.idle_sprite
        
        if sprite is not None:
            sprite_w = sprite.get_width()
            sprite_h = sprite.get_height()
            
            # Position: bottom aligned with ground (self.y), centered on self.x
            screen_x = self.x - sprite_w // 2
            screen_y = self.y - sprite_h
            
            # Clamp to screen bounds (prevents sprite going off-screen)
            screen_x = max(0, min(screen_x, WIDTH - sprite_w))
            screen_y = max(0, screen_y)
            
            return pygame.Rect(screen_x, screen_y, sprite_w, sprite_h)
        else:
            # Fallback hitbox for shape-based rendering
            return pygame.Rect(self.x + 10, self.y - 70, 20, 70)

    def draw(self):
        sprite = self.jump_sprite if not self.on_ground else self.idle_sprite
        
        if sprite is not None:
            rect = self._get_display_rect()
            WIN.blit(sprite, (rect.x, rect.y))
        else:
            # Fallback to simple shapes
            color = BLACK if not self.invincible else RED
            # Head
            pygame.draw.rect(WIN, color, (self.x + 10, self.y - 70, 20, 20))
            # Body
            pygame.draw.rect(WIN, color, (self.x + 15, self.y - 50, 10, 30))
            # Legs
            pygame.draw.rect(WIN, color, (self.x + 10, self.y - 20, 8, 20))
            pygame.draw.rect(WIN, color, (self.x + 22, self.y - 20, 8, 20))

    def rect(self):
        return self._get_display_rect()

# ================= OBSTACLE =================
class Obstacle:
    def __init__(self, speed, obstacle_type=None):
        self.x = WIDTH
        self.y = GROUND_Y
        self.speed = speed
        self.hit = False  # Track if spike has spawned diamonds
        
        # Randomly choose obstacle type if not specified
        if obstacle_type is None:
            rand = random.random()
            if rand < 0.6:  # 60% box
                obstacle_type = "box"
            elif rand < 0.85:  # 25% spike
                obstacle_type = "spike"
            else:  # 15% tall
                obstacle_type = "tall"
        
        self.type = obstacle_type
        
        # Set dimensions based on type
        if self.type == "box":
            self.width = 40
            self.height = random.randint(40, 70)
        elif self.type == "spike":
            self.width = 25
            self.height = 60
        elif self.type == "tall":
            self.width = 40
            self.height = random.randint(80, 100)

    def update(self):
        self.x -= self.speed

    def draw(self):
        if self.type == "box":
            pygame.draw.rect(WIN, BLACK,
                             (self.x, self.y - self.height,
                              self.width, self.height))
        elif self.type == "spike":
            # Draw spike as triangle pointing up
            spike_tip_x = self.x + self.width // 2
            spike_base_y = self.y - self.height
            pygame.draw.polygon(WIN, BLACK, [
                (self.x, self.y),
                (self.x + self.width, self.y),
                (spike_tip_x, spike_base_y)
            ])
        elif self.type == "tall":
            pygame.draw.rect(WIN, BLACK,
                             (self.x, self.y - self.height,
                              self.width, self.height))

    def rect(self):
        return pygame.Rect(self.x, self.y - self.height,
                           self.width, self.height)

# ================= DIAMOND =================
class Diamond:
    def __init__(self, speed):
        self.x = WIDTH
        self.y = GROUND_Y - random.randint(120, 180)
        self.speed = speed

    def update(self):
        self.x -= self.speed

    def draw(self):
        pygame.draw.polygon(WIN, (255, 215, 0), [
            (self.x, self.y),
            (self.x + 12, self.y - 12),
            (self.x + 24, self.y),
            (self.x + 12, self.y + 12)
        ])

    def rect(self):
        return pygame.Rect(self.x, self.y - 12, 24, 24)

# ================= INPUT BOX =================
class InputBox:
    def __init__(self, x, y, width, height, label, max_chars=20, numeric=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.text = ""
        self.active = False
        self.max_chars = max_chars
        self.numeric = numeric
        self.cursor_visible = True
        self.cursor_time = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isprintable() and len(self.text) < self.max_chars:
                if self.numeric:
                    if event.unicode.isdigit():
                        self.text += event.unicode
                else:
                    if event.unicode.isalpha() or event.unicode == ' ':
                        self.text += event.unicode

    def update(self):
        self.cursor_time += 1
        if self.cursor_time % 30 == 0:
            self.cursor_visible = not self.cursor_visible

    def draw(self):
        # Draw border
        color = RED if self.active else BLACK
        pygame.draw.rect(WIN, color, self.rect, 2)
        
        # Draw label
        label_surf = FONT_SMALL.render(self.label, True, BLACK)
        WIN.blit(label_surf, (self.rect.x, self.rect.y - 25))
        
        # Draw text
        text_surf = FONT_SMALL.render(self.text, True, BLACK)
        WIN.blit(text_surf, (self.rect.x + 10, self.rect.centery - text_surf.get_height()//2))
        
        # Draw cursor if active
        if self.active and self.cursor_visible:
            cursor_x = self.rect.x + 10 + text_surf.get_width()
            pygame.draw.line(WIN, BLACK, (cursor_x, self.rect.y + 5), 
                           (cursor_x, self.rect.y + self.rect.height - 5), 2)

# ================= DROPDOWN =================
class Dropdown:
    def __init__(self, x, y, width, height, label, options, max_visible=3):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.options = options
        self.selected = None
        self.open = False
        self.hover_index = -1
        self.option_height = height
        self.max_visible = max_visible
        self.scroll_offset = 0
        self.opens_upward = False
        
    def _calculate_position(self):
        """Calculate if dropdown should open upward or downward."""
        space_below = HEIGHT - (self.rect.y + self.rect.height)
        options_height = min(len(self.options), self.max_visible) * self.option_height
        
        # If not enough space below, try opening upward
        if space_below < options_height + 10:  # 10px margin
            space_above = self.rect.y - 60  # Account for label
            if space_above >= options_height:
                self.opens_upward = True
                return
        
        self.opens_upward = False

    def _get_option_rect(self, index):
        """Get the rectangle for an option, accounting for direction."""
        if self.opens_upward:
            option_y = self.rect.y - (index + 1) * self.option_height
        else:
            option_y = self.rect.y + (index + 1) * self.option_height
        
        return pygame.Rect(self.rect.x, option_y, self.rect.width, self.option_height)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Clicked on dropdown box itself
            if self.rect.collidepoint(event.pos):
                self.open = not self.open
                self.hover_index = -1
                self.scroll_offset = 0
                if self.open:
                    self._calculate_position()
                return True  # Consume click when toggling
            
            # Clicked on an option (only if open)
            elif self.open:
                visible_options = min(len(self.options), self.max_visible)
                for i in range(visible_options):
                    actual_index = i + self.scroll_offset
                    option_rect = self._get_option_rect(i)
                    if option_rect.collidepoint(event.pos):
                        self.selected = self.options[actual_index]
                        self.open = False
                        self.scroll_offset = 0
                        return True  # Selection made - consume click
                
                return True  # Click was on dropdown area but not an option
        
        # Track hover for visual feedback
        if self.open:
            visible_options = min(len(self.options), self.max_visible)
            for i in range(visible_options):
                option_rect = self._get_option_rect(i)
                if option_rect.collidepoint(pygame.mouse.get_pos()):
                    self.hover_index = i
                    return
            self.hover_index = -1
        
        return False  # Event not handled by dropdown

    def draw(self):
        # Draw main dropdown box
        box_color = RED if self.open else BLACK
        pygame.draw.rect(WIN, box_color, self.rect, 2)
        
        # Draw label above dropdown
        label_surf = FONT_SMALL.render(self.label, True, BLACK)
        WIN.blit(label_surf, (self.rect.x, self.rect.y - 25))
        
        # Draw selected value or placeholder
        display_text = self.selected if self.selected else "Select Gender"
        text_surf = FONT_SMALL.render(display_text, True, BLACK)
        WIN.blit(text_surf, (self.rect.x + 10, 
                            self.rect.centery - text_surf.get_height()//2))
        
        # Draw dropdown arrow indicator (flip if opening upward)
        arrow_x = self.rect.right - 15
        arrow_y = self.rect.centery
        if self.opens_upward:
            # Arrow pointing up
            pygame.draw.polygon(WIN, BLACK, [
                (arrow_x - 5, arrow_y + 3),
                (arrow_x + 5, arrow_y + 3),
                (arrow_x, arrow_y - 3)
            ])
        else:
            # Arrow pointing down
            pygame.draw.polygon(WIN, BLACK, [
                (arrow_x - 5, arrow_y - 3),
                (arrow_x + 5, arrow_y - 3),
                (arrow_x, arrow_y + 3)
            ])
        
        # Draw options if dropdown is open
        if self.open:
            visible_options = min(len(self.options), self.max_visible)
            
            for i in range(visible_options):
                actual_index = i + self.scroll_offset
                option_rect = self._get_option_rect(i)
                
                # Highlight hovered option
                if i == self.hover_index:
                    pygame.draw.rect(WIN, (200, 200, 200), option_rect)
                
                # Draw option background
                pygame.draw.rect(WIN, (255, 255, 255), option_rect)
                
                # Draw option border
                pygame.draw.rect(WIN, BLACK, option_rect, 1)
                
                # Draw option text
                option_text = FONT_SMALL.render(self.options[actual_index], True, BLACK)
                WIN.blit(option_text, (option_rect.x + 10,
                                      option_rect.centery - option_text.get_height()//2))
            
            # Draw scroll indicator if there are more options than visible
            if len(self.options) > self.max_visible:
                scroll_text = FONT_SMALL.render(
                    f"({self.scroll_offset + visible_options}/{len(self.options)})", 
                    True, (100, 100, 100)
                )
                last_option_rect = self._get_option_rect(visible_options - 1)
                WIN.blit(scroll_text, (last_option_rect.x + 10, 
                                      last_option_rect.y + last_option_rect.height + 5))

# ================= BUTTON =================
class Button:
    def __init__(self, text, x, y, width=220, height=60, toggle=False):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.toggle = toggle
        self.selected = False

    def draw(self):
        if self.selected and self.toggle:
            pygame.draw.rect(WIN, RED, self.rect)
            color = (255, 255, 255)
        else:
            pygame.draw.rect(WIN, BLACK, self.rect, 2)
            color = BLACK
        
        label = FONT_SMALL.render(self.text, True, color)
        WIN.blit(label,
                 (self.rect.centerx - label.get_width()//2,
                  self.rect.centery - label.get_height()//2))

    def clicked(self, pos):
        return self.rect.collidepoint(pos)

# ================= CLOUD =================
class Cloud:
    def __init__(self, speed):
        self.x = WIDTH + 50
        self.y = random.randint(50, 250)
        self.speed = speed
        self.width = random.randint(60, 100)
        self.height = random.randint(30, 50)

    def update(self):
        self.x -= self.speed * 0.3

    def draw(self):
        # Simple cloud shape using circles
        pygame.draw.circle(WIN, (220, 220, 220), (self.x, self.y), self.height//2)
        pygame.draw.circle(WIN, (220, 220, 220), (self.x + 20, self.y - 10), self.height//2 + 5)
        pygame.draw.circle(WIN, (220, 220, 220), (self.x + 40, self.y), self.height//2)
        pygame.draw.circle(WIN, (220, 220, 220), (self.x + 60, self.y - 8), self.height//2)
        pygame.draw.rect(WIN, (220, 220, 220), (self.x, self.y - self.height//2, self.width, self.height//2 + 5))

    def off_screen(self):
        return self.x < -100

# ================= VARIABLES =================
state = "login"
username = ""
age = ""
gender = ""
error_message = ""

# Login UI elements
username_box = InputBox(WIDTH//2 - 150, 330, 300, 40, "Username:")
age_box = InputBox(WIDTH//2 - 150, 420, 300, 40, "Age:", max_chars=2, numeric=True)
gender_dropdown = Dropdown(WIDTH//2 - 150, 510, 300, 40, "Gender:", ["Male", "Female"])
start_btn = Button("START GAME", WIDTH//2 - 110, 700, 220, 60)

player = Player("Male")  # Default, will be replaced when user selects gender
lives = 3
distance = 0
diamonds_collected = 0
speed = 5
obstacles = []
diamonds = []
clouds = []
last_spawn = 0
last_cloud_spawn = 0
start_time = 0

play_btn = Button("Play Again", WIDTH//2 - 240, 500)
exit_btn = Button("Exit", WIDTH//2 + 20, 500)

def reset():
    global player, lives, distance, diamonds_collected, speed
    global obstacles, diamonds, clouds, last_spawn, last_cloud_spawn, start_time
    global username_box, age_box, gender_dropdown, gender

    player = Player(gender)
    lives = 3
    distance = 0
    diamonds_collected = 0
    speed = 5
    obstacles = []
    diamonds = []
    clouds = []
    last_spawn = 0
    last_cloud_spawn = 0
    start_time = time.time()
    
    # Reset login UI
    username_box.text = ""
    age_box.text = ""
    username_box.active = False
    age_box.active = False
    gender_dropdown.selected = None
    gender_dropdown.open = False

# ================= DAY/NIGHT =================
def get_sky():
    t = (time.time() * 0.05) % 2
    if t < 1:
        return (135 + int(40*t),
                206 - int(60*t),
                235 - int(100*t))
    else:
        t -= 1
        return (175 - int(40*t),
                146 + int(60*t),
                135 + int(100*t))

# ================= MAIN LOOP =================
running = True
while running:
    clock.tick(FPS)
    WIN.fill(get_sky())

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # LOGIN
        if state == "login":
            username_box.handle_event(event)
            age_box.handle_event(event)
            
            # Handle dropdown and prevent other clicks if it's open
            dropdown_consumed = gender_dropdown.handle_event(event)
            
            if event.type == pygame.MOUSEBUTTONDOWN and not dropdown_consumed:
                if start_btn.clicked(event.pos):
                    if username_box.text == "":
                        error_message = "Username required"
                    elif not age_box.text.isdigit() or not (10 <= int(age_box.text) <= 50):
                        error_message = "Invalid age (10-50 only)"
                    elif gender_dropdown.selected is None:
                        error_message = "Select gender"
                    else:
                        username = username_box.text
                        age = age_box.text
                        gender = gender_dropdown.selected
                        reset()
                        state = "playing"
                        error_message = ""

        # PLAYING
        elif state == "playing":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()

        # RESULT
        elif state == "result":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_btn.clicked(event.pos):
                    reset()
                    state = "playing"
                if exit_btn.clicked(event.pos):
                    running = False

    # ================= DRAW LOGIN =================
    if state == "login":

        # Titles centered
        title1 = FONT_MED.render("Welcome to the Game", True, BLACK)
        title2 = FONT_BIG.render("CHASER", True, BLACK)

        WIN.blit(title1, (WIDTH//2 - title1.get_width()//2, 80))
        WIN.blit(title2, (WIDTH//2 - title2.get_width()//2, 140))

        # Update and draw input boxes
        username_box.update()
        age_box.update()
        username_box.draw()
        age_box.draw()

        # Draw gender dropdown
        gender_dropdown.draw()

        # Draw start button
        start_btn.draw()

        # Draw error message if any
        if error_message:
            err = FONT_SMALL.render(error_message, True, RED)
            WIN.blit(err, (WIDTH//2 - err.get_width()//2, 700))

    # ================= PLAYING =================
    elif state == "playing":

        pygame.draw.line(WIN, BLACK, (0, GROUND_Y), (WIDTH, GROUND_Y), 3)

        # Spawn clouds
        if time.time() - last_cloud_spawn > 3:
            clouds.append(Cloud(speed))
            last_cloud_spawn = time.time()

        # Update and draw clouds (behind everything)
        for cloud in clouds[:]:
            cloud.update()
            cloud.draw()
            if cloud.off_screen():
                clouds.remove(cloud)

        player.update()
        player.draw()

        # Controlled spawn spacing
        if time.time() - last_spawn > 1.5:
            obstacles.append(Obstacle(speed))
            if random.random() > 0.2:
                diamonds.append(Diamond(speed))
            last_spawn = time.time()

        for obs in obstacles[:]:
            obs.update()
            obs.draw()
            if obs.rect().colliderect(player.rect()):
                if not player.invincible:
                    lives -= 1
                    player.invincible = True
                    player.inv_time = time.time()
                    
                    # Spawn diamonds if hit a spike (only once per spike)
                    if obs.type == "spike" and not obs.hit:
                        obs.hit = True
                        num_diamonds = random.randint(1, 3)
                        for _ in range(num_diamonds):
                            # Create diamond at spike position with slight offset
                            diamond = Diamond(speed)
                            diamond.x = obs.x + obs.width // 2
                            diamond.y = obs.y - obs.height - 20
                            diamonds.append(diamond)
                    
                    if lives <= 0:
                        state = "result"

        for dia in diamonds[:]:
            dia.update()
            dia.draw()
            if dia.rect().colliderect(player.rect()):
                diamonds_collected += 1
                diamonds.remove(dia)

        distance += speed * 0.05

        if distance > 300:
            speed = 10
        elif distance > 150:
            speed = 7

        WIN.blit(FONT_SMALL.render(f"Time: {int(time.time()-start_time)}", True, BLACK), (20, 20))
        WIN.blit(FONT_SMALL.render(f"Distance: {int(distance)}", True, BLACK), (20, 50))
        lives_text = FONT_SMALL.render(f"Lives: {lives}", True, BLACK)
        WIN.blit(lives_text, (WIDTH - lives_text.get_width() - 20, 20))
        diamonds_text = FONT_SMALL.render(f"Diamonds: {diamonds_collected}", True, BLACK)
        WIN.blit(diamonds_text, (WIDTH - diamonds_text.get_width() - 20, 50))

    # ================= RESULT =================
    elif state == "result":

        text = FONT_BIG.render("GAME OVER", True, BLACK)
        WIN.blit(text, (WIDTH//2 - text.get_width()//2, 200))

        stats = FONT_MED.render(
            f"Distance: {int(distance)}   Diamonds: {diamonds_collected}",
            True, BLACK)
        WIN.blit(stats, (WIDTH//2 - stats.get_width()//2, 300))

        play_btn.draw()
        exit_btn.draw()

    pygame.display.update()

pygame.quit()
sys.exit()