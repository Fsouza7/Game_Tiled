from Importations import *

from Objects.Object import Object


class Void(Object):
    ANIMATION_DELAY = 2

    def __init__(self, x, y, width, height):
        from setup import load_sprite_sheets
        super().__init__(x, y, width, height, "death")

        # self.image = self.void["on"][0]
        self.mask = pygame.mask.from_surface(self.image)
        self.animation_count = 3
        self.animation_name = "off"

    def on(self):
        self.animation_name = "on"

    def off(self):
        self.animation_name = "off"

    # def loop(self):
    #     sprites = self.void[self.animation_name]
    #     sprite_index = (self.animation_count //
    #                     self.ANIMATION_DELAY) % len(sprites)
    #     self.image = sprites[sprite_index]
    #     self.animation_count += 1
    #
    #     self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
    #     self.mask = pygame.mask.from_surface(self.image)
    #
    #     if self.animation_count // self.ANIMATION_DELAY > len(sprites):
    #         self.animation_count = 0