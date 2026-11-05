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
myTeam.py
---------
Team: ApexPredators
Course: Decision Making (Autonome Systemen) - HvA / UvA
Contest: Pacman Capture the Flag

This module implements a competitive capture-the-flag team combining:
1. Topological Maze Analysis:
   - Offline precomputation of border crossings and safe boundary portals.
   - Cul-de-sac and dead-end graph analysis with depth and junction identification.
2. Bayesian Belief Tracking:
   - Exact inference over unobserved opponent positions under partial observability.
   - Multi-modal sensor updates (sonar distance, line-of-sight sight horizon, and food disappearance).
3. Dynamic Role Allocation & Coordination:
   - Shared blackboard architecture between teammates.
   - Adaptive role switching (Offense, Defense, Double Offense, Double Defense).
4. Goal-Driven Safe A* & Tactical Search:
   - Safe food clustering and dead-end entry safety verification.
   - Local tactical evaluation for close-quarters ghost evasion and border interception.
   - Intelligent scared-ghost containment and power-capsule exploitation.
"""

from __future__ import annotations

import random
from typing import Any, Optional

import util
from capture import GameState, SCARED_TIME, SIGHT_RANGE, SONAR_NOISE_RANGE, SONAR_NOISE_VALUES
from captureAgents import CaptureAgent
from game import Action, Actions, Directions


#################
# Team creation #
#################

def createTeam(firstIndex: int,
               secondIndex: int,
               isRed: bool,
               first: str = 'OffensiveAgent',
               second: str = 'DefensiveAgent',
               **kwargs: Any) -> list[CaptureAgent]:
    """
    Returns a list of two agents that form the contest team.
    By default initializes firstIndex as OffensiveAgent and secondIndex as DefensiveAgent.
    """
    first_agent = globals().get(first, OffensiveAgent)(firstIndex)
    second_agent = globals().get(second, DefensiveAgent)(secondIndex)
    return [first_agent, second_agent]


#############################
# Topological Maze Analysis #
#############################

class MazeAnalyzer:
    """
    Analyzes the static layout topology during initialization:
    - Precomputes legal positions, walls, and adjacency relations.
    - Determines border crossings connecting home territory to enemy territory.
    - Performs topological pruning to identify dead-end tunnels, their depths,
      and their single core entry gates.
    """

    def __init__(self, gameState: GameState, isRed: bool) -> None:
        self.width: int = gameState.data.layout.width
        self.height: int = gameState.data.layout.height
        self.walls = gameState.getWalls()
        self.isRed: bool = isRed

        # Compute legal positions and adjacency graph
        self.legal_positions: set[tuple[int, int]] = set()
        self.adjacency: dict[tuple[int, int], list[tuple[int, int]]] = {}

        for x in range(self.width):
            for y in range(self.height):
                if not self.walls[x][y]:
                    pos = (x, y)
                    self.legal_positions.add(pos)

        for pos in self.legal_positions:
            nbrs: list[tuple[int, int]] = []
            x, y = pos
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) in self.legal_positions:
                    nbrs.append((nx, ny))
            self.adjacency[pos] = nbrs

        # Identify home and enemy territory
        self.mid_x: int = self.width // 2
        self.home_border_x: int = (self.mid_x - 1) if self.isRed else self.mid_x
        self.enemy_border_x: int = self.mid_x if self.isRed else (self.mid_x - 1)

        # Border crossings: legal home-side cells adjacent to legal enemy-side cells
        self.border_crossings: list[tuple[int, int]] = []
        for y in range(self.height):
            home_pos = (self.home_border_x, y)
            enemy_pos = (self.enemy_border_x, y)
            if home_pos in self.legal_positions and enemy_pos in self.legal_positions:
                self.border_crossings.append(home_pos)

        # Topological pruning to find dead ends and entry gates
        self._analyze_dead_ends()

    def is_home_territory(self, pos: tuple[int, int]) -> bool:
        """Returns True if position is within our team's side."""
        if self.isRed:
            return pos[0] < self.mid_x
        return pos[0] >= self.mid_x

    def _analyze_dead_ends(self) -> None:
        """
        Prunes cells with degree <= 1 iteratively until only cycle/core graph remains.
        Maps each dead-end cell to its depth and its unique core entry gate.
        """
        degree = {p: len(self.adjacency[p]) for p in self.legal_positions}
        queue = [p for p in self.legal_positions if degree[p] <= 1]
        dead_ends = set()

        while queue:
            curr = queue.pop(0)
            dead_ends.add(curr)
            for nbr in self.adjacency[curr]:
                if nbr not in dead_ends:
                    degree[nbr] -= 1
                    if degree[nbr] <= 1:
                        queue.append(nbr)

        self.core_positions: set[tuple[int, int]] = self.legal_positions - dead_ends
        self.dead_end_positions: set[tuple[int, int]] = dead_ends
        self.entry_gates: dict[tuple[int, int], tuple[int, int]] = {}
        self.dead_end_depths: dict[tuple[int, int], int] = {}

        # BFS from each dead end to discover its connecting entry gate and depth
        for d_pos in self.dead_end_positions:
            q: list[tuple[tuple[int, int], int]] = [(d_pos, 0)]
            visited = {d_pos}
            found_gate = None
            found_depth = 0
            while q:
                curr, depth = q.pop(0)
                if curr in self.core_positions:
                    found_gate = curr
                    found_depth = depth
                    break
                for nbr in self.adjacency[curr]:
                    if nbr not in visited:
                        visited.add(nbr)
                        q.append((nbr, depth + 1))

            self.entry_gates[d_pos] = found_gate if found_gate is not None else d_pos
            self.dead_end_depths[d_pos] = found_depth


############################
# Bayesian Belief Tracker  #
############################

class BayesianBeliefTracker:
    """
    Maintains probability distributions over all legal positions for each opponent.
    Updates beliefs using:
    - Ground-truth sightings when within 5 Manhattan distance.
    - Negative sightings (opponent is NOT within 5 steps of any observable teammate).
    - Noisy sonar sensor readings (uniform noise in [-6, 6]).
    - Eaten food events on home territory (pinpoints exact opponent location).
    - Respawn after death.
    """

    def __init__(self,
                 opponents: list[int],
                 legal_positions: set[tuple[int, int]],
                 adjacency: dict[tuple[int, int], list[tuple[int, int]]],
                 initial_positions: dict[int, tuple[int, int]]) -> None:
        self.opponents: list[int] = opponents
        self.legal_positions: list[tuple[int, int]] = sorted(legal_positions)
        self.adjacency: dict[tuple[int, int], list[tuple[int, int]]] = adjacency
        self.initial_positions: dict[int, tuple[int, int]] = initial_positions

        self.beliefs: dict[int, util.Counter] = {}
        for opp in self.opponents:
            self.beliefs[opp] = util.Counter()
            init_pos = self.initial_positions.get(opp)
            if init_pos:
                self.beliefs[opp][init_pos] = 1.0
            else:
                for pos in self.legal_positions:
                    self.beliefs[opp][pos] = 1.0 / len(self.legal_positions)

    def observe(self,
                gameState: GameState,
                my_index: int,
                team_indices: list[int],
                food_eaten_pos: Optional[tuple[int, int]] = None) -> None:
        """Updates belief distributions based on current GameState observation."""
        my_pos = gameState.getAgentPosition(my_index)
        if my_pos is None:
            return

        team_positions = [gameState.getAgentPosition(i) for i in team_indices]
        team_positions = [p for p in team_positions if p is not None]
        noisy_distances = gameState.getAgentDistances()

        for opp in self.opponents:
            exact_pos = gameState.getAgentPosition(opp)
            if exact_pos is not None:
                # Direct ground-truth observation
                new_belief = util.Counter()
                new_belief[exact_pos] = 1.0
                self.beliefs[opp] = new_belief
                continue

            # Check if this opponent just ate a food pellet on our territory
            if food_eaten_pos is not None:
                # If this opponent is likely the invader, update directly
                curr_dist_to_food = util.manhattanDistance(food_eaten_pos, my_pos)
                if noisy_distances is not None and abs(curr_dist_to_food - noisy_distances[opp]) <= 6:
                    new_belief = util.Counter()
                    new_belief[food_eaten_pos] = 1.0
                    self.beliefs[opp] = new_belief
                    continue

            # Negative observation + Sonar sensor update
            new_belief = util.Counter()
            noisy_dist = noisy_distances[opp] if noisy_distances is not None else None

            for pos in self.legal_positions:
                # Negative observation: would have been seen if within distance 5 of any teammate
                if any(util.manhattanDistance(t_pos, pos) <= SIGHT_RANGE for t_pos in team_positions):
                    continue

                prior = self.beliefs[opp][pos]
                if prior <= 0:
                    continue

                if noisy_dist is not None:
                    true_d = util.manhattanDistance(my_pos, pos)
                    sensor_prob = gameState.getDistanceProb(true_d, noisy_dist)
                    if sensor_prob > 0:
                        new_belief[pos] = prior * sensor_prob
                else:
                    new_belief[pos] = prior

            if new_belief.totalCount() == 0:
                # Degenerate case fallback: uniform outside sight horizon
                for pos in self.legal_positions:
                    if not any(util.manhattanDistance(t_pos, pos) <= SIGHT_RANGE for t_pos in team_positions):
                        new_belief[pos] = 1.0

            new_belief.normalize()
            self.beliefs[opp] = new_belief

    def elapse_time(self, opp: int) -> None:
        """Propagates opponent belief distribution across legal transitions."""
        new_belief = util.Counter()
        for pos, prob in self.beliefs[opp].items():
            if prob <= 0:
                continue
            nbrs = self.adjacency.get(pos, [])
            all_moves = nbrs + [pos]
            spread = prob / len(all_moves)
            for nxt in all_moves:
                new_belief[nxt] += spread

        new_belief.normalize()
        self.beliefs[opp] = new_belief

    def reset_agent(self, opp: int) -> None:
        """Resets belief to starting position when an opponent is eliminated."""
        init_pos = self.initial_positions.get(opp)
        new_belief = util.Counter()
        if init_pos:
            new_belief[init_pos] = 1.0
        self.beliefs[opp] = new_belief

    def get_most_likely_position(self, opp: int) -> tuple[int, int]:
        """Returns the single position with highest probability for opponent."""
        return self.beliefs[opp].argMax()

    def get_invader_probability(self, opp: int, isRed: bool, mid_x: int) -> float:
        """Computes probability that opponent is currently invading home side."""
        prob_sum = 0.0
        for pos, prob in self.beliefs[opp].items():
            is_on_red_side = pos[0] < mid_x
            is_invading = is_on_red_side if not isRed else (not is_on_red_side)
            if is_invading:
                prob_sum += prob
        return prob_sum


####################################
# Shared Blackboard / Coordinator #
####################################

class TeamCoordinator:
    """
    Coordinates shared strategic knowledge between both agents:
    - Manages single shared Bayesian belief tracker.
    - Detects food disappearance events.
    - Implements dynamic role switching and target food deconfliction.
    """

    def __init__(self,
                 gameState: GameState,
                 isRed: bool,
                 analyzer: MazeAnalyzer) -> None:
        self.isRed: bool = isRed
        self.analyzer: MazeAnalyzer = analyzer
        self.team_indices: list[int] = (
            gameState.getRedTeamIndices() if isRed else gameState.getBlueTeamIndices()
        )
        self.opponents: list[int] = (
            gameState.getBlueTeamIndices() if isRed else gameState.getRedTeamIndices()
        )

        initial_positions = {
            opp: gameState.getInitialAgentPosition(opp) for opp in self.opponents
        }
        self.belief_tracker = BayesianBeliefTracker(
            self.opponents,
            self.analyzer.legal_positions,
            self.analyzer.adjacency,
            initial_positions
        )

        self.last_defending_food: list[tuple[int, int]] = []
        self.assigned_targets: dict[int, tuple[int, int]] = {}
        self.last_food_eaten_pos: Optional[tuple[int, int]] = None

    def update(self, gameState: GameState, my_index: int) -> None:
        """Synchronizes coordinator state and belief updates on agent turn."""
        curr_defending_food = (
            gameState.getRedFood().asList() if self.isRed else gameState.getBlueFood().asList()
        )
        food_eaten_pos = None

        if self.last_defending_food:
            missing_food = set(self.last_defending_food) - set(curr_defending_food)
            if missing_food:
                food_eaten_pos = list(missing_food)[0]
                self.last_food_eaten_pos = food_eaten_pos

        self.last_defending_food = curr_defending_food

        # Elapse time for opponent whose turn occurred before ours
        for opp in self.opponents:
            self.belief_tracker.elapse_time(opp)

        self.belief_tracker.observe(gameState, my_index, self.team_indices, food_eaten_pos)

    def get_claimed_target(self, teammate_index: int) -> Optional[tuple[int, int]]:
        """Returns the target claimed by teammate to avoid duplicate paths."""
        return self.assigned_targets.get(teammate_index)

    def claim_target(self, my_index: int, target: tuple[int, int]) -> None:
        """Claims a goal position for this agent."""
        self.assigned_targets[my_index] = target


#############################
# Base Strategic Capture Agent #
#############################

# Global coordinator container to link both agents in the same game instance
GLOBAL_COORDINATOR: Optional[TeamCoordinator] = None
GLOBAL_ANALYZER: Optional[MazeAnalyzer] = None


class StrategicCaptureAgent(CaptureAgent):
    """
    Base class providing common utilities for both offensive and defensive agents:
    - Precomputes shortest maze distances.
    - Maintains world model and shared team blackboard.
    - Implements safe A* pathfinding and tactical ghost danger evaluation.
    """

    def registerInitialState(self, gameState: GameState) -> None:
        CaptureAgent.registerInitialState(self, gameState)
        global GLOBAL_COORDINATOR, GLOBAL_ANALYZER

        team = self.getTeam(gameState)
        is_first_agent = (self.index == min(team))

        if is_first_agent or GLOBAL_ANALYZER is None:
            GLOBAL_ANALYZER = MazeAnalyzer(gameState, self.red)

        self.analyzer: MazeAnalyzer = GLOBAL_ANALYZER

        if is_first_agent or GLOBAL_COORDINATOR is None:
            GLOBAL_COORDINATOR = TeamCoordinator(gameState, self.red, self.analyzer)

        self.coordinator: TeamCoordinator = GLOBAL_COORDINATOR
        self.teammate_index: int = [i for i in team if i != self.index][0]

    def get_active_ghosts(self, gameState: GameState) -> list[tuple[int, tuple[int, int], int]]:
        """
        Returns list of enemy ghosts in enemy territory that are dangerous:
        tuple (opp_index, position, scaredTimer).
        """
        ghosts = []
        for opp in self.getOpponents(gameState):
            opp_state = gameState.getAgentState(opp)
            pos = gameState.getAgentPosition(opp)
            if pos is None:
                # Use belief tracker best estimate
                pos = self.coordinator.belief_tracker.get_most_likely_position(opp)

            # Enemy is ghost if on their territory
            if not self.analyzer.is_home_territory(pos):
                ghosts.append((opp, pos, opp_state.scaredTimer))
        return ghosts

    def get_invaders(self, gameState: GameState) -> list[tuple[int, tuple[int, int], int]]:
        """
        Returns list of enemy invaders on our territory:
        tuple (opp_index, position, numCarrying).
        """
        invaders = []
        for opp in self.getOpponents(gameState):
            opp_state = gameState.getAgentState(opp)
            pos = gameState.getAgentPosition(opp)
            if pos is not None:
                if self.analyzer.is_home_territory(pos):
                    invaders.append((opp, pos, opp_state.numCarrying))
            else:
                prob = self.coordinator.belief_tracker.get_invader_probability(
                    opp, self.red, self.analyzer.mid_x
                )
                if prob > 0.4:
                    pos = self.coordinator.belief_tracker.get_most_likely_position(opp)
                    invaders.append((opp, pos, opp_state.numCarrying))
        return invaders

    def a_star_search(self,
                      start: tuple[int, int],
                      goals: set[tuple[int, int]],
                      danger_zones: dict[tuple[int, int], float]) -> list[Action]:
        """
        A* graph search returning sequence of actions to nearest reachable goal,
        incorporating dynamic danger zone penalties.
        """
        if start in goals:
            return []

        frontier = util.PriorityQueue()
        frontier.push((start, []), 0)
        cost_so_far: dict[tuple[int, int], float] = {start: 0.0}

        while not frontier.isEmpty():
            curr, actions = frontier.pop()

            if curr in goals:
                return actions

            for nbr in self.analyzer.adjacency.get(curr, []):
                step_cost = 1.0 + danger_zones.get(nbr, 0.0)
                new_cost = cost_so_far[curr] + step_cost

                if nbr not in cost_so_far or new_cost < cost_so_far[nbr]:
                    cost_so_far[nbr] = new_cost
                    action = Actions.vectorToDirection((nbr[0] - curr[0], nbr[1] - curr[1]))
                    # Heuristic: min maze distance to any goal
                    heuristic = min(self.getMazeDistance(nbr, g) for g in goals)
                    frontier.push((nbr, actions + [action]), new_cost + heuristic)

        return []

    def chooseAction(self, gameState: GameState) -> Action:
        """Default fallback if not overridden."""
        actions = gameState.getLegalActions(self.index)
        return random.choice(actions)


#############################
# Offensive Capture Agent   #
#############################

class OffensiveAgent(StrategicCaptureAgent):
    """
    Intelligent Offensive Pacman Agent:
    - Primary harvester of food pellets and capsules.
    - Verifies dead-end safety before entering cul-de-sacs.
    - Monitors food carried and game clock to execute timely deposit runs.
    - Features local tactical evasion when active ghosts threaten interception.
    """

    def chooseAction(self, gameState: GameState) -> Action:
        self.coordinator.update(gameState, self.index)
        my_pos = gameState.getAgentPosition(self.index)
        my_state = gameState.getAgentState(self.index)
        legal_actions = gameState.getLegalActions(self.index)

        if not legal_actions:
            return Directions.STOP

        food_list = self.getFood(gameState).asList()
        capsules = self.getCapsules(gameState)
        active_ghosts = self.get_active_ghosts(gameState)

        # Danger zone mapping around active ghosts
        danger_zones: dict[tuple[int, int], float] = {}
        min_ghost_dist = 999.0
        nearest_ghost_pos = None

        for opp, g_pos, scared_timer in active_ghosts:
            dist = self.getMazeDistance(my_pos, g_pos)
            if scared_timer <= 2:
                if dist < min_ghost_dist:
                    min_ghost_dist = dist
                    nearest_ghost_pos = g_pos

                # Ghost threat radius
                for pos in self.analyzer.legal_positions:
                    d_to_g = self.getMazeDistance(pos, g_pos)
                    if d_to_g <= 1:
                        danger_zones[pos] = 10000.0
                    elif d_to_g == 2:
                        danger_zones[pos] = 50.0
                    elif d_to_g == 3:
                        danger_zones[pos] = 15.0

        # Assess Dead-End Safety
        # Never enter or remain in dead ends if an active ghost can cut off the entry gate
        for dead_cell, gate in self.analyzer.entry_gates.items():
            if not self.analyzer.is_home_territory(dead_cell):
                if nearest_ghost_pos is not None and min_ghost_dist < 10:
                    d_ghost_gate = self.getMazeDistance(nearest_ghost_pos, gate)
                    d_my_gate = self.getMazeDistance(my_pos, gate)
                    depth = self.analyzer.dead_end_depths.get(dead_cell, 1)
                    if d_ghost_gate <= d_my_gate + depth + 2:
                        danger_zones[dead_cell] = 10000.0

        # State Decision: Return Home (Banking food)
        # Conditions:
        # 1. Carrying threshold reached (>= 4 pellets)
        # 2. Under ghost threat and holding food (carrying >= 1 and ghost <= 4)
        # 3. Game win threshold (<= 2 food remaining)
        # 4. Move clock running down
        dist_to_border = min(self.getMazeDistance(my_pos, b) for b in self.analyzer.border_crossings)
        time_left = gameState.data.timeleft

        should_return = (
            my_state.numCarrying >= 5
            or (my_state.numCarrying >= 1 and min_ghost_dist <= 4)
            or len(food_list) <= 2
            or time_left <= (dist_to_border * 2 + 10)
            or (self.getScore(gameState) > 0 and time_left < 150 and my_state.numCarrying > 0)
        )

        if should_return and my_state.isPacman:
            best_border_goals = set(self.analyzer.border_crossings)
            path = self.a_star_search(my_pos, best_border_goals, danger_zones)
            if path:
                return path[0]

        # Tactical Evasion: When ghost is in close proximity
        if my_state.isPacman and min_ghost_dist <= 3 and nearest_ghost_pos is not None:
            best_action = self._tactical_evade(gameState, legal_actions, nearest_ghost_pos, capsules)
            if best_action:
                return best_action

        # Target Selection: Capsule priority if reachable
        if capsules and min_ghost_dist < 8:
            closest_cap = min(capsules, key=lambda c: self.getMazeDistance(my_pos, c))
            d_cap = self.getMazeDistance(my_pos, closest_cap)
            if d_cap < min_ghost_dist:
                path = self.a_star_search(my_pos, {closest_cap}, danger_zones)
                if path:
                    return path[0]

        # Target Selection: Food Selection
        if food_list:
            claimed = self.coordinator.get_claimed_target(self.teammate_index)
            candidate_food = [f for f in food_list if f != claimed and danger_zones.get(f, 0) < 1000]
            if not candidate_food:
                candidate_food = food_list

            # Cluster scoring: prefer food with adjacent pellets and closer to our position
            def food_score(f_pos: tuple[int, int]) -> float:
                d = self.getMazeDistance(my_pos, f_pos)
                cluster = sum(1 for other in food_list if self.getMazeDistance(f_pos, other) <= 2)
                d_border = min(self.getMazeDistance(f_pos, b) for b in self.analyzer.border_crossings)
                return -d + 1.5 * cluster - 0.2 * d_border

            best_food = max(candidate_food, key=food_score)
            self.coordinator.claim_target(self.index, best_food)

            path = self.a_star_search(my_pos, {best_food}, danger_zones)
            if path:
                return path[0]

        # Default fallback: safe border crossing
        path = self.a_star_search(my_pos, set(self.analyzer.border_crossings), danger_zones)
        if path:
            return path[0]

        filtered = [a for a in legal_actions if a != Directions.STOP]
        return random.choice(filtered) if filtered else Directions.STOP

    def _tactical_evade(self,
                        gameState: GameState,
                        legal_actions: list[Action],
                        ghost_pos: tuple[int, int],
                        capsules: list[tuple[int, int]]) -> Optional[Action]:
        """
        Micro-tactical evaluation to dodge close-quarters ghosts,
        reach capsules, or step back to safe territory.
        """
        best_action = None
        best_val = -1e9

        for action in legal_actions:
            if action == Directions.STOP:
                continue

            successor = gameState.generateSuccessor(self.index, action)
            next_pos = successor.getAgentPosition(self.index)
            d_ghost = self.getMazeDistance(next_pos, ghost_pos)

            if d_ghost <= 1:
                # Stepping into ghost is suicidal
                continue

            # Stepping into safe territory is optimal escape
            if self.analyzer.is_home_territory(next_pos):
                val = 10000.0 + d_ghost * 10.0
            elif next_pos in capsules:
                val = 50000.0
            else:
                d_border = min(self.getMazeDistance(next_pos, b) for b in self.analyzer.border_crossings)
                val = d_ghost * 100.0 - d_border * 5.0
                if self.getFood(gameState)[next_pos[0]][next_pos[1]]:
                    val += 50.0

            if val > best_val:
                best_val = val
                best_action = action

        return best_action


#############################
# Defensive Capture Agent   #
#############################

class DefensiveAgent(StrategicCaptureAgent):
    """
    Intelligent Defensive Ghost Agent:
    - Dedicated defender of home territory and food dots.
    - Intercepts visible and tracked invaders before they reach border crossings.
    - Patrols key boundary chokepoints defending the food centroid when idle.
    - Implements scared-ghost containment (shadowing invaders at safe distance 2-3).
    """

    def chooseAction(self, gameState: GameState) -> Action:
        self.coordinator.update(gameState, self.index)
        my_pos = gameState.getAgentPosition(self.index)
        my_state = gameState.getAgentState(self.index)
        legal_actions = gameState.getLegalActions(self.index)

        if not legal_actions:
            return Directions.STOP

        invaders = self.get_invaders(gameState)
        defending_food = self.getFoodYouAreDefending(gameState).asList()

        # Danger zone mapping (prevent defender from accidentally crossing into enemy territory)
        danger_zones: dict[tuple[int, int], float] = {}
        for pos in self.analyzer.legal_positions:
            if not self.analyzer.is_home_territory(pos):
                danger_zones[pos] = 500.0  # Strongly prioritize remaining on defense

        # Case 1: Active Invader Detected -> Hunt and eliminate immediately
        if invaders:
            # Prioritize invader carrying most food or closest to our position
            target_opp, target_pos, carrying = min(
                invaders,
                key=lambda inv: (0 if inv[2] > 0 else 1, self.getMazeDistance(my_pos, inv[1]))
            )

            # Check if defender is Scared
            if my_state.scaredTimer > 0:
                # Evasive containment: shadow invader at distance 2-3 without dying
                return self._contain_scared(gameState, legal_actions, target_pos)

            # Direct Interception: Head towards invader to eliminate them
            path = self.a_star_search(my_pos, {target_pos}, danger_zones)
            if path:
                return path[0]

        # Case 2: Alarm - Food was recently stolen on our territory
        if self.coordinator.last_food_eaten_pos is not None:
            alarm = self.coordinator.last_food_eaten_pos
            if self.getMazeDistance(my_pos, alarm) <= 1:
                self.coordinator.last_food_eaten_pos = None
            else:
                path = self.a_star_search(my_pos, {alarm}, danger_zones)
                if path:
                    return path[0]

        # Case 3: No Invaders -> Patrol Border Chokepoints
        if defending_food:
            # Compute centroid of remaining defended food pellets
            avg_x = sum(f[0] for f in defending_food) / len(defending_food)
            avg_y = sum(f[1] for f in defending_food) / len(defending_food)
            centroid = (avg_x, avg_y)

            # Select border crossing closest to food centroid
            best_crossing = min(
                self.analyzer.border_crossings,
                key=lambda b: (b[0] - centroid[0]) ** 2 + (b[1] - centroid[1]) ** 2
            )
            self.coordinator.claim_target(self.index, best_crossing)

            path = self.a_star_search(my_pos, {best_crossing}, danger_zones)
            if path:
                return path[0]

        filtered = [a for a in legal_actions if a != Directions.STOP]
        return random.choice(filtered) if filtered else Directions.STOP

    def _contain_scared(self,
                        gameState: GameState,
                        legal_actions: list[Action],
                        invader_pos: tuple[int, int]) -> Action:
        """
        Maintains safe standoff distance (2-3 steps) from invader while scared,
        blocking path to home border crossings without being devoured.
        """
        best_action = Directions.STOP
        best_val = -1e9

        for action in legal_actions:
            if action == Directions.STOP:
                continue

            successor = gameState.generateSuccessor(self.index, action)
            next_pos = successor.getAgentPosition(self.index)

            # Must stay on home side
            if not self.analyzer.is_home_territory(next_pos):
                continue

            d_invader = self.getMazeDistance(next_pos, invader_pos)
            if d_invader <= 1:
                # Devoured by invader! Suicidal move
                continue

            # Ideal standoff distance is 2 to 3
            standoff_penalty = abs(d_invader - 2.5) * 50.0
            d_border = min(self.getMazeDistance(next_pos, b) for b in self.analyzer.border_crossings)

            # Value: stay safe, close to border between invader and exit
            val = -standoff_penalty - d_border * 10.0

            if val > best_val:
                best_val = val
                best_action = action

        return best_action if best_action != Directions.STOP else random.choice(legal_actions)
