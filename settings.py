import pygame
from Importations import *
level_map= [
',,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,m,,,,,,,,,,,,,,,,,,,',
',,,,,,,,,,,,,f,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,xx,,,,,,,,,,,,,,,,,',
',,,,,,,,,,,,xxx,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,',
',,,,,,,,,,,,,,,,,,,,,,,,,,,,f,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,mf,,,,,,,,,,,',
',,,,,,,,,,,,,,,,,,,,,,,,,,,xxx,,,,,,,,,,,,,,,,,,,m,,,,xxxxx,mmmmm,,,,,xxx,,,,,,,,,,',
',,,,,,,,,,,,,,,f,,,,,,,,,,,,,,,,,,,,,,m,,xx,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,',
',,,,,,,,,,,,,xxxxx,,,,,,xx,,,,,,,,,,,,,,,,,,,,,,,,x,,,,,,,,,,,,,,,,lll,,,,,,,,,,,,,',
',,,,,,,,,,,,,,,,,,,,,mmmmmmmm,,,x,,,,xx,,,,,,ll,,,,,mmmmmm,,,ll,,,,,,,,,,,,,,,,,,,,',
',,,,,,,llll,,,,,p,,,,,,,,,,,,,,,,,,,,l,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,',
',,,,,,,,mmmmmmmmmmmmmmmmmmmm,,,,f,,,,,,ll,,,,,,,,f,,,,,,,mmmmmmmmmm,,,,f,,,,,,,,,,,',
',,,,xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx,,,,,,,,,,,xxxxxxxxxxxxxxxxxxxxxxxxxxxx,,,,,,,,,',
'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx,,,,,,,,xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
]


WIDTH, HEIGHT = 1400, 800
FPS = 60
PLAYER_VEL = 6
objects=[]
window = pygame.display.set_mode((WIDTH, HEIGHT))
apples=[]
fires = []



def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, width, height, direction=False):
    path = join("assets", dir1, dir2)
    images = [f for f in listdir(path) if isfile(join(path, f))]

    all_sprites = {}

    for image in images:
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()

        sprites = []
        for i in range(sprite_sheet.get_width() // width):
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            rect = pygame.Rect(i * width, 0, width, height)
            surface.blit(sprite_sheet, (0, 0), rect)
            sprites.append(pygame.transform.scale2x(surface))

        if direction:
            all_sprites[image.replace(".png", "") + "_right"] = sprites
            all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
        else:
            all_sprites[image.replace(".png", "")] = sprites

    return all_sprites