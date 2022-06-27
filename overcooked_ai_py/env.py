import gym
from gym import spaces

import cv2
import pygame
import copy
import numpy as np

from overcooked_ai_py.mdp.overcooked_env import OvercookedEnv as OriginalEnv
from overcooked_ai_py.mdp.overcooked_mdp import OvercookedGridworld
from overcooked_ai_py.visualization.state_visualizer import StateVisualizer
from overcooked_ai_py.mdp.actions import Action

import time

class time_measure():
    def __init__(self):
        self.s = 0
        self.e = 0
    
    def start(self):
        self.s = time.time()
        return 0
    
    def end(self):
        self.e = time.time() - self.s
        return self.e
    
    def check_time_over(self, target_time=300):
        r = False
        if target_time <= time.time() - self.s:
            r = True
        return r
    
    def time_passed(self):
        return time.time() - self.s

def _convert_action(joint_action) -> list:
    action_set = []
    for _action in joint_action:
        action_set.append(Action.INDEX_TO_ACTION[int(_action)])

    return action_set


class OverCookedEnv():
    
    def __init__(self,
                 scenario="tutorial_0",
                 episode_length=-1,
                 time_limit = 300
                 ):
        super(OverCookedEnv, self).__init__()
    
        self.scenario = scenario
        self.episode_length = episode_length

        base_mdp = OvercookedGridworld.from_layout_name(scenario)
        self.overcooked = OriginalEnv.from_mdp(base_mdp, horizon=episode_length)
        self.visualizer = StateVisualizer()

        self.t = time_measure()
        self.time_limit = time_limit
        self.score = 0

        self._available_actions = Action.ALL_ACTIONS

    def reset(self):
        self.overcooked.reset()
        self.t.end()
        self.t.start()
        return None
        return self._get_observation()

    def render(self, mode='rgb_array'):
        t = self.time_limit - self.t.time_passed()
        image = self.visualizer.render_state(state=self.overcooked.state, grid=self.overcooked.mdp.terrain_mtx,
                                             hud_data=StateVisualizer.default_hud_data(self.overcooked.state, time_left = t, score = self.score))

        buffer = pygame.surfarray.array3d(image)
        image = copy.deepcopy(buffer)
        image = np.flip(np.rot90(image, 3), 1)

        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        image = cv2.resize(image, (528, 464))

        return image

    def step(self, action):
        action = _convert_action(action)

        next_state, reward, done, info = self.overcooked.step(action)
        
        self.score += reward
        return next_state, reward, done, info

    def _get_observation(self):
        return self.get_feature_state().reshape(len(self.agents), -1)

    def get_onehot_state(self):
        return np.array(self.overcooked.lossless_state_encoding_mdp(self.overcooked.state))

    def get_feature_state(self):
        return np.array(self.overcooked.featurize_state_mdp(self.overcooked.state))


    @property
    def agents(self) -> [str]:
        num_agents = len(self.overcooked.lossless_state_encoding_mdp(self.overcooked.state))
        return ['ally' for _ in range(num_agents)]

    @property
    def observation_space(self):
        state = self.get_feature_state()[0]
        state = np.array(state)
        # return spaces.Discrete(4056)
        return spaces.Discrete(state.shape[0])

    @property
    def action_space(self):
        return spaces.Discrete(Action.NUM_ACTIONS)
