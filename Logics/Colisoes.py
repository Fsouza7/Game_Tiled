
from settings import *
clock = pygame.time.Clock()



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


def handle_move(w, player, objects):
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
            player.death(w)

        if obj and obj.name == "fan":
            player.make_hit()
            player.death(w)

        if obj and obj.name == "death":
            print("GAME OVER")
            player.death(w)

        if obj and obj.name == "saw":
            player.death(w)





