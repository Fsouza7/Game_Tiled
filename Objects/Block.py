from Importations import *
from Objects.Object import Object


class Block(Object):
    def __init__(self, x, y, size,nome):

        super().__init__(x, y, size, size)
        block = Block.get_block(size,nome)
        self.image.blit(block, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)


    @staticmethod
    def get_block(size,nome):
        path = join("assets", "Terrain", "Terrain.png")
        if nome == "terra":
            rect_terra = pygame.Rect(96, 0, size, size)
            image = pygame.image.load(path).convert_alpha()
            surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
            surface.blit(image, (0, 0), rect_terra)
        elif nome == "decor":
            rect_decor = pygame.Rect(0, 0, size, size)
            image = pygame.image.load(path).convert_alpha()
            surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
            surface.blit(image, (0, 0), rect_decor)

        return pygame.transform.scale2x(surface)



