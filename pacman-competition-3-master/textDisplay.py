# textDisplay.py
# --------------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
# 
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).


import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from capture import GameState

try: 
    import pacman
except:
    pass

DRAW_EVERY = 1
SLEEP_TIME = 0 # This can be overwritten by __init__
DISPLAY_MOVES = False
QUIET = False # Supresses output

class NullGraphics:
    def initialize(self, state: 'GameState', isBlue: bool = False) -> None:
        pass

    def update(self, state: 'GameState') -> None:
        pass

    def checkNullDisplay(self) -> bool:
        return True

    def pause(self) -> None:
        time.sleep(SLEEP_TIME)

    def draw(self, state: 'GameState') -> None:
        print(state)

    def updateDistributions(self, dist) -> None:
        pass

    def finish(self) -> None:
        pass


class NoGraphics(NullGraphics):
    def draw(self, state: 'GameState') -> None:
        pass

class PacmanGraphics:
    def __init__(self, speed: int | None = None):
        if speed != None:
            global SLEEP_TIME
            SLEEP_TIME = speed

    def initialize(self, state: 'GameState', isBlue: bool = False) -> None:
        self.draw(state)
        self.pause()
        self.turn = 0
        self.agentCounter = 0

    def update(self, state: 'GameState') -> None:
        numAgents = len(state.agentStates)
        self.agentCounter = (self.agentCounter + 1) % numAgents
        if self.agentCounter == 0:
            self.turn += 1
            if DISPLAY_MOVES:
                ghosts = [pacman.nearestPoint(state.getGhostPosition(i)) for i in range(1, numAgents)]
                print("%4d) P: %-8s" % self.turn, str(pacman.nearestPoint(state.getPacmanPosition())),'| Score: %-5d' % state.score,'| Ghosts:', ghosts)
            if self.turn % DRAW_EVERY == 0:
                self.draw(state)
                self.pause()
        if state._win or state._lose:
            self.draw(state)

    def pause(self) -> None:
        time.sleep(SLEEP_TIME)

    def draw(self, state: 'GameState') -> None:
        print(state)

    def finish(self) -> None:
        pass

Graphics = NullGraphics | NoGraphics | PacmanGraphics