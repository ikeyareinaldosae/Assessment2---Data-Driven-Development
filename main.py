import pygame
import json
import os

# --- Setup ---
pygame.init()
WIDTH, HEIGHT = 1000, 800
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("💰 Click Tycoon")
font_path = "./assets/fonts/LuckiestGuy-Regular.ttf"
font = pygame.font.Font(font_path, 28)
small_font = pygame.font.Font(font_path, 20)
clock = pygame.time.Clock()

slash_sound = pygame.mixer.Sound("./assets/sounds/slash.wav")
coin_sound = pygame.mixer.Sound("./assets/sounds/coin.wav")
purchase_sound = pygame.mixer.Sound("./assets/sounds/purchase.wav")

slash_sound.set_volume(0.3)
coin_sound.set_volume(0.3)
purchase_sound.set_volume(0.3)

# --- Assets ---
bg_img = pygame.image.load("./assets/bamboo-bg.png").convert()
bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
ts_img = pygame.image.load("./assets/title_screen.png").convert()
ts_img = pygame.transform.scale(ts_img, (WIDTH, HEIGHT))
coin_img = pygame.image.load("./assets/coin.png").convert_alpha()

upgrade_btn = pygame.image.load("./assets/upgrade-btn.png").convert()
gray_btn = "./assets/gray-btn.png"
red_btn = "./assets/red-btn.png"
green_btn = "./assets/green-btn.png"

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (50, 205, 50)
GRAY = (180, 180, 180)
RED = (255, 80, 80)
YELLOW = (255, 200, 0)
DARK_GREEN = (58, 71, 16)

# ============================================================
# 🥷 ANIMATION SYSTEM
# ============================================================
def load_animation(folder):
    """Load all PNGs from a folder as animation frames."""
    frames = []
    for filename in sorted(os.listdir(folder)):
        if filename.endswith(".png"):
            path = os.path.join(folder, filename)
            img = pygame.image.load(path).convert_alpha()
            frames.append(img)
    return frames

class AnimatedSprite:
    def __init__(self, x, y, animations, frame_speed=0.08):
        self.animations = animations  # dict: {"idle": [...], "slash": [...]}
        self.state = "idle"
        self.frame_index = 0
        self.frame_speed = frame_speed
        self.frame_timer = 0
        self.image = self.animations[self.state][self.frame_index]
        self.rect = self.image.get_rect(center=(x, y))

    def play(self, state, override=False):
        """Switch animation state (e.g., idle → slash)."""
        if self.state != state or override:
            self.state = state
            self.frame_index = 0
            self.frame_timer = 0
            self.image = self.animations[self.state][self.frame_index]

    def update(self, dt):
        frames = self.animations[self.state]
        self.frame_timer += dt

        if self.frame_timer >= self.frame_speed:
            self.frame_timer = 0
            self.frame_index += 1

            if self.frame_index >= len(frames):
                # if slash finished → go back to idle
                if self.state == "slash":
                    self.state = "idle"
                self.frame_index = 0

            self.image = self.animations[self.state][self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)

# ============================================================
# 💾 GAME DATA
# ============================================================
class GameData:
    def __init__(self, filename="save.json"):
        self.filename = filename
        self.data = {"money": 0, "per_click": 1, "auto": 0, "name": ""}
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                self.data = json.load(f)

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f)

    def reset(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
        self.data = {"money": 0, "per_click": 1, "auto": 0, "name": ""}
        print("Game reset!")


# ============================================================
# 🎛️ BUTTON CLASS
# ============================================================
class Button:
    def __init__(self, x, y, image_path, text="", text_color=DARK_GREEN):
        self.image_default = pygame.image.load(image_path).convert_alpha()
        base, ext = os.path.splitext(image_path)
        hover_path = f"{base}-hover{ext}"

        # Check if hover image exists
        if os.path.exists(hover_path):
            self.image_hover = pygame.image.load(hover_path).convert_alpha()
        else:
            self.image_hover = self.image_default  # fallback

        self.image = self.image_default
        self.rect = self.image.get_rect(topleft=(x, y))
        self.text = text
        self.text_color = text_color

    def draw(self, surface):
        # Update image based on hover state
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            self.image = self.image_hover
        else:
            self.image = self.image_default

        # Draw button
        surface.blit(self.image, self.rect)
        
        # Center text inside button
        if self.text:
            label = font.render(self.text, True, self.text_color)
            surface.blit(
                label,
                (
                    self.rect.centerx - (label.get_width() / 2) + 5,
                    self.rect.centery - (label.get_height() / 2) + 5,
                ),
            )

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)
    

# ============================================================
# ✨ POPUP TEXT
# ============================================================
class PopupText:
    def __init__(self, text, x, y, color=(255, 255, 255)):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.alpha = 255  # start fully visible
        self.lifetime = 2.0  # seconds
        self.timer = 0

        # Render text to a surface
        self.surface = font.render(self.text, True, self.color).convert_alpha()

    def update(self, dt):
        self.timer += dt
        self.y -= 30 * dt  # move upward
        self.alpha = max(0, 255 * (1 - self.timer / self.lifetime))
        self.surface.set_alpha(int(self.alpha))

    def draw(self, surface):
        surface.blit(self.surface, (self.x, self.y))

    def is_alive(self):
        return self.timer < self.lifetime


# ============================================================
# 🪙 UPGRADE CLASS
# ============================================================
class Upgrade:
    def __init__(self, name, base_cost, type_, value):
        """
        name: str — display name
        base_cost: int — starting price
        type_: str — "click" or "auto"
        value: int — how much it increases per purchase
        """
        self.name = name
        self.base_cost = base_cost
        self.type = type_
        self.value = value
        self.level = 0

    def cost(self):
        """Scale cost exponentially with level"""
        return int(self.base_cost * (1.5 ** self.level))

    def apply(self, data):
        """Apply upgrade effect to game data"""
        if self.type == "click":
            data["per_click"] += self.value
        elif self.type == "auto":
            data["auto"] += self.value
        self.level += 1


# ============================================================
# 🕹️ MAIN GAME CLASS
# ============================================================
class TycoonGame:
    def __init__(self):
        self.data = GameData()
        self.save_exists = os.path.exists(self.data.filename)
        self.player_name = self.data.data.get("name", "")
        self.state = "opening"
        self.confirm_new = False  # New game confirmation flag

        self.popups = []

        # Load ninja animations
        idle_frames = load_animation("./assets/ninja/idle")
        slash_frames = load_animation("./assets/ninja/slash")
        bamboo_idle_frames = load_animation("./assets/breakables/bamboo/idle")
        bamboo_slash_frames = load_animation("./assets/breakables/bamboo/slash")
        self.ninja = AnimatedSprite(400, 600, {"idle": idle_frames, "slash": slash_frames}, frame_speed=0.1)
        self.bamboo = AnimatedSprite(600, 600, {"idle": bamboo_idle_frames, "slash": bamboo_slash_frames})

        # UI setup
        self.newgame_btn = Button(350, 300, "./assets/green-btn.png", "NEW GAME", WHITE)
        self.loadgame_btn = Button(350, 400, "./assets/green-btn.png", "LOAD GAME", WHITE)
        self.quit_btn = Button(350, 500, "./assets/red-btn.png", "QUIT", WHITE)
        self.click_btn = Button(840, 650, "./assets/slash-btn.png")
        self.reset_btn = Button(15, 500, "./assets/red-btn.png", "RESET")
        self.confirm_yes_btn = Button(350, 500, "./assets/green-btn.png", "YES", WHITE)
        self.confirm_no_btn = Button(350, 580, "./assets/red-btn.png", "NO", WHITE)

        # --- Upgrade system ---
        self.upgrades = [
            Upgrade("Katana", 20, "click", 1),
            Upgrade("Meditation", 100, "auto", 1),
            Upgrade("Zen State", 500, "auto", 5),
        ]
        self.upgrade_buttons = []
        y = 280
        for i, upgrade in enumerate(self.upgrades):
            btn = Button(15, y + i * 70, "./assets/upgrade-btn.png", "")
            self.upgrade_buttons.append(btn)

        self.auto_timer = 0


    # --- Draw helpers ---
    def draw_text(self, text, x, y, color=BLACK, size=28):
        label = font.render(text, True, color)
        screen.blit(label, (x, y))

    # --- Screens ---
    def opening_screen(self):
        screen.blit(ts_img, (0, 0))

        if self.save_exists:
            self.loadgame_btn.color = GREEN
            self.loadgame_btn.text_color = WHITE
        else:
            self.loadgame_btn.color = GRAY  # gray out
            self.loadgame_btn.text_color = BLACK

        # Draw menu buttons
        for btn in [self.newgame_btn, self.loadgame_btn, self.quit_btn]:
            btn.draw(screen)

        # Confirmation popup
        if self.confirm_new:
            rect = pygame.Rect(0, 0, 500, 300)
            rect.center = (WIDTH // 2, HEIGHT // 1.6)
            pygame.draw.rect(screen, DARK_GREEN, rect, 0, 10)
            self.draw_text("Start a new game?", 350, 380, WHITE, 22)
            self.draw_text("All progress will be lost!", 320, 430, WHITE, 22)
            self.confirm_yes_btn.draw(screen)
            self.confirm_no_btn.draw(screen)

    def draw_name_input(self):
        screen.fill(WHITE)
        self.draw_text("Enter your name:", WIDTH / 2 - 100, 200)
        self.draw_text(self.player_name + "|", WIDTH / 2 - 100, 250, GREEN)
        self.draw_text("(Press Enter to continue)", WIDTH / 2 - 130, 300, BLACK, 20)

    def draw_game_screen(self):
        screen.blit(bg_img, (0, 0))
        self.ninja.draw(screen)
        self.bamboo.draw(screen)
        screen.blit(coin_img, (30, 710))
        for popup in self.popups:
            popup.draw(screen)

        d = self.data.data
        self.draw_text(f"{d['name']}", 400, 80)
        self.draw_text(f"{int(d['money'])}", 75, 730)
        self.draw_text(f"Per Click: +{d['per_click']}", 30, 70, WHITE)
        self.draw_text(f"Auto Income: {d['auto']}/sec", 30, 110, WHITE)

        self.click_btn.draw(screen)
        for upgrade, btn in zip(self.upgrades, self.upgrade_buttons):
            btn.text = f"{upgrade.name} (${upgrade.cost()})"
            btn.draw(screen)

        self.reset_btn.draw(screen)

    # --- Logic ---
    def upgrade_click(self):
        d = self.data.data
        cost = d["per_click"] * 20
        if d["money"] >= cost:
            d["money"] -= cost
            d["per_click"] += 1

    def hire_worker(self):
        d = self.data.data
        cost = (d["auto"] + 1) * 100
        if d["money"] >= cost:
            d["money"] -= cost
            d["auto"] += 1

    # --- Handle mouse clicks ---
    def handle_click(self, pos):
        if self.state == "opening":
            if self.confirm_new:
                if self.confirm_yes_btn.is_clicked(pos):
                    self.data.reset()
                    self.player_name = ""
                    self.save_exists = os.path.exists(self.data.filename)
                    self.confirm_new = False
                    self.state = "name_input"

                elif self.confirm_no_btn.is_clicked(pos):
                    self.confirm_new = False
                return
            
            else:
                if self.newgame_btn.is_clicked(pos):
                    self.confirm_new = True

                elif self.loadgame_btn.is_clicked(pos):
                    if self.save_exists:  # only works if save exists
                        self.data.load()
                        self.player_name = self.data.data.get("name", "")
                        self.state = "main_game" if self.player_name else "name_input"
                    else:
                        print("⚠️ No save file found — cannot load.")
                elif self.quit_btn.is_clicked(pos):
                    pygame.quit()
                    exit()

        elif self.state == "main_game":
            if self.click_btn.is_clicked(pos):
                amount = self.data.data["per_click"]
                self.data.data["money"] += amount
                self.popups.append(PopupText(f"+{amount}", pos[0], pos[1], (255, 255, 0)))
                self.ninja.play("slash", override=True)
                self.bamboo.play("slash", override=True)

                # sounds
                slash_sound.play()
                coin_sound.play()
           
            elif self.reset_btn.is_clicked(pos):
                self.data.reset()
                self.player_name = ""
                self.state = "opening"

            # Handle all upgrades
            for upgrade, btn in zip(self.upgrades, self.upgrade_buttons):
                if btn.is_clicked(pos):
                    cost = upgrade.cost()
                    if self.data.data["money"] >= cost:
                        self.data.data["money"] -= cost
                        upgrade.apply(self.data.data)
                        self.popups.append(PopupText(f"{upgrade.name} +", 500, 800, (0, 255, 0)))
                        purchase_sound.play()
                    else:
                        self.popups.append(PopupText(f"Not enough gold!", 400, 700, RED))

    # --- Main loop ---
    def run(self):
        running = True
        while running:
            dt = clock.tick(FPS) / 1000
            self.popups = [p for p in self.popups if p.is_alive()]
            for p in self.popups:
                p.update(dt)
            self.auto_timer += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.data.save()
                    running = False

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)

                if self.state == "name_input":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN and self.player_name.strip():
                            self.data.data["name"] = self.player_name
                            self.data.save()
                            self.state = "main_game"
                        elif event.key == pygame.K_BACKSPACE:
                            self.player_name = self.player_name[:-1]
                        else:
                            if len(self.player_name) < 12 and event.unicode.isprintable():
                                self.player_name += event.unicode

            # Auto income
            if self.state == "main_game" and self.auto_timer >= 1:
                self.data.data["money"] += self.data.data["auto"]
                self.auto_timer = 0
            
            if self.state == "main_game":
                self.data.save()
                self.ninja.update(dt)
                self.bamboo.update(dt)

            # Draw screen
            if self.state == "opening":
                self.opening_screen()
            elif self.state == "name_input":
                self.draw_name_input()
            elif self.state == "main_game":
                self.draw_game_screen()

            pygame.display.flip()

        pygame.quit()


# --- Run ---
if __name__ == "__main__":
    TycoonGame().run()
