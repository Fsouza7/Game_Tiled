import pygame
from Importations import *
level_map= [
',,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,m,,,,,,,,,,,,,,,,,,,',
',,,,,,,,,,,,,f,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,xx,,,,,,,,,,,,,,,,,',
',,,,,,,,,,,,xxx,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,',
',,,,,,,,,,,,,,,,,,,,,,,,,,,xxx,,,,,,,,,,,,,,,,,,,m,,,,xxxxx,mmmmm,,,,,xxx,,,,,,,,,,',
',,,,,,,,,,,,,,,f,,,,,,,,,,,,,,,,,,,,,,m,,xx,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,',
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
PLAYER_VEL = 9
objects=[]
window = pygame.display.set_mode((WIDTH, HEIGHT))
apples=[]
fires = []
button_infos = []
menu_folder = "./assets/menu/Buttons/Menu_jogo"
menu_path = os.path.join(os.getcwd(), menu_folder)

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

def load_button_images():
    button_images = []
    resized_button_images = []  # Lista para armazenar as imagens redimensionadas

    for file_name in os.listdir(menu_path):
        if file_name.endswith(".png"):
            file_path = os.path.join(menu_path, file_name)
            image = pygame.image.load(file_path).convert_alpha()
            button_images.append(image)

            resized_image = pygame.transform.scale2x(image)  # Aumenta o tamanho do botão em 2x
            resized_button_images.append(resized_image)

    return resized_button_images