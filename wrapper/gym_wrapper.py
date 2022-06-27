import pygame as pg
import numpy as np
import threading
import cv2 as cv
import time

from overcooked_ai_py.env import OverCookedEnv


class GymWrapper:
    def __init__(self):
        self.level = None
        self.duration = None

        self._rendered_image = None
        self._remote_action = None
        self._black_screen = np.zeros((600, 800, 3), dtype=np.uint8)

        self._reset_image()
        self._init_gui()
        self.start_game()

        self._start_time = None
        self.env = None

    def _init_gui(self):
        pg.display.set_caption('Player 1')
        self.screen = pg.display.set_mode((800, 600))

        self._run = True
        self.thr_game = threading.Thread(target=self._loop, args=(self, ))
        self.thr_game.start()


    def _reset_image(self):
        self._rendered_image = self._black_screen

    def set_level(self, level: str) -> None:
        self.level = level

    def set_duration(self, duration: int) -> None:
        self.duration = duration

    def remote_action(self, action: int):
        self._remote_action = action

    def on_key_pressed(self, key: int) -> None:
        self._key_id = key
        self._timestamp_key_pressed = time.time()


    def get_key(self):
        if hasattr(self, '_timestamp_key_pressed') and (time.time() - self._timestamp_key_pressed <= 0.01):
            return self._key_id
        else:
            return None

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
        try:
            self.env = OverCookedEnv(scenario=self.level, time_limit=self.duration)
            self.env.reset()
            self._start_time = time.time()
        except:
            pass

    def abort_game(self):
        del self.env
        self._reset_image()

    def _loop(self, parent_instance):

        while parent_instance._run:
            action = [4, 4]

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    parent_instance._on_close()

                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_UP:  # up
                        action[0] = 0
                    if event.key == pg.K_DOWN:  # down
                        action[0] = 1
                    if event.key == pg.K_LEFT:  # left
                        action[0] = 3
                    if event.key == pg.K_RIGHT:  # right
                        action[0] = 2
                    if event.key == pg.K_RSHIFT:  # pickup
                        action[0] = 5

            if hasattr(self, 'env') and self.env is not None:
                if self._remote_action != None:
                    action[1] = self._remote_action
                    self._remote_action = None

                self.env.step(action=action)
                image = self.env.render()
                image = cv.resize(image, (800, 600))

                self.screen.blit(pg.surfarray.make_surface(np.rot90(np.flip(image[..., ::-1], 1))), (0, 0))
                pg.display.flip()

                parent_instance._rendered_image = image

                if time.time() - self._start_time > self.duration:
                    self.abort_game()

            else:
                self.screen.blit(pg.surfarray.make_surface(np.rot90(self._black_screen)), (0, 0))
                pg.display.flip()

                parent_instance._rendered_image = self._black_screen

    def render(self):
        return self._rendered_image
