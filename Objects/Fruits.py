from Importations import *

from Objects.Object import Object


class Apple(Object):
    ANIMATION_DELAY = 5

    def __init__(self, x, y, width, height):
        from setup import load_sprite_sheets
        super().__init__(x, y, width, height, "apple")
        self.apple = load_sprite_sheets("Items", "Fruits/Apple", width, height)
        self.image = self.apple["Apple"][0]
        self.mask = pygame.mask.from_surface(self.image)
        self.animation_count = 3
        self.animation_name = "Apple"
        self.eaten = False

    def loop(self):
        if self.eaten:
            return

        sprites = self.apple[self.animation_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)

        if self.animation_count // self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0


    @staticmethod
    def eat(apples,player,objects):
        for apple in apples:
            if pygame.sprite.collide_rect(apple, player):
                apples.remove(apple)
                objects.remove(apple)
