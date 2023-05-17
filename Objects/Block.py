from Importations import *
from Objects.Object import Object


class Block(Object):
    def __init__(self, x, y, size):
        from setup import get_block
        super().__init__(x, y, size, size)
        block = get_block(size)
        self.image.blit(block, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)

