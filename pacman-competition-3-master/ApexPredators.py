# myTeam.py
# ---------
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

"""
myTeam.py / ApexPredators.py
----------------------------
Team: ApexPredators
Course: Decision Making (Minor Autonome Systemen) - HvA / UvA
Contest: Pacman Capture the Flag

Championship Architectuur (1 Aanvaller + 1 Verdediger):
- OffensiveAgent:
  * Doel-commitment (Target Persistence): voorkomt target-thrashing en oscillaties.
  * BFS-padplanning met dynamische geestenvermijding op vijandelijk gebied.
  * Flankeert automatisch langs camping defenders via open grensovergangen.
  * Krachtcapsule-opportunisme: eet capsule -> jaagt bange spoken op.
  * Veilig bankeren bij 3-4 pellets of naderend gevaar.
- DefensiveAgent:
  * Directe onderschepping van indringers via getMazeDistance.
  * Alarminterceptie bij verdwenen voedsel.
  * Strategische frontline-patrouille langs grensovergangen nabij het voedselzwaartepunt.
  * Scared-standoff containment (afstand 2-3) om niet dood te gaan tijdens vijandelijke capsule.
"""

from __future__ import annotations

import collections
import random
from typing import Optional

from captureAgents import CaptureAgent
from game import Directions, Actions


#################
# Team creation #
#################

def createTeam(firstIndex: int,
               secondIndex: int,
               isRed: bool,
               first: str = 'OffensiveAgent',
               second: str = 'DefensiveAgent',
               **kwargs) -> list[CaptureAgent]:
    """
    Initialiseert het ApexPredators team met 1 Aanvaller en 1 Verdediger.
    """
    return [globals().get(first, OffensiveAgent)(firstIndex),
            globals().get(second, DefensiveAgent)(secondIndex)]


#####################
# Basis Agentklasse #
#####################

class ApexBaseAgent(CaptureAgent):
    """
    Gemeenschappelijke functionaliteit voor topologie, afstanden en navigatie.
    """

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self.start = gameState.getAgentPosition(self.index)
        walls = gameState.getWalls()
        self.walls = walls
        self.width = walls.width
        self.height = walls.height

        # Bepaal gebiedsgrenzen
        self.mid_x = self.width // 2
        self.home_x = (self.mid_x - 1) if self.red else self.mid_x
        self.enemy_x = self.mid_x if self.red else (self.mid_x - 1)

        # Zoek alle doorgangen op de grens
        self.border_crossings = [
            (self.home_x, y) for y in range(self.height)
            if not walls[self.home_x][y] and not walls[self.enemy_x][y]
        ]
        if not self.border_crossings:
            self.border_crossings = [
                (self.home_x, y) for y in range(self.height)
                if not walls[self.home_x][y]
            ]
        self.border_crossings.sort(key=lambda b: b[1])

    def is_home(self, pos: tuple[int, int]) -> bool:
        """Geeft True als de positie op eigen helft ligt."""
        return pos[0] < self.mid_x if self.red else pos[0] >= self.mid_x

    def dist(self, p1: tuple[int, int], p2: tuple[int, int]) -> int:
        """Kortste doolhofafstand via Berkeley precomputed distancer."""
        return self.getMazeDistance(p1, p2)

    def get_active_ghosts(self, gameState) -> list[tuple[int, int]]:
        """Posities van actieve (gevaarlijke) vijandige spoken."""
        ghosts = []
        for opp in self.getOpponents(gameState):
            s = gameState.getAgentState(opp)
            p = s.getPosition()
            if p is not None and not s.isPacman and s.scaredTimer <= 2:
                ghosts.append(p)
        return ghosts

    def get_scared_ghosts(self, gameState) -> list[tuple[tuple[int, int], int]]:
        """Posities en timers van kwetsbare (scared) vijandige spoken."""
        scared = []
        for opp in self.getOpponents(gameState):
            s = gameState.getAgentState(opp)
            p = s.getPosition()
            if p is not None and not s.isPacman and s.scaredTimer > 2:
                scared.append((p, s.scaredTimer))
        return scared

    def get_invaders(self, gameState) -> list[tuple[int, tuple[int, int], int]]:
        """Zichtbare indringers op eigen helft: (index, pos, numCarrying)."""
        invaders = []
        for opp in self.getOpponents(gameState):
            s = gameState.getAgentState(opp)
            p = s.getPosition()
            if p is not None and s.isPacman:
                invaders.append((opp, p, s.numCarrying))
        return invaders

    def bfs_direction(self, start: tuple[int, int], goals: set[tuple[int, int]], forbidden: set[tuple[int, int]]) -> Optional[str]:
        """
        Vindt via BFS het kortste pad van start naar één van de goals dat forbidden vermijdt.
        Geeft de eerste actie (richting) terug.
        """
        if not goals or start in goals:
            return None

        queue = collections.deque()
        visited = {start}

        x, y = int(start[0]), int(start[1])
        for a, (dx, dy) in [(Directions.NORTH, (0, 1)), (Directions.SOUTH, (0, -1)),
                            (Directions.EAST, (1, 0)), (Directions.WEST, (-1, 0))]:
            nx, ny = x + dx, y + dy
            nb = (nx, ny)
            if not self.walls[nx][ny] and nb not in forbidden:
                if nb in goals:
                    return a
                visited.add(nb)
                queue.append((nb, a))

        while queue:
            curr, first_action = queue.popleft()
            cx, cy = int(curr[0]), int(curr[1])

            for a, (dx, dy) in [(Directions.NORTH, (0, 1)), (Directions.SOUTH, (0, -1)),
                                (Directions.EAST, (1, 0)), (Directions.WEST, (-1, 0))]:
                nx, ny = cx + dx, cy + dy
                nb = (nx, ny)
                if not self.walls[nx][ny] and nb not in visited and nb not in forbidden:
                    if nb in goals:
                        return first_action
                    visited.add(nb)
                    queue.append((nb, first_action))

        return None

    def get_best_action_towards(self, gameState, target_pos, avoid_positions=None):
        """
        Kiest de legale actie die ons het dichtst bij target_pos brengt.
        Optioneel worden gevaarlijke posities (avoid_positions) gemeden.
        """
        if avoid_positions is None:
            avoid_positions = set()

        legal_actions = gameState.getLegalActions(self.index)
        moving_actions = [a for a in legal_actions if a != Directions.STOP]
        if not moving_actions:
            return Directions.STOP

        best_action = None
        min_dist = 999999

        for action in moving_actions:
            succ = gameState.generateSuccessor(self.index, action)
            next_pos = succ.getAgentPosition(self.index)

            if next_pos in avoid_positions:
                continue

            dist = self.getMazeDistance(next_pos, target_pos)
            if dist < min_dist:
                min_dist = dist
                best_action = action

        if best_action is None:
            best_action = min(
                moving_actions,
                key=lambda a: self.getMazeDistance(
                    gameState.generateSuccessor(self.index, a).getAgentPosition(self.index),
                    target_pos
                )
            )

        return best_action


###################
# Offensive Agent #
###################

class OffensiveAgent(ApexBaseAgent):
    """
    Agressieve, intelligente aanvaller:
    - Kiest doelwitten die niet door vijandelijke geesten bewaakt worden.
    - Flankeert automatisch via open grensovergangen dankzij BFS routeplanning.
    - Pakt krachtcapsules wanneer geesten in de buurt zijn.
    - Eet kwetsbare geesten op voor bonuspunten en vrije doorgang.
    - Bankeert tijdig punten om winst te verzilveren.
    - Doel-commitment: houdt hetzelfde doelwit vast totdat het bereikt of onveilig is.
    """

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self.current_target = None

    def chooseAction(self, gameState):
        my_pos = gameState.getAgentPosition(self.index)
        my_state = gameState.getAgentState(self.index)
        carrying = my_state.numCarrying
        time_left = getattr(gameState.data, 'timeleft', 1200)

        food_list = self.getFood(gameState).asList()
        capsules = self.getCapsules(gameState)
        active_ghosts = self.get_active_ghosts(gameState)
        scared_ghosts = self.get_scared_ghosts(gameState)

        # Verboden cellen: spookposities en directe buren ALLEEN OP VIJANDELIJK GEBIED!
        forbidden_cells = set()
        for g_pos in active_ghosts:
            for dx, dy in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
                cell = (int(g_pos[0] + dx), int(g_pos[1] + dy))
                if not self.is_home(cell):
                    forbidden_cells.add(cell)

        min_ghost_dist = min([self.dist(my_pos, g) for g in active_ghosts], default=999)
        min_border_dist = min([self.dist(my_pos, b) for b in self.border_crossings])

        # -------------------------------------------------------------
        # BESLISSING 1: Terugkeren naar huis (Bankeren)
        # -------------------------------------------------------------
        should_return = (
            len(food_list) <= 2
            or time_left < min_border_dist * 2 + 15
            or carrying >= 4
            or (carrying >= 2 and min_ghost_dist <= 5)
            or (carrying >= 1 and min_ghost_dist <= 3)
            or (carrying > 0 and self.getScore(gameState) > 0 and time_left < 150)
        )

        if should_return and my_state.isPacman:
            self.current_target = None
            safe_crossings = {b for b in self.border_crossings if b not in forbidden_cells}
            if not safe_crossings:
                safe_crossings = set(self.border_crossings)

            action = self.bfs_direction(my_pos, safe_crossings, forbidden_cells)
            if action:
                return action
            target_border = min(safe_crossings, key=lambda b: self.dist(my_pos, b))
            return self.get_best_action_towards(gameState, target_border, forbidden_cells)

        # -------------------------------------------------------------
        # BESLISSING 2: Jagen op 'scared' geesten (gratis eliminatie)
        # -------------------------------------------------------------
        if scared_ghosts and my_state.isPacman:
            nearest_scared, s_timer = min(scared_ghosts, key=lambda sg: self.dist(my_pos, sg[0]))
            d_scared = self.dist(my_pos, nearest_scared)
            if d_scared <= s_timer and d_scared <= 6:
                self.current_target = None
                action = self.bfs_direction(my_pos, {nearest_scared}, forbidden_cells)
                if action:
                    return action
                return self.get_best_action_towards(gameState, nearest_scared, forbidden_cells)

        # -------------------------------------------------------------
        # BESLISSING 3: Krachtcapsule prioritering
        # -------------------------------------------------------------
        if capsules and active_ghosts and min_ghost_dist <= 7:
            nearest_cap = min(capsules, key=lambda c: self.dist(my_pos, c))
            d_cap = self.dist(my_pos, nearest_cap)
            if d_cap < min_ghost_dist + 2:
                self.current_target = nearest_cap
                action = self.bfs_direction(my_pos, {nearest_cap}, forbidden_cells)
                if action:
                    return action
                return self.get_best_action_towards(gameState, nearest_cap, forbidden_cells)

        # -------------------------------------------------------------
        # BESLISSING 4: Voedselverzameling met doel-commitment & flankeren
        # -------------------------------------------------------------
        if food_list:
            target_valid = (
                self.current_target is not None
                and self.current_target in food_list
                and self.current_target not in forbidden_cells
                and min([self.dist(g, self.current_target) for g in active_ghosts], default=999) > 2
            )

            if not target_valid:
                self.current_target = self._select_safe_food(my_pos, food_list, active_ghosts)

            if self.current_target:
                action = self.bfs_direction(my_pos, {self.current_target}, forbidden_cells)
                if action:
                    return action
                return self.get_best_action_towards(gameState, self.current_target, forbidden_cells)

        # Noodplan: ga naar de grens
        nearest_border = min(self.border_crossings, key=lambda b: self.dist(my_pos, b))
        return self.get_best_action_towards(gameState, nearest_border, forbidden_cells)

    def _select_safe_food(self, my_pos, food_list, active_ghosts):
        """Kiest voedsel dat niet bewaakt wordt door actieve geesten."""
        if not active_ghosts:
            return min(food_list, key=lambda f: self.dist(my_pos, f))

        safe_foods = [
            f for f in food_list
            if min([self.dist(g, f) for g in active_ghosts], default=999) >= 3
        ]

        if not safe_foods:
            return max(food_list, key=lambda f: min([self.dist(g, f) for g in active_ghosts], default=0))

        def food_score(f):
            d_my = self.dist(my_pos, f)
            d_ghost = min([self.dist(g, f) for g in active_ghosts], default=999)
            cluster = sum(1 for o in safe_foods if abs(f[0] - o[0]) + abs(f[1] - o[1]) <= 2)
            return -d_my + cluster * 0.8 + min(d_ghost, 8) * 0.5

        return max(safe_foods, key=food_score)


###################
# Defensive Agent #
###################

class DefensiveAgent(ApexBaseAgent):
    """
    Betrouwbare, waakzame verdediger:
    - Onderschept indringers direct via kortste route.
    - Onderzoekt direct verdwenen stippen (alarm).
    - Patrouilleert strategisch de grens nabij het voedselzwaartepunt.
    - Scared containment: houdt 2 stappen afstand wanneer 'scared'.
    """

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self.last_defended_food = set(self.getFoodYouAreDefending(gameState).asList())
        self.alarm_pos = None

    def chooseAction(self, gameState):
        my_pos = gameState.getAgentPosition(self.index)
        my_state = gameState.getAgentState(self.index)
        time_left = getattr(gameState.data, 'timeleft', 1200)
        score = self.getScore(gameState)

        # Detecteer verdwenen voedsel
        curr_defended = set(self.getFoodYouAreDefending(gameState).asList())
        missing = self.last_defended_food - curr_defended
        if missing:
            self.alarm_pos = min(missing, key=lambda p: self.dist(my_pos, p))
        self.last_defended_food = curr_defended

        # Zoek zichtbare indringers
        invaders = self.get_invaders(gameState)

        # -------------------------------------------------------------
        # TOESTAND 0: Nood-DoubleOffense (als we ver achterstaan laat)
        # -------------------------------------------------------------
        if score <= -6 and time_left < 250 and not invaders:
            enemy_food = self.getFood(gameState).asList()
            if enemy_food:
                target = min(enemy_food, key=lambda f: self.dist(my_pos, f))
                return self.get_best_action_towards(gameState, target)

        # -------------------------------------------------------------
        # TOESTAND 1: Indringer onderscheppen
        # -------------------------------------------------------------
        if invaders:
            self.alarm_pos = None
            target_invader = max(invaders, key=lambda inv: (inv[2], -self.dist(my_pos, inv[1])))[1]

            if my_state.scaredTimer > 0:
                legal = gameState.getLegalActions(self.index)
                moving = [a for a in legal if a != Directions.STOP]
                best_act = Directions.STOP
                best_score = -99999
                for a in moving:
                    succ = gameState.generateSuccessor(self.index, a)
                    np = succ.getAgentPosition(self.index)
                    if not self.is_home(np):
                        continue
                    d = self.dist(np, target_invader)
                    if d >= 2:
                        s = -abs(d - 2.5)
                        if s > best_score:
                            best_score = s
                            best_act = a
                return best_act if best_act != Directions.STOP else random.choice(moving or [Directions.STOP])

            # Vol gas direct op de indringer af!
            return self.get_best_action_towards(gameState, target_invader)

        # -------------------------------------------------------------
        # TOESTAND 2: Alarm op verdwenen voedsel
        # -------------------------------------------------------------
        if self.alarm_pos is not None:
            if self.dist(my_pos, self.alarm_pos) <= 1:
                self.alarm_pos = None  # Plek gecontroleerd
            else:
                return self.get_best_action_towards(gameState, self.alarm_pos)

        # -------------------------------------------------------------
        # TOESTAND 3: Strategische patrouille bij voedselzwaartepunt
        # -------------------------------------------------------------
        target_patrol = self._get_strategic_patrol_point(curr_defended)
        return self.get_best_action_towards(gameState, target_patrol)

    def _get_strategic_patrol_point(self, defended_food):
        """Berekent een patrouillepunt op de grens dat dicht bij onze stippen ligt."""
        if not defended_food:
            return self.border_crossings[len(self.border_crossings) // 2]

        avg_y = sum(f[1] for f in defended_food) / len(defended_food)
        return min(self.border_crossings, key=lambda b: abs(b[1] - avg_y))
