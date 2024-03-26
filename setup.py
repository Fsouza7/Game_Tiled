import pygame
import os
from Importations import *
from Objects import Player, Block, Object, Fire, Fan, Fruits, Void,Saw
from settings import *
from Logics.Colisoes import *
from Logics.Menu import *


offset_x = 300
scroll_area_width = 800

pygame.init()
pygame.display.set_caption("Platformer")


def draw(window, background, bg_image, player, objects, offset_x):
    for tile in background:
        window.blit(bg_image, tile)

    for obj in objects:
        obj.draw(window, offset_x)

    player.draw(window, offset_x)

    # Colocar imagem no canto inferior
    if player.count_fruits > 10:
       pass
    level_image = pygame.image.load(join("assets/Menu/Levels", f"1.png"))
    level_rect = level_image.get_rect()
    level_rect.bottomright = (WIDTH, 25)
    window.blit(level_image, level_rect)

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
    background, bg_image = get_background("Pink.png")
    resized_button_images = load_button_images()
    offset_x = 300
    block_size = 66
    apples.clear()
    fires.clear()
    objects.clear()
    fans.clear()
    for row_index, row in enumerate(level_map):
        for col_index, cell in enumerate(row):
            x = col_index * block_size
            y = row_index * block_size

            if cell == "x":
                block = Block.Block(x, y, block_size, "terra")
                objects.append(block)

            elif cell == "p":
                player = Player.Player(x, y, 50, 50)

            elif cell == "m":
                apple = Fruits.Apple(x, y, 32, 32)
                objects.append(apple)
                apples.append(apple)

            elif cell == "f":
                fire = Fire.Fire(x, y, 16, 32)
                objects.append(fire)
                fires.append(fire)

            elif cell == "l":
                block = Block.Block(x, y, block_size, "decor")
                objects.append(block)

            elif cell == "v":
                fan = Fan.Fan(x, y, 24, 8)
                objects.append(fan)
                fans.append(fan)

            elif cell == "d":
                death = Void.Void(x,y,38,42)
                objects.append(death)

            elif cell == "s":
                serra = Saw.Saw(x, y, 38, 42)
                objects.append(serra)
                serras.append(serra)

    run = True
    show_menu = False
    is_paused = False
    menu_offset = 0
    menu_clock = pygame.time.Clock()

    while run:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    show_menu = not show_menu
                    is_paused = not is_paused  # Inverter o estado de pausa
                elif event.key == pygame.K_SPACE and player.jump_count < 2:
                    player.jump()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clique do botão esquerdo do mouse
                    click_pos = pygame.mouse.get_pos()
                    handle_menu_click(main, button_infos, click_pos)

        keys = pygame.key.get_pressed()

        if not is_paused:  # Executar lógica do jogo apenas se não estiver pausado
            player.loop(FPS, apples)
            for aple in apples:
                aple.loop()
            for fir in fires:
                fir.on()
                fir.loop()
            for fan in fans:
                fan.on()
                fan.loop()
            for serra in serras:
                serra.on()
                serra.loop()


            handle_move(main, player, objects)

            if ((player.rect.right - offset_x >= WIDTH - scroll_area_width) and player.x_vel > 0) or (
                    (player.rect.left - offset_x <= scroll_area_width) and player.x_vel < 0):
                offset_x += player.x_vel

        draw(window, background, bg_image, player, objects, offset_x)
        Fruits.Apple.eat(apples, player, objects)
        menu_clock.tick()
        if show_menu and is_paused:  # Exibir o menu somente quando estiver pausado
            menu_offset += 1
            clock.tick(60)
            draw_menu(window, resized_button_images,menu_offset)
        pygame.display.flip()

    pygame.quit()
    quit()
    return show_menu

if __name__ == "__main__":
    window = pygame.display.set_mode((WIDTH, HEIGHT))
    main(window)
