from Importations import *
import time
from setup import load_sprite_sheets
from settings import *

class Player(pygame.sprite.Sprite):

    COLOR = (255, 0, 0)
    GRAVITY = 1

    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):

        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)

        self.x_vel = 0
        self.y_vel = 0
        self.mask = None
        self.direction = "left"
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.count_fruits = 1
        self.iniciar = False
        if self.iniciar == 0:
            self.SPRITES = load_sprite_sheets("MainCharacters", "PinkMan", 96, 96, True)

    def jump(self):
        self.y_vel = -self.GRAVITY * 8
        self.animation_count = 0
        self.jump_count += 1
        if self.jump_count == 1:
            self.fall_count = 0

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def make_hit(self):
        self.hit = True

    def death(self,w):
        death = + 1
        print(f"voce morreu {death} vez")
        level_image = pygame.image.load(join("assets/Menu/Text", f"game over.png"))
        level_rect = level_image.get_rect()
        level_rect.bottomright = (750, 300)
        window.blit(level_image, level_rect)
        pygame.display.update()
        pygame.time.wait(300)
        w(window)

    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    def eat_apple(self, apple):
        if pygame.sprite.collide_rect(self, apple):
                self.count_fruits += 1
                print(self.count_fruits)

    def eat_fruits(self):
        self.count_fruits += 1
        self.eat_fruit = True

        return self.count_fruits


    def loop(self, fps,apples):
        self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
        if self.iniciar == True:
            self.move(self.x_vel, self.y_vel)

        self.eat_fruit = False
        for apple in apples:
            if self.eat_apple(apple):
                self.eat_fruits()
                break

        if self.hit:
            self.hit_count += 1
        if self.hit_count > fps * 2:
            self.hit = False
            self.hit_count = 0

        self.fall_count += 1
        self.update_sprite()

    def landed(self):
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0

    def hit_head(self):
        self.count = 0
        self.y_vel *= -1

    def update_sprite(self):
        if self.iniciar == False:
            sprite_sheet = 'Appearing (96x96)'

            if self.animation_count == 30:
                self.iniciar = True

        else:
            sprite_sheet = "idle"
            self.SPRITES = load_sprite_sheets("MainCharacters", "PinkMan", 32, 32, True)
            if self.hit:
                sprite_sheet = "hit"
            elif self.y_vel < 0:
                if self.jump_count == 1:
                    sprite_sheet = "jump"
                elif self.jump_count == 2:
                    sprite_sheet = "double_jump"
            elif self.y_vel > self.GRAVITY * 2:
                sprite_sheet = "fall"
            elif self.x_vel != 0:
                sprite_sheet = "run"



        sprite_sheet_name = sprite_sheet + "_" + self.direction
        sprites = self.SPRITES[sprite_sheet_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[sprite_index]
        self.animation_count += 1
        self.update()

    def update(self):
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win, offset_x):
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))