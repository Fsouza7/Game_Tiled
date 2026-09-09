import pygame
import os

import setup
from settings import *

pygame.init()

pygame.display.set_caption("Platformer")

# Defina a pasta do menu
menu_folder = "./assets/menu/Buttons/Menu_jogo"
menu_path = os.path.join(os.getcwd(), menu_folder)
resized_button_images = []



def draw_menu(window,resized_button_images, menu_offset):
    # Desenha os botões do menu
    button_width = 20  # Largura original do botão
    button_height = 200  # Altura original do botão
    button_spacing = 30  # Espaçamento entre os botões
    total_width = len(resized_button_images) * (button_width + button_spacing) - button_spacing
    start_x = (WIDTH - total_width) // 2
    y = (HEIGHT - button_height) // 1.5
    menu_y = 100 + menu_offset  # Altere o valor 100 para ajustar a posição vertical inicial do menu


    for index, image in enumerate(resized_button_images):
        button_rect = image.get_rect()
        button_rect.topleft = (start_x, y)
        window.blit(image, button_rect)
        button_info = {
            'index': index,
            'rect': button_rect
        }
        button_infos.append(button_info)
        start_x += button_width + button_spacing

    pygame.display.update()

def handle_menu_click(w,button_infos, click_pos):
    for button_info in button_infos:
        if button_info['rect'].collidepoint(click_pos):
            button_index = button_info['index']
            print("Botão", button_index, "clicado")
            if button_index == 4:
                print("Botão", button_index, "clicado")
                show_menu = w(window)
                if show_menu:
                    # Reiniciar o loop principal
                    continue

            return


