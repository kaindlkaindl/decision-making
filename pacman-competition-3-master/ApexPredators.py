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
Team: ApexPredators (Matin & Gabriel)
Vak: Decision Making (Minor Autonome Systemen) - HvA / UvA

Dit is ons sterkste team. We combineren drie technieken:

1. Doolhofanalyse (MazeAnalyzer)
   Voor het spel begint zoeken we alle doodlopende gangen. Van elke cel
   onthouden we de ingang (gate) en de diepte. Zo weten we later of we een
   gang veilig in kunnen lopen of dat een spook ons kan insluiten.

2. Kansverdeling over de vijand (BeliefTracker)
   Buiten 5 vakjes zien we de tegenstander niet. We houden daarom per
   tegenstander een kansverdeling bij over alle vakjes. We updaten die met
   (a) de ruisachtige afstandsmeting, (b) het feit dat we hem binnen 5 vakjes
   zouden zien, (c) verdwenen eigen stippen en (d) zijn beweging per zet.

3. Planning met gevarenkosten (Dijkstra / A*)
   We rekenen kortste routes uit over het doolhof, maar vakjes bij een spook
   krijgen een hoge strafkost. Daardoor lopen we er automatisch omheen.
   Doelen kiezen we op basis van routekosten en afstand naar huis, en we
   houden ons doel vast (goal commitment) zodat we niet gaan oscilleren.

Rolverdeling: 1 aanvaller (OffensiveAgent) en 1 verdediger (DefensiveAgent).
Als we aan het eind van het spel achterstaan, wordt de verdediger ook aanvaller.
"""

from __future__ import annotations

import heapq
import os
import random
from collections import defaultdict
from typing import Optional

from captureAgents import CaptureAgent
from game import Directions
from util import manhattanDistance

DIRS = [(Directions.NORTH, (0, 1)), (Directions.SOUTH, (0, -1)),
        (Directions.EAST, (1, 0)), (Directions.WEST, (-1, 0))]

SIGHT = 5            # zichtbereik (Manhattan)
BLOCK = 1000.0       # strafkost voor vakjes waar we direct gepakt worden
SCARED_ROUNDS = 40   # hoe lang een tegenstander bang blijft na een capsule


#################
# Team creation #
#################

def createTeam(firstIndex: int,
               secondIndex: int,
               isRed: bool,
               first: str = 'OffensiveAgent',
               second: str = 'DefensiveAgent',
               **kwargs) -> list[CaptureAgent]:
    """Maakt het team: 1 aanvaller en 1 verdediger."""
    return [globals().get(first, OffensiveAgent)(firstIndex),
            globals().get(second, DefensiveAgent)(secondIndex)]


###################
# Maze analysis   #
###################

class MazeAnalyzer:
    """
    Doolhofanalyse die we eenmalig bij de start doen.

    - cells / nbrs: alle vrije vakjes en hun buren.
    - Dead-end pruning: we halen steeds cellen met hooguit 1 buur weg. Wat
      weggehaald wordt is een doodlopende gang. Van elke zo'n cel bewaren we
      de ingang (gate = eerste cel die blijft staan) en de diepte (aantal
      stappen tot die ingang).
    """

    def __init__(self, walls):
        self.width = walls.width
        self.height = walls.height
        self.walls = walls
        self.cells = [(x, y) for x in range(self.width) for y in range(self.height)
                      if not walls[x][y]]
        cellset = set(self.cells)
        self.nbrs = {}
        for (x, y) in self.cells:
            self.nbrs[(x, y)] = [(x + dx, y + dy) for _, (dx, dy) in DIRS
                                 if (x + dx, y + dy) in cellset]
        self.gate = {}
        self.depth = {}
        self._prune()

    def _prune(self):
        alive = set(self.cells)
        deg = {c: len(self.nbrs[c]) for c in self.cells}
        stack = [c for c in self.cells if deg[c] <= 1]
        parent = {}
        while stack:
            c = stack.pop()
            if c not in alive:
                continue
            alive.discard(c)
            live = [n for n in self.nbrs[c] if n in alive]
            if live:
                p = live[0]
                parent[c] = p
                deg[p] -= 1
                if deg[p] <= 1:
                    stack.append(p)
        for c in parent:
            cur, d = c, 0
            seen = 0
            while cur in parent and seen < 500:
                cur = parent[cur]
                d += 1
                seen += 1
            if cur in alive:          # alleen echte gangen met een ingang
                self.gate[c] = cur
                self.depth[c] = d

    def dijkstra(self, start, extra_cost):
        """Kortste route met kosten 1 + gevarenkosten per betreden vakje."""
        dist = {start: 0.0}
        prev = {}
        heap = [(0.0, start)]
        while heap:
            d, c = heapq.heappop(heap)
            if d > dist.get(c, 1e18):
                continue
            for n in self.nbrs[c]:
                nd = d + 1.0 + extra_cost.get(n, 0.0)
                if nd < dist.get(n, 1e18):
                    dist[n] = nd
                    prev[n] = c
                    heapq.heappush(heap, (nd, n))
        return dist, prev


###################
# Belief tracker  #
###################

class BeliefTracker:
    """
    Kansverdeling B(s) over de positie van een tegenstander.
    Elke beurt: (1) elapse (hij zet een stap), (2) observe (nieuwe informatie).
    """

    def __init__(self, maze: MazeAnalyzer, start):
        self.maze = maze
        self.p = {start: 1.0}

    def elapse(self):
        new = defaultdict(float)
        for s, pr in self.p.items():
            options = self.maze.nbrs[s] + [s]
            share = pr / len(options)
            for o in options:
                new[o] += share
        self.p = dict(new)

    def set_point(self, s):
        self.p = {s: 1.0}

    def observe(self, visible, my_pos, team_positions, noisy, gameState):
        if visible is not None:
            self.p = {(int(visible[0]), int(visible[1])): 1.0}
            return

        def allowed(s):
            return all(manhattanDistance(t, s) > SIGHT for t in team_positions)

        def likelihood(s):
            if noisy is None:
                return 1.0
            return gameState.getDistanceProb(manhattanDistance(my_pos, s), noisy)

        new = {}
        for s, pr in self.p.items():
            if not allowed(s):
                continue
            w = likelihood(s)
            if w > 0:
                new[s] = pr * w
        if not new:        # we zaten er naast: opnieuw beginnen vanuit de meting
            for s in self.maze.cells:
                if allowed(s):
                    w = likelihood(s)
                    if w > 0:
                        new[s] = w
        if not new:
            new = {s: 1.0 for s in self.maze.cells}
        total = sum(new.values())
        self.p = {s: v / total for s, v in new.items()}

    def best(self):
        s = max(self.p, key=self.p.get)
        return s, self.p[s]


#####################
# Basis Agentklasse #
#####################

class ApexBaseAgent(CaptureAgent):
    """Gedeelde logica: grenzen, afstanden, beliefs, gevarenkosten en navigatie."""

    scare_end = -10 ** 9      # tijdstip (timeleft) waarop de vijand weer gevaarlijk wordt
    targets = {}              # gekozen voedseldoel per agent (voor teamcoordinatie)

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        walls = gameState.getWalls()
        self.walls = walls
        self.width = walls.width
        self.height = walls.height
        self.mid_x = self.width // 2
        self.home_x = (self.mid_x - 1) if self.red else self.mid_x
        self.enemy_x = self.mid_x if self.red else (self.mid_x - 1)
        self.maze = MazeAnalyzer(walls)

        self.border_crossings = [
            (self.home_x, y) for y in range(self.height)
            if not walls[self.home_x][y] and not walls[self.enemy_x][y]
        ]
        if not self.border_crossings:
            self.border_crossings = [(self.home_x, y) for y in range(self.height)
                                     if not walls[self.home_x][y]]
        self.border_crossings.sort(key=lambda b: b[1])

        self.start = gameState.getAgentPosition(self.index)
        self.opponents = self.getOpponents(gameState)
        self.beliefs = {o: BeliefTracker(self.maze, gameState.getInitialAgentPosition(o))
                        for o in self.opponents}
        self.last_food = set(self.getFoodYouAreDefending(gameState).asList())
        self.last_caps = list(self.getCapsules(gameState))
        self.history = []
        self.current_target = None
        self.alarm_pos = None
        self.alarm_age = 0
        self.wait_count = 0
        ApexBaseAgent.scare_end = -10 ** 9
        ApexBaseAgent.targets = {}

    # ---------- kleine hulpfuncties ----------

    def is_home(self, pos) -> bool:
        return pos[0] < self.mid_x if self.red else pos[0] >= self.mid_x

    def dist(self, a, b) -> int:
        return self.getMazeDistance((int(a[0]), int(a[1])), (int(b[0]), int(b[1])))

    def my_moves_left(self, gameState) -> int:
        return gameState.data.timeleft // 4

    def scared_rounds_left(self, gameState) -> int:
        return max(0, (gameState.data.timeleft - ApexBaseAgent.scare_end) // 4)

    # ---------- informatie bijwerken ----------

    def update_info(self, gameState):
        """Werkt beliefs, capsule-timer en positiegeschiedenis bij (elke beurt)."""
        me = gameState.getAgentPosition(self.index)
        team_pos = [gameState.getAgentPosition(i) for i in self.getTeam(gameState)]
        noisy_all = gameState.getAgentDistances()

        # capsule door ons opgegeten? Dan zijn de tegenstanders 40 rondes bang.
        caps = list(self.getCapsules(gameState))
        for c in self.last_caps:
            if c not in caps and c in team_pos:
                ApexBaseAgent.scare_end = gameState.data.timeleft - 4 * SCARED_ROUNDS
        self.last_caps = caps

        # eigen verdwenen stippen: daar stond zojuist een indringer
        cur_food = set(self.getFoodYouAreDefending(gameState).asList())
        eaten = self.last_food - cur_food
        self.last_food = cur_food

        for b in self.beliefs.values():
            b.elapse()
        for s in eaten:
            opp = max(self.beliefs, key=lambda o: self.beliefs[o].p.get(s, 0.0))
            self.beliefs[opp].set_point(s)
            self.alarm_pos = s
            self.alarm_age = 0
        for o, b in self.beliefs.items():
            noisy = noisy_all[o] if noisy_all else None
            b.observe(gameState.getAgentPosition(o), me, team_pos, noisy, gameState)

        self.history.append(me)
        if len(self.history) > 10:
            self.history.pop(0)
        self.alarm_age += 1

    def get_threats(self, gameState):
        """Lijst (positie, gewicht) van gevaarlijke spoken: zichtbaar = 1.0, geschat = 0.6."""
        threats = []
        scared_left = self.scared_rounds_left(gameState)
        for o in self.opponents:
            st = gameState.getAgentState(o)
            pos = st.getPosition()
            if pos is not None:
                if not st.isPacman and st.scaredTimer <= 3:
                    threats.append(((int(pos[0]), int(pos[1])), 1.0))
            elif scared_left <= 6:
                est, conf = self.beliefs[o].best()
                if conf >= 0.3 and not self.is_home(est):
                    threats.append((est, 0.6))
        return threats

    def build_cost(self, me, threats, scale=1.0):
        """Strafkosten per vakje op vijandelijk gebied rond spoken en in valkuil-gangen."""
        cost = {}
        base = {0: BLOCK, 1: BLOCK, 2: 60.0, 3: 20.0, 4: 6.0}
        for c in self.maze.cells:
            if self.is_home(c):
                continue
            extra = 0.0
            for g, w in threats:
                d = self.dist(g, c)
                extra += base.get(d, 0.0) * w
                if c in self.maze.gate:
                    gate = self.maze.gate[c]
                    depth = self.maze.depth[c]
                    # veilig als wij de gang uit zijn voordat het spook bij de ingang kan zijn
                    if self.dist(g, gate) <= self.dist(me, gate) + 2 * depth + 1:
                        extra += 600.0 * w
            if extra:
                cost[c] = extra * scale
        return cost

    # ---------- bewegen ----------

    def step_towards(self, gameState, prev, start, target) -> Optional[str]:
        if target == start:
            return None
        legal = gameState.getLegalActions(self.index)
        cur = target
        for _ in range(1000):
            p = prev.get(cur)
            if p is None:
                return None
            if p == start:
                break
            cur = p
        dx, dy = cur[0] - start[0], cur[1] - start[1]
        for a, (ax, ay) in DIRS:
            if (ax, ay) == (dx, dy) and a in legal:
                return a
        return None

    def greedy_action(self, gameState, target, home_only=False, keep_away=None):
        """Kies de zet die het dichtst bij target komt (gebruikt voor de verdediger)."""
        legal = [a for a in gameState.getLegalActions(self.index) if a != Directions.STOP]
        best, best_val = None, 1e18
        for a in legal:
            nxt = gameState.generateSuccessor(self.index, a).getAgentPosition(self.index)
            if home_only and not self.is_home(nxt):
                continue
            val = self.dist(nxt, target)
            if val < best_val:
                best, best_val = a, val
        if best is None:
            best = legal[0] if legal else Directions.STOP
        return best

    def safe_fallback(self, gameState):
        legal = gameState.getLegalActions(self.index)
        moving = [a for a in legal if a != Directions.STOP]
        return random.choice(moving) if moving else Directions.STOP

    def is_oscillating(self) -> bool:
        h = self.history
        return len(h) >= 8 and len(set(h[-8:])) <= 2

    # ---------- aanvallen (ook gebruikt door de verdediger in noodgeval) ----------

    def attack(self, gameState, partner_mode=False):
        me = gameState.getAgentPosition(self.index)
        st = gameState.getAgentState(self.index)
        carrying = st.numCarrying
        food = self.getFood(gameState).asList()
        caps = self.getCapsules(gameState)
        moves_left = self.my_moves_left(gameState)

        threats = self.get_threats(gameState)
        # Zonder buit op zak is doodgaan goedkoop: dan durven we meer (voorkomt patstelling)
        scale = 1.0 if carrying > 0 else 0.3
        if carrying == 0 and self.wait_count >= 8:
            scale = 0.05
        cost = self.build_cost(me, threats, scale)
        dist_map, prev = self.maze.dijkstra(me, cost)

        homes = [b for b in self.border_crossings if b in dist_map]
        best_home = min(homes, key=lambda b: dist_map[b]) if homes else self.start
        home_steps = self.dist(me, best_home)

        dg = min([self.dist(me, g) for g, w in threats if w >= 1.0], default=999)
        dg_est = min([self.dist(me, g) for g, w in threats if w < 1.0], default=999)
        scared_left = self.scared_rounds_left(gameState)

        # ---- beslissing: naar huis? ----
        limit = 5
        if scared_left > 12:
            limit = 8
        near_food = min([dist_map.get(f, 1e9) for f in food], default=1e9)
        if not threats and near_food <= 2 and scared_left <= 12:
            limit = 6
        return_home = carrying > 0 and (
            carrying >= limit
            or dg <= 6
            or dg_est <= 4
            or len(food) <= 2
            or moves_left <= home_steps + 3
        )

        target = None
        if return_home:
            target = best_home
            self.current_target = None
        else:
            # ---- capsule als er een spook in de buurt is ----
            if caps and threats and scared_left <= 6:
                reach = [(dist_map.get(c, 1e9), c) for c in caps]
                dcap, cap = min(reach)
                if dcap < 700 and dcap <= 14 and (dg > 900 or dcap <= dg + 3):
                    target = cap
            # ---- voedsel kiezen met goal commitment ----
            if target is None and food:
                w_home = 0.3 + 0.2 * carrying
                mate_target = None
                for idx, t in ApexBaseAgent.targets.items():
                    if idx != self.index:
                        mate_target = t
                best_f, best_s = None, 1e18
                for f in food:
                    d = dist_map.get(f)
                    if d is None:
                        continue
                    s = d + w_home * min(self.dist(f, b) for b in self.border_crossings)
                    if f == self.current_target:
                        s -= 3.0
                    if partner_mode and mate_target is not None and self.dist(f, mate_target) <= 4:
                        s += 6.0
                    if s < best_s:
                        best_f, best_s = f, s
                if best_f is not None and dist_map[best_f] < 700:
                    target = best_f
                    self.current_target = best_f
                elif carrying > 0:
                    target = best_home
            if target is None:
                target = best_home if carrying > 0 else None
        ApexBaseAgent.targets[self.index] = self.current_target
        self.wait_count = self.wait_count + 1 if target is None else 0
        action = None
        if target is not None:
            action = self.step_towards(gameState, prev, me, target)

        if target is None or action is None:
            # niets veiligs te halen: wacht bij de grens (of ga naar huis)
            action = self.step_towards(gameState, prev, me, best_home)
            if action is None:
                action = Directions.STOP if Directions.STOP in gameState.getLegalActions(self.index) \
                    else self.safe_fallback(gameState)

        if self.is_oscillating() and not threats and carrying == 0:
            self.current_target = None
            return self.safe_fallback(gameState)
        return action

    # ---------- verdedigen ----------

    def defend(self, gameState):
        me = gameState.getAgentPosition(self.index)
        st = gameState.getAgentState(self.index)

        invaders = []
        for o in self.opponents:
            s = gameState.getAgentState(o)
            p = s.getPosition()
            if p is not None and s.isPacman:
                invaders.append(((int(p[0]), int(p[1])), s.numCarrying))

        if invaders:
            self.alarm_pos = None
            target = min(invaders, key=lambda ic: self.dist(me, ic[0]))[0]
            if st.scaredTimer > 0:
                return self.scared_block(gameState, target)
            return self.greedy_action(gameState, target, home_only=True)

        # geen indringer zichtbaar: gebruik de kansverdeling
        best_mass, best_cell = 0.0, None
        for o in self.opponents:
            b = self.beliefs[o]
            mass = sum(pr for s, pr in b.p.items() if self.is_home(s))
            if mass > best_mass:
                home_cells = {s: pr for s, pr in b.p.items() if self.is_home(s)}
                best_mass, best_cell = mass, max(home_cells, key=home_cells.get)
        if best_cell is not None and best_mass >= 0.5:
            if self.dist(me, best_cell) <= 1 and st.scaredTimer <= 0:
                pass
            else:
                return self.greedy_action(gameState, best_cell, home_only=True)

        if self.alarm_pos is not None and self.alarm_age < 25:
            if self.dist(me, self.alarm_pos) <= 1:
                self.alarm_pos = None
            else:
                return self.greedy_action(gameState, self.alarm_pos, home_only=True)

        patrol = self.patrol_point(gameState)
        if me == patrol:
            legal = gameState.getLegalActions(self.index)
            return Directions.STOP if Directions.STOP in legal else self.safe_fallback(gameState)
        return self.greedy_action(gameState, patrol, home_only=True)

    def scared_block(self, gameState, invader):
        """Als wij bang zijn blijven we op ~2.5 stappen afstand en blokkeren we de weg."""
        legal = [a for a in gameState.getLegalActions(self.index) if a != Directions.STOP]
        best, best_score = None, -1e18
        fallback, far = None, -1
        for a in legal:
            nxt = gameState.generateSuccessor(self.index, a).getAgentPosition(self.index)
            if not self.is_home(nxt):
                continue
            d = self.dist(nxt, invader)
            if d > far:
                fallback, far = a, d
            if d >= 2 and -abs(d - 2.5) > best_score:
                best, best_score = a, -abs(d - 2.5)
        if best is not None:
            return best
        return fallback if fallback is not None else self.safe_fallback(gameState)

    def patrol_point(self, gameState):
        """Staan op de grensdoorgang waar de vijand het meest waarschijnlijk binnenkomt."""
        defended = list(self.getFoodYouAreDefending(gameState).asList())
        ests = []
        for o in self.opponents:
            est, conf = self.beliefs[o].best()
            if not self.is_home(est) and conf >= 0.05:
                ests.append(est)
        if ests:
            # het meest dichtbije vermoedelijke vijandelijke aanvalspunt bij onze grens
            def cross_cost(b):
                return min(self.dist(e, b) for e in ests)
            return min(self.border_crossings, key=cross_cost)
        if not defended:
            return self.border_crossings[len(self.border_crossings) // 2]
        avg_y = sum(f[1] for f in defended) / len(defended)
        return min(self.border_crossings, key=lambda b: abs(b[1] - avg_y))


###################
# Offensive Agent #
###################

class OffensiveAgent(ApexBaseAgent):
    """Aanvaller: haalt stippen met gevarenkosten-routes en brengt ze veilig terug."""

    def chooseAction(self, gameState):
        try:
            self.update_info(gameState)
            return self.attack(gameState)
        except Exception:
            _debug_trace()
            return self.safe_fallback(gameState)


###################
# Defensive Agent #
###################

class DefensiveAgent(ApexBaseAgent):
    """
    Verdediger: onderschept indringers, volgt de kansverdeling bij mist en
    patrouilleert bij de grens. Staan we aan het eind achter, dan helpt hij mee
    met aanvallen.
    """

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self.attack_mode = False

    def chooseAction(self, gameState):
        try:
            self.update_info(gameState)
            st = gameState.getAgentState(self.index)
            score = self.getScore(gameState)
            moves_left = self.my_moves_left(gameState)

            invader_visible = any(
                gameState.getAgentState(o).isPacman and gameState.getAgentState(o).getPosition() is not None
                for o in self.opponents)
            if not self.attack_mode and score < 0 and moves_left <= 90 and not invader_visible:
                self.attack_mode = True
            if self.attack_mode and score >= 0 and st.numCarrying == 0 and not st.isPacman:
                self.attack_mode = False
            if self.attack_mode:
                return self.attack(gameState, partner_mode=True)
            return self.defend(gameState)
        except Exception:
            _debug_trace()
            return self.safe_fallback(gameState)


def _debug_trace():
    import os
    if os.environ.get('APEX_DEBUG'):
        import traceback
        traceback.print_exc()

