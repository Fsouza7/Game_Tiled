import pygame

from Importations import *
from Objects import Player,Block,Object,Fire,Fan,Fruits
from settings import *
from Logics.Colisoes import *

offset_x = 0
scroll_area_width = 800

pygame.init()

pygame.display.set_caption("Platformer")

def draw(window, background, bg_image, player, objects, offset_x):
    for tile in background:
        window.blit(bg_image, tile)

    for obj in objects:
        obj.draw(window, offset_x)

    player.draw(window, offset_x)

    pygame.display.update()

def get_background(name):
    image = pygame.image.load(join("assets", "Background", name))
    _, _, width, height = image.get_rect()
    tiles = []

    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            pos = (i * width, j * height)
            tiles.append(pos)

    return tiles, image

def main(window):
    global player, fire
    global offset_x
    clock = pygame.time.Clock()
    background, bg_image = get_background("Yellow.png")

    block_size = 66

    for row_index, row in enumerate(level_map):
        for col_index, cell in enumerate(row):
            x = col_index * block_size
            y = row_index * block_size

            if cell == "x":
                block = Block.Block(x, y, block_size,"terra")
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
            elif cell == "l":
                block = Block.Block(x, y, block_size, "decor")
                objects.append(block)

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