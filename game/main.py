"""Entry point: python -m game.main"""
import logging

from game.core.game_app import GameApp


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = GameApp()
    app.run()


if __name__ == "__main__":
    main()
