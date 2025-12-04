import sys
import random
import math
import os

import pygame

from scripts.utils import load_image, load_images, Animation
from scripts.entities import PhysicsEntity, Player, Enemy
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds
from scripts.particle import Particle
from scripts.spark import Spark


class Game:
    def __init__(self):
        pygame.init()

        pygame.display.set_caption("Platformia")
        self.screen = pygame.display.set_mode((640, 480))
        self.display = pygame.Surface((320, 240), pygame.SRCALPHA)
        self.display_2 = pygame.Surface((320, 240))

        self.clock = pygame.time.Clock()
        self.movement = [False, False]

        self.assets = {
            'decor': load_images('tiles/decor'),
            'grass': load_images('tiles/grass'),
            'large_decor': load_images('tiles/large_decor'),
            'stone': load_images('tiles/stone'),
            'player': load_image('entities/player.png'),
            'background': load_image('UPDATED-BACKGROUND3.png'),
            'clouds': load_images('clouds'),
            'game_over': load_image('GAME-OVER.png'),
            'you_win': load_image('YOU-WIN.png'),
            'enemy/idle': Animation(load_images('entities/enemy/idle'), img_dur=6),
            'enemy/run': Animation(load_images('entities/enemy/run'), img_dur=4),
            'player/idle': Animation(load_images('entities/player/idle'), img_dur=6),
            'player/run': Animation(load_images('entities/player/run'), img_dur=4),
            'player/jump': Animation(load_images('entities/player/jump')),
            'player/slide': Animation(load_images('entities/player/slide')),
            'player/wall_slide': Animation(load_images('entities/player/wall_slide')),
            'particles/leaf': Animation(load_images('particles/leaf'), img_dur=20, loop=False),
            'particles/particle': Animation(load_images('particles/particle'), img_dur=6, loop=False),
            'gun': load_image('gun.png'),
            'projectile': load_image('projectile.png'),
        }

        self.sfx = {
            'jump': pygame.mixer.Sound('data/sfx/jump.wav'),
            'dash': pygame.mixer.Sound('data/sfx/dash.wav'),
            'hit': pygame.mixer.Sound('data/sfx/hit.wav'),
            'shoot': pygame.mixer.Sound('data/sfx/shoot.wav'),
            'ambience': pygame.mixer.Sound('data/sfx/ambience.wav'),
        }

        self.sfx['ambience'].set_volume(0.2)
        self.sfx['shoot'].set_volume(0.4)
        self.sfx['hit'].set_volume(0.8)
        self.sfx['dash'].set_volume(0.3)
        self.sfx['jump'].set_volume(0.7)

        self.clouds = Clouds(self.assets['clouds'], count=16)

        self.player = Player(self, (50, 50), (8, 15))
        self.player.health = 3
        self.player.max_health = 3

        self.tilemap = Tilemap(self, tile_size=16)

        # Enhanced heart images
        self.heart_full, self.heart_empty = self._create_heart_images(size=14)

        self.level = 0
        self.load_level(self.level)

        self.screenshake = 0

    def _create_heart_images(self, size=14):
        """Create smoother, more stylized heart icons (full and empty)."""
        surf_full = pygame.Surface((size, size), pygame.SRCALPHA)
        surf_empty = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        radius = size // 4

        # --- Full Heart (shiny red) ---
        color = (230, 50, 50)
        highlight = (255, 120, 120)
        dark = (180, 0, 0)
        c1 = (center - radius // 1, center - radius // 2)
        c2 = (center + radius // 1, center - radius // 2)
        pygame.draw.circle(surf_full, color, c1, radius)
        pygame.draw.circle(surf_full, color, c2, radius)
        pygame.draw.polygon(surf_full, color, [
            (center - radius - 1, center - radius // 2),
            (center + radius + 1, center - radius // 2),
            (center, size - 1)
        ])
        # small highlight
        pygame.draw.circle(surf_full, highlight, (c1[0]-1, c1[1]-1), radius//3)
        pygame.draw.circle(surf_full, highlight, (c2[0]-1, c2[1]-1), radius//3)
        pygame.draw.polygon(surf_full, dark, [
            (center - radius - 1, center - radius // 2),
            (center + radius + 1, center - radius // 2),
            (center, size - 1)
        ], 1)

        # --- Empty Heart (gray outline) ---
        outline = (100, 100, 100)
        pygame.draw.circle(surf_empty, outline, c1, radius, 2)
        pygame.draw.circle(surf_empty, outline, c2, radius, 2)
        pygame.draw.polygon(surf_empty, outline, [
            (center - radius - 1, center - radius // 2),
            (center + radius + 1, center - radius // 2),
            (center, size - 1)
        ], 2)

        return surf_full, surf_empty

    def load_level(self, map_id):
        self.tilemap.load('data/maps/' + str(map_id) + '.json')

        self.leaf_spawners = []
        for tree in self.tilemap.extract([('large_decor', 2)], keep=True):
            self.leaf_spawners.append(pygame.Rect(4 + tree['pos'][0], 4 + tree['pos'][1], 23, 13))

        self.enemies = []
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1)]):
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
                self.player.air_time = 0
                self.player.health = self.player.max_health
            else:
                self.enemies.append(Enemy(self, spawner['pos'], (8, 15)))

        self.projectiles = []
        self.particles = []
        self.sparks = []

        self.scroll = [0, 0]
        self.dead = 0
        self.transition = -30

    def show_game_over(self):
        # Use image for header if available, keep a small restart text rendered
        # Create pixelated font for restart prompt
        font_large = pygame.font.Font(None, 48)
        restart_text_large = font_large.render('PRESS R TO RESTART', True, (255, 255, 255))
        restart_text = pygame.transform.scale(restart_text_large,
                                            (restart_text_large.get_width() // 2,
                                            restart_text_large.get_height() // 2))
        
        # Create shadow for pixelated effect
        shadow_large = font_large.render('PRESS R TO RESTART', True, (0, 0, 0))
        shadow_text = pygame.transform.scale(shadow_large,
                                            (shadow_large.get_width() // 2,
                                            shadow_large.get_height() // 2))
        
        try:
            game_over_img = self.assets.get('game_over') or load_image('GAME-OVER.png')
        except Exception:
            game_over_img = None
        waiting = True
        
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        waiting = False
                        self.load_level(self.level)

            overlay = pygame.Surface(self.display.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.display.fill((0, 0, 0, 0))
            self.display.blit(overlay, (0, 0))

            # blit image centered (if available) otherwise fall back to text
            if game_over_img:
                gw, gh = game_over_img.get_size()
                gx = self.display.get_width() // 2 - gw // 2
                gy = self.display.get_height() // 2 - gh // 2 - 16
                self.display.blit(game_over_img, (gx, gy))
            else:
                # fallback text centered
                font = pygame.font.Font(None, 72)
                game_over_text = font.render("GAME OVER", True, (255, 0, 0))
                self.display.blit(game_over_text,
                                (self.display.get_width() // 2 - game_over_text.get_width() // 2,
                                self.display.get_height() // 2 - 60))

            # Blinking restart prompt at top center with pixelated shadow
            visible = (pygame.time.get_ticks() // 500) % 2 == 0
            if visible:
                dw, dh = self.display.get_size()
                px = (dw - restart_text.get_width()) // 2
                py = 180
                # Draw shadow first
                self.display.blit(shadow_text, (px + 1, py + 1))
                # Draw main text
                self.display.blit(restart_text, (px, py))

            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
            pygame.display.update()
            self.clock.tick(60)
    
    def show_congratulations(self):
        # Use image for header if available, keep a small restart text rendered
        # Create pixelated font for restart prompt
        font_large = pygame.font.Font(None, 48)
        restart_text_large = font_large.render('PRESS R TO PLAY AGAIN', True, (255, 255, 255))
        restart_text = pygame.transform.scale(restart_text_large,
                                            (restart_text_large.get_width() // 2,
                                            restart_text_large.get_height() // 2))
        
        # Create shadow for pixelated effect
        shadow_large = font_large.render('PRESS R TO PLAY AGAIN', True, (0, 0, 0))
        shadow_text = pygame.transform.scale(shadow_large,
                                            (shadow_large.get_width() // 2,
                                            shadow_large.get_height() // 2))
        
        try:
            you_win_img = self.assets.get('you_win') or load_image('YOU-WIN.png')
        except Exception:
            you_win_img = None

        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        waiting = False
                        self.level = 0  # restart from first level
                        self.load_level(self.level)

            overlay = pygame.Surface(self.display.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.display.fill((0, 0, 0, 0))
            self.display.blit(overlay, (0, 0))

            # blit image centered (if available) otherwise fall back to text
            if you_win_img:
                iw, ih = you_win_img.get_size()
                ix = self.display.get_width() // 2 - iw // 2
                iy = self.display.get_height() // 2 - ih // 2 - 16
                self.display.blit(you_win_img, (ix, iy))
            else:
                font = pygame.font.Font(None, 40)
                congrats_text = font.render("CONGRATULATIONS!", True, (0, 255, 0))
                self.display.blit(congrats_text,
                                (self.display.get_width() // 2 - congrats_text.get_width() // 2,
                                self.display.get_height() // 2 - 60))

            # Blinking restart prompt at top center with pixelated shadow
            visible = (pygame.time.get_ticks() // 500) % 2 == 0
            if visible:
                dw, dh = self.display.get_size()
                px = (dw - restart_text.get_width()) // 2
                py = 150
                # Draw shadow first
                self.display.blit(shadow_text, (px + 1, py + 1))
                # Draw main text
                self.display.blit(restart_text, (px, py))

            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
            pygame.display.update()
            self.clock.tick(60)


    def show_title(self):
        """Display the title image (no text). Wait for any key or mouse press to continue."""
        try:
            # Load via existing helper so path resolves to data/images/title.jpg
            title_img = self.assets.get('title') or load_image('title-menu.png')
        except Exception:
            title_img = None

        # Prepare text for blinking prompt with pixel-art style
        # Use a larger font and scale down with nearest-neighbor for pixelated look
        font_large = pygame.font.Font(None, 48)
        prompt_text_large = font_large.render('PRESS ENTER', True, (255, 255, 255))
        # Scale down to create pixelated effect (nearest-neighbor)
        prompt_text = pygame.transform.scale(prompt_text_large, 
                                              (prompt_text_large.get_width() // 2, 
                                               prompt_text_large.get_height() // 2))

        # If title image exists, scale and center it, otherwise just show black
        if title_img:
            self.assets['title'] = title_img
            iw, ih = title_img.get_size()
            dw, dh = self.display.get_size()
            scale = min(dw / iw, dh / ih)
            new_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
            img_scaled = pygame.transform.smoothscale(title_img, new_size)
            img_x = (dw - new_size[0]) // 2
            img_y = (dh - new_size[1]) // 2
        else:
            img_scaled = None
            img_x = img_y = 0

        # Prepare player idle animation to render on the title screen (if available)
        idle_anim = None
        try:
            if isinstance(self.assets.get('player/idle'), Animation):
                idle_anim = self.assets.get('player/idle').copy()
            else:
                idle_anim = Animation(load_images('entities/player/idle'), img_dur=6)
        except Exception:
            idle_anim = None

        # Default player placement (centered on title image; you can adjust later)
        dw, dh = self.display.get_size()
        if img_scaled:
            player_center_x = img_x + (new_size[0] // 2)
            # place the player above the bottom of the title image
            player_center_y = img_y + new_size[1] - 127
        else:
            player_center_x = dw // 2
            player_center_y = dh // 2 + 40

        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                # Only proceed on Enter (ignore mouse clicks and other keys)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        # start title-enter animation (player jump) then exit title
                        play_jump = True
                        waiting = False

            # Clear
            self.display.fill((0, 0, 0))

            # Draw title image if available
            if img_scaled:
                self.display.blit(img_scaled, (img_x, img_y))

            # Update and draw player idle animation
            if idle_anim:
                idle_anim.update()
                try:
                    frame_img = idle_anim.img()
                    fx = player_center_x - frame_img.get_width() // 2
                    fy = player_center_y - frame_img.get_height() // 2
                    self.display.blit(frame_img, (fx, fy))
                except Exception:
                    # ignore rendering errors for safety
                    pass

            # Blinking prompt at top center with pixelated shadow
            visible = (pygame.time.get_ticks() // 500) % 2 == 0
            if visible:
                dw, dh = self.display.get_size()
                px = (dw - prompt_text.get_width()) // 2
                py = 30
                # Create shadow with pixelated effect
                shadow_large = font_large.render('PRESS ENTER', True, (0, 0, 0))
                shadow_text = pygame.transform.scale(shadow_large, 
                                                      (shadow_large.get_width() // 2, 
                                                       shadow_large.get_height() // 2))
                self.display.blit(shadow_text, (px + 1, py + 1))
                self.display.blit(prompt_text, (px, py))

            # present to the real screen
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
            pygame.display.update()
            self.clock.tick(60)

        # If Enter was pressed, play a short jump animation before returning
        if 'play_jump' in locals() and play_jump:
            # try to use the jump animation if available
            try:
                jump_anim = None
                if isinstance(self.assets.get('player/jump'), Animation):
                    jump_anim = self.assets.get('player/jump').copy()
                elif idle_anim:
                    jump_anim = idle_anim.copy()
                else:
                    jump_anim = Animation(load_images('entities/player/idle'), img_dur=6)
            except Exception:
                jump_anim = None

            # animation parameters
            total_frames = 30
            jump_height = 28

            # play sfx if available
            try:
                if 'jump' in self.sfx:
                    self.sfx['jump'].play()
            except Exception:
                pass

            for t in range(total_frames):
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

                # update animation frame
                if jump_anim:
                    jump_anim.update()
                    try:
                        frame_img = jump_anim.img()
                    except Exception:
                        frame_img = None
                else:
                    frame_img = None

                u = t / float(max(1, total_frames - 1))
                # simple arc: sin curve for smooth jump
                y_off = -int(math.sin(u * math.pi) * jump_height)

                # redraw background/title
                self.display.fill((0, 0, 0))
                if img_scaled:
                    self.display.blit(img_scaled, (img_x, img_y))

                # draw player frame at offset
                if frame_img:
                    fx = player_center_x - frame_img.get_width() // 2
                    fy = player_center_y - frame_img.get_height() // 2 + y_off
                    self.display.blit(frame_img, (fx, fy))

                # present
                self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
                pygame.display.update()
                self.clock.tick(60)

            # small delay after animation
            pygame.time.delay(120)

        # end of title screen; control returns to run()




    def _draw_hearts(self):
        """Draws the heart HUD with a soft gray background panel."""
        heart_w = self.heart_full.get_width()
        heart_h = self.heart_full.get_height()
        spacing = 6
        total_width = (heart_w + spacing) * self.player.max_health - spacing
        bg_rect = pygame.Rect(4, 4, total_width + 8, heart_h + 8)

        # Slightly transparent gray background
        bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surf.fill((40, 40, 40, 160))
        pygame.draw.rect(bg_surf, (80, 80, 80, 180), bg_surf.get_rect(), 1, border_radius=4)
        self.display.blit(bg_surf, (bg_rect.x, bg_rect.y))

        # Draw hearts on top
        x = bg_rect.x + 4
        y = bg_rect.y + 4
        for i in range(self.player.max_health):
            if i < self.player.health:
                self.display.blit(self.heart_full, (x + i * (heart_w + spacing), y))
            else:
                self.display.blit(self.heart_empty, (x + i * (heart_w + spacing), y))

    def run(self):
        # show title image on start (waits for key/mouse press)
        try:
            self.show_title()
        except Exception:
            # Fail silently if title cannot be shown
            pass

        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
        self.sfx['ambience'].play(-1)

        while True:
            self.display.fill((0, 0, 0, 0))
            self.display_2.blit(self.assets['background'], (0, 0))
            self.screenshake = max(0, self.screenshake - 1)

            if not len(self.enemies):
                self.transition += 1
                if self.transition > 30:
                    total_levels = len(os.listdir('data/maps'))
                    if self.level + 1 >= total_levels:
                        self.show_congratulations()  # All levels completed
                    else:
                        self.level += 1
                        self.load_level(self.level)

            if self.transition < 0:
                self.transition += 1

            if self.dead:
                self.dead += 1
                if self.dead >= 10:
                    self.transition = min(30, self.transition + 1)
                if self.dead > 10 and self.transition >= 30:
                    self.show_game_over()

            self.scroll[0] += (self.player.rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / 30
            self.scroll[1] += (self.player.rect().centery - self.display.get_height() / 2 - self.scroll[1]) / 30
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            for rect in self.leaf_spawners:
                if random.random() * 49999 < rect.width * rect.height:
                    pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                    self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))

            self.clouds.update()
            self.clouds.render(self.display, offset=render_scroll)
            self.tilemap.render(self.display, offset=render_scroll)

            for enemy in self.enemies.copy():
                kill = enemy.update(self.tilemap, (0, 0))
                enemy.render(self.display, offset=render_scroll)
                if kill:
                    self.enemies.remove(enemy)

            if not self.dead:
                self.player.update(self.tilemap, (self.movement[1] - self.movement[0], 0))
                self.player.render(self.display, offset=render_scroll)

            for projectile in self.projectiles.copy():
                projectile[0][0] += projectile[1]
                projectile[2] += 1
                img = self.assets['projectile']
                self.display.blit(img, (
                    projectile[0][0] - img.get_width() / 2 - render_scroll[0],
                    projectile[0][1] - img.get_height() / 2 - render_scroll[1]
                ))
                if self.tilemap.solid_check(projectile[0]):
                    self.projectiles.remove(projectile)
                    for _ in range(4):
                        self.sparks.append(Spark(projectile[0], random.random() - 0.5 +
                                                 (math.pi if projectile[1] > 0 else 0), 2 + random.random()))
                elif projectile[2] > 360:
                    self.projectiles.remove(projectile)
                elif abs(self.player.dashing) < 50:
                    if self.player.rect().collidepoint(projectile[0]):
                        self.projectiles.remove(projectile)
                        self.player.health = max(0, getattr(self.player, 'health', 1) - 1)
                        self.sfx['hit'].play()
                        self.screenshake = max(16, self.screenshake)
                        for _ in range(30):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 5
                            self.sparks.append(Spark(self.player.rect().center, angle, 2 + random.random()))
                            self.particles.append(
                                Particle(self, 'particle', self.player.rect().center,
                                         velocity=[math.cos(angle + math.pi) * speed * 0.5,
                                                   math.sin(angle + math.pi) * speed * 0.5],
                                         frame=random.randint(0, 7))
                            )
                        if self.player.health <= 0:
                            self.dead += 1

            for spark in self.sparks.copy():
                kill = spark.update()
                spark.render(self.display, offset=render_scroll)
                if kill:
                    self.sparks.remove(spark)

            display_mask = pygame.mask.from_surface(self.display)
            display_silhouette = display_mask.to_surface(setcolor=(0, 0, 0, 180),
                                                         unsetcolor=(0, 0, 0, 0))
            for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                self.display_2.blit(display_silhouette, offset)

            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display, offset=render_scroll)
                if particle.type == 'leaf':
                    particle.pos[0] += math.sin(particle.animation.frame * 0.035) * 0.3
                if kill:
                    self.particles.remove(particle)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:
                        self.movement[0] = True
                    if event.key == pygame.K_d:
                        self.movement[1] = True
                    if event.key == pygame.K_SPACE:
                        if self.player.jump():
                            self.sfx['jump'].play()
                    if event.key == pygame.K_l:
                        self.player.dash()

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_a:
                        self.movement[0] = False
                    if event.key == pygame.K_d:
                        self.movement[1] = False

            if self.transition:
                transition_surf = pygame.Surface(self.display.get_size())
                pygame.draw.circle(transition_surf, (255, 255, 255),
                                   (self.display.get_width() // 2, self.display.get_height() // 2),
                                   (30 - abs(self.transition)) * 8)
                transition_surf.set_colorkey((255, 255, 255))
                self.display.blit(transition_surf, (0, 0))

            # Draw hearts with background
            self._draw_hearts()

            self.display_2.blit(self.display, (0, 0))
            screenshake_offset = (
                random.random() * self.screenshake - self.screenshake / 2,
                random.random() * self.screenshake - self.screenshake / 2
            )
            self.screen.blit(pygame.transform.scale(self.display_2, self.screen.get_size()), screenshake_offset)
            pygame.display.update()
            self.clock.tick(60)


Game().run()
