# myTeam.py
# ---------
# Licensing Information: You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.

import random
import time
import traceback
from captureAgents import CaptureAgent
from game import Directions
from util import nearestPoint


def createTeam(firstIndex, secondIndex, isRed,
               first='SmartOffense', second='SmartDefense', **kwargs):
    classes = {'SmartOffense': SmartOffense, 'SmartDefense': SmartDefense}
    return [classes[first](firstIndex), classes[second](secondIndex)]


class TeamAgent(CaptureAgent):
    def registerInitialState(self, gameState):
        CaptureAgent.registerInitialState(self, gameState)
        self.start = gameState.getAgentPosition(self.index)
        self.previous_position = None
        walls = gameState.getWalls()
        mid = walls.width // 2
        home_x = mid - 1 if self.red else mid
        self.border = [(home_x, y) for y in range(walls.height)
                       if not walls[home_x][y]]
        self.patrol = self.border[len(self.border) // 2] if self.border else self.start

    def chooseAction(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP
        started = time.perf_counter()
        try:
            action = self.chooseStrategyAction(gameState)
            elapsed = time.perf_counter() - started
            if elapsed > 0.5:
                print(f"Agent {self.index}: trage beurt ({elapsed:.3f}s)")
            if action in legal:
                return action
            print(f"Agent {self.index}: ongeldige actie {action!r}")
        except Exception:
            print(f"Agent {self.index}: fout tijdens kiezen van actie")
            traceback.print_exc()
        return Directions.STOP if Directions.STOP in legal else legal[0]

    def successor(self, state, action):
        next_state = state.generateSuccessor(self.index, action)
        pos = next_state.getAgentState(self.index).getPosition()
        return next_state

    def distance(self, a, b):
        return self.getMazeDistance(nearestPoint(a), nearestPoint(b))

    def closest(self, pos, targets):
        return min((self.distance(pos, t) for t in targets), default=9999)

    def actions(self, state):
        legal = state.getLegalActions(self.index)
        moving = [a for a in legal if a != Directions.STOP]
        return moving or legal

    def select(self, state, evaluator):
        actions = self.actions(state)
        if not actions:
            return Directions.STOP
        scored = [(evaluator(self.successor(state, a), a), a) for a in actions]
        best = max(v for v, a in scored)
        return random.choice([a for v, a in scored if v == best])

    def movement_penalty(self, state, action):
        pos = state.getAgentPosition(self.index)
        penalty = 0
        if pos == self.previous_position:
            penalty -= 3
        return penalty
class SmartOffense(TeamAgent):
    def chooseStrategyAction(self, gameState):
        me = gameState.getAgentState(self.index)
        pos = me.getPosition()
        food = self.getFood(gameState).asList()
        capsules = self.getCapsules(gameState)
        carrying = me.numCarrying
        enemies = [gameState.getAgentState(i) for i in self.getOpponents(gameState)]
        ghosts = [e for e in enemies if not e.isPacman and e.scaredTimer <= 1
                  and e.getPosition() is not None]
        danger = self.closest(pos, [g.getPosition() for g in ghosts])
        home_dist = self.closest(pos, self.border)
        time_left = getattr(gameState.data, 'timeleft', 1200)
        return_home = (carrying >= 4 or (carrying >= 1 and danger <= 5)
                       or (carrying > 0 and time_left < 4 * (home_dist + 5))
                       or len(food) <= 2)

        def evaluate(next_state, action):
            next_me = next_state.getAgentState(self.index)
            p = next_me.getPosition()
            next_food = self.getFood(next_state).asList()
            value = 0.0
            if return_home:
                value -= 5 * self.closest(p, self.border)
                if not next_me.isPacman:
                    value += 120 + 15 * carrying
            else:
                value -= 2.5 * self.closest(p, next_food)
                value += 25 * (len(food) - len(next_food))
                if capsules and danger <= 7:
                    value -= 1.5 * self.closest(p, capsules)
                if p in capsules:
                    value += 45
            for ghost in ghosts:
                d = self.distance(p, ghost.getPosition())
                if next_me.isPacman:
                    if d <= 1:
                        value -= 400
                    elif d <= 2:
                        value -= 120
                    elif d <= 4:
                        value -= 25 / d
            if p == pos:
                value -= 5
            if p == self.previous_position:
                value -= 2
            return value

        action = self.select(gameState, evaluate)
        self.previous_position = pos
        return action


class SmartDefense(TeamAgent):
    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self.last_defended_food = set(self.getFoodYouAreDefending(gameState).asList())
        self.suspected_target = None

    def chooseStrategyAction(self, gameState):
        pos = gameState.getAgentPosition(self.index)
        enemies = [gameState.getAgentState(i) for i in self.getOpponents(gameState)]
        invaders = [e.getPosition() for e in enemies
                    if e.isPacman and e.getPosition() is not None]
        defended = set(self.getFoodYouAreDefending(gameState).asList())
        missing = self.last_defended_food - defended
        if missing:
            self.suspected_target = min(missing, key=lambda p: self.distance(pos, p))
        self.last_defended_food = defended
        if invaders:
            target = min(invaders, key=lambda p: self.distance(pos, p))
            self.suspected_target = None
        elif self.suspected_target is not None:
            target = self.suspected_target
            if self.distance(pos, target) <= 1:
                self.suspected_target = None
        else:
            target = self.patrol

        def evaluate(next_state, action):
            p = next_state.getAgentPosition(self.index)
            next_me = next_state.getAgentState(self.index)
            value = -5 * self.distance(p, target)
            if next_me.isPacman:
                value -= 200
            if p == self.previous_position:
                value -= 2
            if p == pos:
                value -= 4
            if invaders and next_me.scaredTimer > 0:
                d = self.closest(p, invaders)
                if d <= 2:
                    value -= 150
            return value

        action = self.select(gameState, evaluate)
        self.previous_position = pos
        return action
