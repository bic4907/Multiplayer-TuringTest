import random


class RandomAgent:
    def __init__(self):
        pass

    def get_action(self, obs):
        return random.randint(0, 5)
