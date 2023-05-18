import pygame

from Importations import *
from Objects import Player,Block,Object,Fire,Fan,Fruits
from settings import level_map

pygame.init()

pygame.display.set_caption("Platformer")

WIDTH, HEIGHT = 1400, 800
FPS = 60
PLAYER_VEL = 6
objects=[]
window = pygame.display.set_mode((WIDTH, HEIGHT))
apples=[]
fires = []

def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def draw(window, background, bg_image, player, objects, offset_x):
    for tile in background:
        window.blit(bg_image, tile)

    for obj in objects:
        obj.draw(window, offset_x)

    player.draw(window, offset_x)

    pygame.display.update()


def handle_vertical_collision(player, objects, dy):
    collided_objects = []
    for obj in objects:
        if pygame.sprite.collide_rect(player, obj):
            if dy > 0:
                if obj.name == "apple":
                    # Ignora a colisão com a maçã
                    continue
                player.rect.bottom = obj.rect.top
                player.landed()
            elif dy < 0:
                if obj.name == "apple":
                    # Ignora a colisão com a maçã
                    continue
                player.rect.top = obj.rect.bottom
                player.hit_head()

            collided_objects.append(obj)

    return collided_objects


def collide(player, objects, dx):
    player.move(dx, 0)
    player.update()
    collided_object = None
    for obj in objects:
        if pygame.sprite.collide_rect(player, obj):
            if obj.name == "apple":
                # Ignora a colisão com a maçã
                continue
            collided_object = obj
            break

    player.move(-dx, 0)
    player.update()
    return collided_object


def handle_move(player, objects):
    keys = pygame.key.get_pressed()

    player.x_vel = 0
    collide_left = collide(player, objects, -PLAYER_VEL * 2)
    collide_right = collide(player, objects, PLAYER_VEL * 2)
    vertical_collide = handle_vertical_collision(player, objects, player.y_vel)
    to_check = [collide_left, collide_right, *vertical_collide]

    if keys[pygame.K_a] and not collide_left:
        player.move_left(PLAYER_VEL)
    if keys[pygame.K_d] and not collide_right:
        player.move_right(PLAYER_VEL)

    for obj in to_check:
        if obj and obj.name == "fire":
            player.make_hit()
        if obj and obj.name == "fan":
            player.make_hit()


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


def get_background(name):
    image = pygame.image.load(join("assets", "Background", name))
    _, _, width, height = image.get_rect()
    tiles = []

    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            pos = (i * width, j * height)
            tiles.append(pos)

    return tiles, image


def get_block(size):
    path = join("assets", "Terrain", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    rect = pygame.Rect(96, 0, size, size)
    surface.blit(image, (0, 0), rect)
    return pygame.transform.scale2x(surface)


def main(window):
    global player, fire
    clock = pygame.time.Clock()
    background, bg_image = get_background("Blue.png")

    block_size = 66

    for row_index, row in enumerate(level_map):
        for col_index, cell in enumerate(row):
            x = col_index * block_size
            y = row_index * block_size

            if cell == "x":
                block = Block.Block(x, y, block_size)
                objects.append(block)
            elif cell == "p":
                player = Player.Player(x, y, 50, 50)
            elif cell == "m":
                apple = Fruits.Apple(x, y, 32,32)
                objects.append(apple)
                apples.append(apple)
            elif cell == "f":
                fire = Fire.Fire(x,y, 16,32)
                objects.append(fire)
                fires.append(fire)


    offset_x = 0
    scroll_area_width = 200

    run = True
    while run:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and player.jump_count < 2:
                    player.jump()

        keys = pygame.key.get_pressed()

        player.loop(FPS,apples)
        for aple in apples:
            aple.loop()
        for fir in fires:
            fir.on()
            fir.loop()
        handle_move(player, objects)

        draw(window, background, bg_image, player, objects, offset_x)
        Fruits.Apple.eat(apples,player,objects)

        if ((player.rect.right - offset_x >= WIDTH - scroll_area_width) and player.x_vel > 0) or (
                (player.rect.left - offset_x <= scroll_area_width) and player.x_vel < 0):
            offset_x += player.x_vel

    pygame.quit()
    quit()


if __name__ == "__main__":
    main(window)