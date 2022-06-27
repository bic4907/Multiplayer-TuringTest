import os

import pygame
import pygame as pg
import numpy as np
import threading


class DummyWrapper:
    def __init__(self):
        self.level = None
        self.duration = None

        self._rendered_image = None

        self._on_action_event = None
        self._on_close_event = None

        self._reset_image()
        self._init_gui()
        self.start_game()

    def _init_gui(self):
        pg.display.set_caption('Player 2')
        self.screen = pg.display.set_mode((800, 600))

        self._run = True
        self.thr_game = threading.Thread(target=self._loop, args=(self, ))
        self.thr_game.start()


    def set_image(self, image):
        self._rendered_image = image

    def _reset_image(self):
        self._rendered_image = np.zeros((600, 800, 3), dtype=np.uint8)

    def on_action(self, callback):
        self._on_action_event = callback

    def _on_player_action(self, action: int) -> None:
        if self._on_action_event is not None:
            self._on_action_event(action)

    def on_close(self, callback):
        self._on_close_event = callback

    def _on_close(self) -> None:
        if self._on_close_event is not None:
            self._on_close_event()
        self.stop()

    def stop(self):
        self._run = False
        pg.quit()

    def load_state(self) -> None:
        pass

    def start_game(self):
        self._run = True

        t1 = threading.Thread(target=self._loop, args=(self, ))
        t1.start()

    def _loop(self, parent_instance):

        while parent_instance._run:

            action = 4

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    parent_instance._on_close()

                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_UP:  # up
                        action = 0
                    elif event.key == pg.K_DOWN:  # down
                        action = 1
                    elif event.key == pg.K_LEFT:  # left
                        action = 3
                    elif event.key == pg.K_RIGHT:  # right
                        action = 2
                    elif event.key == pg.K_RSHIFT:  # pickup
                        action = 5

            if action != 4:
                parent_instance._on_player_action(action)

            image = parent_instance._rendered_image
            self.screen.blit(pg.surfarray.make_surface(np.rot90(np.flip(image[..., ::-1], 1))), (0, 0))
            pg.display.flip()

    def render(self):
        return self._rendered_image


