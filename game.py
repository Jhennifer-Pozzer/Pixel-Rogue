# game.py
# Roguelike top-down usando Pygame Zero (PgZero)
# Apenas módulos permitidos: pgzero, math, random, Rect do pygame
from pgzero.builtins import keyboard, mouse, Actor, animate, images, music, sounds
from pygame import Rect
import math
import random

# --- Configurações gerais do jogo ---
WIDTH = 768
HEIGHT = 576
TILE_SIZE = 48
GRID_W = WIDTH // TILE_SIZE
GRID_H = HEIGHT // TILE_SIZE

# Estados do jogo
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_GAMEOVER = "gameover"

# Arquivos de imagens (sprites)
PLAYER_IDLE = ["hero_idle_1", "hero_idle_2"]
PLAYER_MOVE = ["hero_walk_1", "hero_walk_2", "hero_walk_3", "hero_walk_4"]
ENEMY_IDLE = ["enemy_idle_1", "enemy_idle_2"]
ENEMY_MOVE = ["enemy_walk_1", "enemy_walk_2"]
BACKGROUND_IMAGE = "dungeon_floor"
BUTTON_IMAGE = "button"

# Arquivos de som
SOUND_HIT = "hit"
SOUND_DEATH = "death"
SOUND_TOGGLE = "toggle"
MUSIC_BG = "bg_music"

# --- Função auxiliar: converte célula da grade para coordenada em pixels ---
def grid_to_pixel(cell_x, cell_y):
    return cell_x * TILE_SIZE + TILE_SIZE // 2, cell_y * TILE_SIZE + TILE_SIZE // 2


# --- Classe para animação de sprites ---
class SpriteAnimation:
    def __init__(self, frames, frame_time=0.18, loop=True):
        self.frames = frames[:]
        self.frame_time = frame_time
        self.loop = loop
        self.time = 0.0
        self.index = 0

    # Atualiza a animação com base no tempo
    def update(self, dt):
        self.time += dt
        if self.time >= self.frame_time:
            steps = int(self.time / self.frame_time)
            self.time -= steps * self.frame_time
            self.index += steps
            if self.loop:
                self.index %= len(self.frames)
            else:
                self.index = min(self.index, len(self.frames) - 1)

    # Retorna o frame atual
    def current(self):
        return self.frames[self.index % len(self.frames)]


# --- Classe base para qualquer personagem (herói e inimigos) ---
class Character:
    def __init__(self, cell_x, cell_y, idle_frames, move_frames, speed=6):
        # Célula atual na grade
        self.cell_x = cell_x
        self.cell_y = cell_y

        # Converte para pixels
        self.x, self.y = grid_to_pixel(cell_x, cell_y)
        self.target_x, self.target_y = self.x, self.y
        self.speed = speed  # velocidade em pixels por segundo

        # Animações
        self.idle_anim = SpriteAnimation(idle_frames, frame_time=0.4)
        self.move_anim = SpriteAnimation(move_frames, frame_time=0.12)

        self.facing_angle = 0.0
        self.actor = Actor(idle_frames[0], (self.x, self.y))
        self.is_moving = False
        self.hp = 3

    # Define nova célula de destino
    def set_target_cell(self, tx, ty):
        self.cell_x = tx
        self.cell_y = ty
        self.target_x, self.target_y = grid_to_pixel(tx, ty)
        self.is_moving = True

    # Movimento suave entre células
    def update_position(self, dt):
        if not self.is_moving:
            self.x, self.y = self.target_x, self.target_y
            return
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            self.x, self.y = self.target_x, self.target_y
            self.is_moving = False
        else:
            step = self.speed * dt * TILE_SIZE
            ratio = min(1, step / dist)
            self.x += dx * ratio
            self.y += dy * ratio
            self.facing_angle = math.degrees(math.atan2(dy, dx))
        self.actor.pos = (self.x, self.y)

    # Atualiza qual animação usar
    def update_animation(self, dt):
        if self.is_moving:
            self.move_anim.update(dt)
            self.actor.image = self.move_anim.current()
        else:
            self.idle_anim.update(dt)
            self.actor.image = self.idle_anim.current()

    # Desenha o personagem
    def draw(self):
        self.actor.pos = (self.x, self.y)
        self.actor.draw()

    # Retângulo para colisão
    def rect(self):
        w = h = TILE_SIZE * 0.6
        return Rect(self.x - w / 2, self.y - h / 2, w, h)


# --- Classe do jogador ---
class Player(Character):
    def __init__(self, cell_x, cell_y):
        super().__init__(cell_x, cell_y, PLAYER_IDLE, PLAYER_MOVE, speed=6)
        self.score = 0

    # Tentativa de movimento (somente quando parado)
    def try_move(self, dx, dy):
        if self.is_moving:
            return
        nx, ny = self.cell_x + dx, self.cell_y + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
            self.set_target_cell(nx, ny)


# --- Classe dos inimigos ---
class Enemy(Character):
    def __init__(self, cell_x, cell_y, territory_radius=3):
        super().__init__(cell_x, cell_y, ENEMY_IDLE, ENEMY_MOVE, speed=4)
        self.territory_center = (cell_x, cell_y)
        self.territory_radius = territory_radius
        self.action_timer = random.uniform(0.2, 1.2)

    # IA simples: anda aleatoriamente dentro do território
    def update_ai(self, dt):
        self.action_timer -= dt
        if self.is_moving:
            return
        if self.action_timer <= 0:
            self.action_timer = random.uniform(0.6, 1.8)

            cx, cy = self.territory_center
            choices = []
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1),(0,0)]:
                nx, ny = self.cell_x + dx, self.cell_y + dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                    if math.hypot(nx - cx, ny - cy) <= self.territory_radius:
                        choices.append((nx, ny))

            if choices:
                nx, ny = random.choice(choices)
                if random.random() < 0.2:
                    return
                if nx != self.cell_x or ny != self.cell_y:
                    self.set_target_cell(nx, ny)


# --- Classe do botão do menu ---
class Button:
    def __init__(self, x, y, text, action):
        self.x = x
        self.y = y
        self.text = text
        self.action = action
        self.actor = Actor(BUTTON_IMAGE, (x, y))

    def draw(self):
        self.actor.draw()
        screen.draw.text(self.text, center=(self.x, self.y),
                         fontsize=28, color="white")

    def check_click(self, pos):
        if self.actor.collidepoint(pos):
            self.action()


# --- Variáveis globais do jogo ---
game_state = STATE_MENU
player = None
enemies = []
buttons = []
music_on = True


# --- Funções principais do jogo ---
def start_new_game():
    """Inicia uma nova partida."""
    global player, enemies, game_state
    player = Player(GRID_W // 2, GRID_H // 2)
    enemies = []

    # Cria inimigos aleatórios
    for i in range(6):
        ex = random.randint(1, GRID_W - 2)
        ey = random.randint(1, GRID_H - 2)
        enemy = Enemy(ex, ey, territory_radius=random.randint(2, 4))
        enemies.append(enemy)

    game_state = STATE_PLAYING
    play_music()


def toggle_music():
    """Liga ou desliga a música."""
    global music_on
    music_on = not music_on
    if music_on:
        play_music()
    else:
        music.stop()
    sounds.toggle.play()


def exit_game():
    """Sai do jogo."""
    import sys
    sys.exit(0)


def play_music():
    """Toca música de fundo."""
    if music_on:
        try:
            music.play(MUSIC_BG)
            music.set_volume(0.5)
        except:
            pass


def create_menu():
    """Cria os botões do menu inicial."""
    global buttons
    buttons = []
    cx = WIDTH // 2
    buttons.append(Button(cx, HEIGHT // 2 - 60, "Iniciar Jogo", start_new_game))
    buttons.append(Button(cx, HEIGHT // 2, "Música On/Off", toggle_music))
    buttons.append(Button(cx, HEIGHT // 2 + 60, "Sair", exit_game))


create_menu()


# --- Atualização por frame ---
def update(dt):
    global game_state
    if game_state == STATE_PLAYING and player:

        # Movimento do jogador
        if not player.is_moving:
            if keyboard.left:
                player.try_move(-1, 0)
            elif keyboard.right:
                player.try_move(1, 0)
            elif keyboard.up:
                player.try_move(0, -1)
            elif keyboard.down:
                player.try_move(0, 1)

        player.update_position(dt)
        player.update_animation(dt)

        # Atualiza inimigos
        for e in enemies:
            e.update_ai(dt)
            e.update_position(dt)
            e.update_animation(dt)

            # Verifica colisão com jogador
            if e.rect().colliderect(player.rect()):
                player.hp -= 1
                sounds.hit.play()

                # empurrão (knockback)
                if not player.is_moving:
                    dx = player.cell_x - e.cell_x
                    dy = player.cell_y - e.cell_y
                    if abs(dx) + abs(dy) > 0:
                        sx = int(math.copysign(1, dx)) if dx != 0 else 0
                        sy = int(math.copysign(1, dy)) if dy != 0 else 0
                        nx = max(0, min(GRID_W - 1, player.cell_x + sx))
                        ny = max(0, min(GRID_H - 1, player.cell_y + sy))
                        player.set_target_cell(nx, ny)

                if player.hp <= 0:
                    sounds.death.play()
                    game_state = STATE_GAMEOVER


# --- Desenho na tela ---
def draw():
    screen.clear()

    if game_state == STATE_MENU:
        screen.fill((25, 25, 30))
        screen.draw.text(
            "Pixel Rogue",
            center=(WIDTH // 2, HEIGHT // 2 - 140),
            fontsize=64,
            color="white"
        )

        for b in buttons:
            b.draw()

        screen.draw.text(
            "Use as setas para mover. Evite os inimigos.",
            center=(WIDTH // 2, HEIGHT - 40),
            fontsize=22,
            color="lightgray"
        )

    elif game_state == STATE_PLAYING:
        # Desenha o piso
        for gx in range(GRID_W):
            for gy in range(GRID_H):
                screen.blit(BACKGROUND_IMAGE, (gx * TILE_SIZE, gy * TILE_SIZE))

        # Desenha inimigos e jogador
        for e in enemies:
            e.draw()

        if player:
            player.draw()

        # Interface (HUD)
        screen.draw.text(f"VP: {player.hp}", (10, 10), fontsize=30, color="white")
        screen.draw.text(f"Inimigos: {len(enemies)}", (10, 44), fontsize=20, color="white")

    elif game_state == STATE_GAMEOVER:
        screen.fill((0, 0, 0))
        screen.draw.text("GAME OVER", center=(WIDTH // 2, HEIGHT // 2 - 20),
                         fontsize=64, color="red")
        screen.draw.text("Aperte Enter para voltar ao menu",
                         center=(WIDTH // 2, HEIGHT // 2 + 40),
                         fontsize=28, color="white")


# --- Eventos de mouse ---
def on_mouse_down(pos):
    if game_state == STATE_MENU:
        for b in buttons:
            b.check_click(pos)


# --- Eventos de teclado ---
def on_key_down(key):
    global game_state
    if game_state == STATE_GAMEOVER and key == keys.RETURN:
        create_menu()
        game_state = STATE_MENU

    if key == keys.ESCAPE:
        create_menu()
        game_state = STATE_MENU
