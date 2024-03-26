from Importations import *

class HealthBar():
    def __int__(self, x, y, w, h, max_hp):
        self.x = x
        self.y = y
        self.w = w
        self.hp = max_hp
        self.max_hp = max_hp

    def draw(self, surface):
        #calcula tamanho da vida
        ratio= self.hp / self.max_hp
        pygame.draw.rect(surface, "red", (self.x, self.y, self.w, self.h))
        pygame.draw.rect(surface, "green"(self.x, self.y, self.w * ratio, self.h))

health_bar = HealthBar(250, 200, 300, 40, 100)
run = True