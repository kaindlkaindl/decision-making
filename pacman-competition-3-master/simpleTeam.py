# simpleTeam.py
# -------------
# Team: Simpele FSM Pacman (Eenvoudig, Begrijpelijk en Betrouwbaar)
# Geschikt voor een gegarandeerde 'Voldoende' die in 2 minuten glashelder uit te leggen is.
#
# Werking:
# - Werkt met een State Machine (Toestand-automaat) met duidelijke regels:
#   * Aanvaller: Eet stippen -> Breng terug bij >= 3 stippen of gevaar -> Vermijd spoken.
#   * Verdediger: Jaag op indringers -> Onderzoek verdwenen stippen -> Patrouilleer de grens.
# - Gebruikt ingebouwde getMazeDistance voor de kortste routes.

import random
from captureAgents import CaptureAgent
from game import Directions


def createTeam(firstIndex: int,
               secondIndex: int,
               isRed: bool,
               first: str = 'SimpleOffenseAgent',
               second: str = 'SimpleDefenseAgent',
               **kwargs) -> list[CaptureAgent]:
    """Maakt het simpele team aan: 1 duidelijke aanvaller en 1 duidelijke verdediger."""
    return [globals()[first](firstIndex), globals()[second](secondIndex)]


class SimpleBaseAgent(CaptureAgent):
    """Basisklasse met handige hulpfuncties voor grensberekeningen en navigatie."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self.start = gameState.getAgentPosition(self.index)
        walls = gameState.getWalls()
        self.width = walls.width
        self.height = walls.height

        # Bepaal de grenslijn (de middenlijn waar we veilig zijn)
        mid_x = self.width // 2
        self.home_x = (mid_x - 1) if self.red else mid_x
        self.enemy_x = mid_x if self.red else (mid_x - 1)

        # Zoek alle doorgangen op de grens
        self.border_crossings = [
            (self.home_x, y) for y in range(self.height)
            if not walls[self.home_x][y] and not walls[self.enemy_x][y]
        ]
        if not self.border_crossings:
            self.border_crossings = [(self.home_x, y) for y in range(self.height) if not walls[self.home_x][y]]

    def is_home(self, pos):
        """Geeft True terug als de positie op onze eigen helft ligt."""
        mid_x = self.width // 2
        return pos[0] < mid_x if self.red else pos[0] >= mid_x

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

            # Sla gevaarlijke vakjes over (bijv. vlak voor een spook)
            if next_pos in avoid_positions:
                continue

            dist = self.getMazeDistance(next_pos, target_pos)
            if dist < min_dist:
                min_dist = dist
                best_action = action

        # Als alle veilige zetten op zijn, kies dan de minst slechte actie
        if best_action is None:
            best_action = min(
                moving_actions,
                key=lambda a: self.getMazeDistance(gameState.generateSuccessor(self.index, a).getAgentPosition(self.index), target_pos)
            )

        return best_action


class SimpleOffenseAgent(SimpleBaseAgent):
    """
    Aanvalsagent die werkt volgens 3 heldere regels:
    1. RETREAT: Hebben we >= 3 stippen of dreigt er gevaar? Ren terug naar de grens om te scoren!
    2. CAPSULE: Ligt er een krachtcapsule vlakbij? Eet die op om spoken ongevaarlijk te maken.
    3. COLLECT: Zoek de dichtstbijzijnde stip en eet die op.
    """

    def chooseAction(self, gameState):
        my_pos = gameState.getAgentPosition(self.index)
        my_state = gameState.getAgentState(self.index)
        food_list = self.getFood(gameState).asList()
        capsules = self.getCapsules(gameState)

        # Bekijk zichtbare vijandelijke geesten die NIET bang (scared) zijn
        opponents = [gameState.getAgentState(i) for i in self.getOpponents(gameState)]
        scary_ghosts = [
            opp.getPosition() for opp in opponents
            if not opp.isPacman and opp.getPosition() is not None and opp.scaredTimer <= 2
        ]

        # Bereken afstand tot dichtstbijzijnde actieve spook
        ghost_dist = min([self.getMazeDistance(my_pos, g) for g in scary_ghosts], default=999)

        # Markeer vakjes pal naast een spook als verboden terrein
        forbidden_cells = set()
        for g_pos in scary_ghosts:
            forbidden_cells.add(g_pos)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                forbidden_cells.add((g_pos[0] + dx, g_pos[1] + dy))

        # TOESTAND 1: TERUG NAAR HUIS (Score veiligstellen)
        # We gaan terug als:
        # - We minstens 3 stippen dragen
        # - We minstens 1 stip dragen én een spook nadert (< 5 stappen)
        # - Er nog maar 2 stippen over zijn (wedstrijd bijna gewonnen)
        # - De tijd bijna op is
        time_left = getattr(gameState.data, 'timeleft', 1200)
        dist_to_border = min(self.getMazeDistance(my_pos, b) for b in self.border_crossings)

        should_retreat = (
            my_state.numCarrying >= 3
            or (my_state.numCarrying >= 1 and ghost_dist <= 4)
            or len(food_list) <= 2
            or (time_left < dist_to_border * 2 + 10 and my_state.numCarrying > 0)
        )

        if should_retreat and my_state.isPacman:
            nearest_border = min(self.border_crossings, key=lambda b: self.getMazeDistance(my_pos, b))
            return self.get_best_action_towards(gameState, nearest_border, forbidden_cells)

        # TOESTAND 2: KRACHTCAPSULE PAKKEN
        if capsules and ghost_dist < 6:
            nearest_capsule = min(capsules, key=lambda c: self.getMazeDistance(my_pos, c))
            if self.getMazeDistance(my_pos, nearest_capsule) < ghost_dist:
                return self.get_best_action_towards(gameState, nearest_capsule, forbidden_cells)

        # TOESTAND 3: DICHTSTBIJZIJNDE STIP ETEN
        if food_list:
            nearest_food = min(food_list, key=lambda f: self.getMazeDistance(my_pos, f))
            return self.get_best_action_towards(gameState, nearest_food, forbidden_cells)

        # Noodplan: ga naar de grens
        nearest_border = min(self.border_crossings, key=lambda b: self.getMazeDistance(my_pos, b))
        return self.get_best_action_towards(gameState, nearest_border)


class SimpleDefenseAgent(SimpleBaseAgent):
    """
    Verdedigingsagent die werkt volgens 3 heldere regels:
    1. INTERCEPT: Zien we een vijand op onze helft? Ren er direct op af om hem te pakken!
    2. ALARM: Is er net een stip van ons verdwenen? Ren direct naar die plek (de inbreker was daar!).
    3. PATROL: Niemand te zien? Bewaak de centrale doorgang op de grenslijn.
    """

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self.last_defending_food = set(self.getFoodYouAreDefending(gameState).asList())
        self.alarm_pos = None

    def chooseAction(self, gameState):
        my_pos = gameState.getAgentPosition(self.index)
        my_state = gameState.getAgentState(self.index)
        defending_food = set(self.getFoodYouAreDefending(gameState).asList())

        # Controleer of er zojuist een stip van ons is opgegeten (inbreker alarm!)
        missing_food = self.last_defending_food - defending_food
        if missing_food:
            self.alarm_pos = list(missing_food)[0]
        self.last_defending_food = defending_food

        # Zoek zichtbare indringers op onze helft
        opponents = [gameState.getAgentState(i) for i in self.getOpponents(gameState)]
        invaders = [
            opp.getPosition() for opp in opponents
            if opp.isPacman and opp.getPosition() is not None
        ]

        # TOESTAND 1: INDRINGER GEVONDEN -> ONDERSCHEPPEN
        if invaders:
            target_invader = min(invaders, key=lambda inv: self.getMazeDistance(my_pos, inv))
            self.alarm_pos = None

            # Als wij 'scared' zijn (vijand heeft capsule), val niet roekeloos aan
            if my_state.scaredTimer > 0:
                # Blijf op 2 stappen afstand (blokkeer de weg, maar ga niet dood)
                legal_actions = gameState.getLegalActions(self.index)
                best_act = Directions.STOP
                best_score = -9999
                for a in legal_actions:
                    if a == Directions.STOP:
                        continue
                    nxt = gameState.generateSuccessor(self.index, a).getAgentPosition(self.index)
                    if not self.is_home(nxt):
                        continue
                    d = self.getMazeDistance(nxt, target_invader)
                    if d >= 2:
                        score = -abs(d - 2.5)
                        if score > best_score:
                            best_score = score
                            best_act = a
                return best_act if best_act != Directions.STOP else random.choice(legal_actions)

            return self.get_best_action_towards(gameState, target_invader)

        # TOESTAND 2: INBREKER ALARM (Eten verdwenen)
        if self.alarm_pos is not None:
            if self.getMazeDistance(my_pos, self.alarm_pos) <= 1:
                self.alarm_pos = None  # Plek geïnspecteerd
            else:
                return self.get_best_action_towards(gameState, self.alarm_pos)

        # TOESTAND 3: PATROUILLEER DE GRENS
        # Patrouilleer rondom de middelste grensovergang
        central_border = self.border_crossings[len(self.border_crossings) // 2]
        return self.get_best_action_towards(gameState, central_border)

