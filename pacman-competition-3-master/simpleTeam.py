# simpleTeam.py
# -------------
# Ons simpele, overzichtelijke team voor Pacman Capture The Flag.
#
# Waarom we dit zo hebben gebouwd:
# We wilden een team dat betrouwbaar wint van de baseline, maar tegelijkertijd
# zó simpel is dat we elke beslissing tijdens een replay binnen 1 minuut kunnen
# uitleggen. Daarom gebruiken we voor beide agents een simpele toestand-automaat
# (State Machine) met vaste regels, en rekenen we routes uit met getMazeDistance.
#
# Rolverdeling:
# - Agent 1 (SimpleOffenseAgent): haalt stippen aan de overkant en brengt ze terug.
# - Agent 2 (SimpleDefenseAgent): blijft op onze helft om indringers te pakken.

import random
from captureAgents import CaptureAgent
from game import Directions


def createTeam(firstIndex: int,
               secondIndex: int,
               isRed: bool,
               first: str = 'SimpleOffenseAgent',
               second: str = 'SimpleDefenseAgent',
               **kwargs) -> list[CaptureAgent]:
    """
    Hier maken we ons team aan: één vaste aanvaller en één vaste verdediger.
    We houden de rollen gescheiden zodat ze elkaar niet in de weg lopen en
    we precies weten wie waarvoor verantwoordelijk is.
    """
    return [globals()[first](firstIndex), globals()[second](secondIndex)]


class SimpleBaseAgent(CaptureAgent):
    """
    Basis-agent waar onze aanvaller en verdediger van erven.
    Hierin zetten we dingen klaar die we allebei nodig hebben: waar de
    middenlijn ligt, waar de doorgangen zijn en hoe we naar een doel lopen.
    """

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self.start = gameState.getAgentPosition(self.index)
        walls = gameState.getWalls()
        self.width = walls.width
        self.height = walls.height

        # We bepalen eerst welke x-coördinaat nog net op onze eigen helft ligt
        # (home_x) en welke net aan de overkant ligt (enemy_x).
        # Rood speelt links (x < mid_x), blauw speelt rechts (x >= mid_x).
        mid_x = self.width // 2
        self.home_x = (mid_x - 1) if self.red else mid_x
        self.enemy_x = mid_x if self.red else (mid_x - 1)

        # We zoeken alle open doorgangen op de grens waar geen muur staat aan
        # onze kant én geen muur aan de kant van de tegenstander.
        self.border_crossings = [
            (self.home_x, y) for y in range(self.height)
            if not walls[self.home_x][y] and not walls[self.enemy_x][y]
        ]
        # Mocht een rare kaart geen directe doorgang hebben, dan pakken we
        # alle open vakjes langs onze grenslijn als terugvaloptie.
        if not self.border_crossings:
            self.border_crossings = [
                (self.home_x, y) for y in range(self.height)
                if not walls[self.home_x][y]
            ]

    def is_home(self, pos):
        """Geeft True terug als een vakje op onze eigen helft van het bord ligt."""
        mid_x = self.width // 2
        return pos[0] < mid_x if self.red else pos[0] >= mid_x

    def get_best_action_towards(self, gameState, target_pos, avoid_positions=None):
        """
        Kiest de zet die ons het dichtst bij het doel (target_pos) brengt.

        We kijken voor elke legale zet (behalve stilstaan) waar we terechtkomen
        en pakken de zet met de kleinste doolhofafstand naar ons doel.
        Vakjes die in avoid_positions staan (zoals vlak naast een spook) slaan
        we over, zodat we niet zomaar een spook inlopen.
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

            # Als dit vakje gevaarlijk is (bijv. naast een spook), slaan we hem over.
            if next_pos in avoid_positions:
                continue

            dist = self.getMazeDistance(next_pos, target_pos)
            if dist < min_dist:
                min_dist = dist
                best_action = action

        # Als we helemaal geen veilige zet meer hebben (we zitten bijvoorbeeld
        # ingesloten), kiezen we alsnog de zet die ons het dichtst bij ons doel brengt.
        if best_action is None:
            best_action = min(
                moving_actions,
                key=lambda a: self.getMazeDistance(
                    gameState.generateSuccessor(self.index, a).getAgentPosition(self.index),
                    target_pos
                )
            )

        return best_action


class SimpleOffenseAgent(SimpleBaseAgent):
    """
    Onze aanvalsagent. Deze werkt volgens drie simpele toestanden (op volgorde van prioriteit):

    1. TERUG NAAR HUIS (RETREAT):
       Als we genoeg stippen bij ons hebben of als er gevaar dreigt, rennen we terug
       over de grens om onze punten veilig te stellen.
    2. KRACHTCAPSULE PAKKEN (CAPSULE):
       Als er een spook in de buurt zit en er ligt een capsule dichterbij dan dat spook,
       pakken we eerst de capsule zodat we veilig zijn.
    3. STIPPEN ETEN (COLLECT):
       In alle andere gevallen lopen we naar de dichtstbijzijnde stip om die op te eten.
    """

    def chooseAction(self, gameState):
        my_pos = gameState.getAgentPosition(self.index)
        my_state = gameState.getAgentState(self.index)
        food_list = self.getFood(gameState).asList()
        capsules = self.getCapsules(gameState)

        # We kijken welke tegenstanders we kunnen zien (binnen 5 stappen) en die
        # op dit moment een gevaarlijk spook zijn (dus geen Pacman en niet bang/scared).
        opponents = [gameState.getAgentState(i) for i in self.getOpponents(gameState)]
        scary_ghosts = [
            opp.getPosition() for opp in opponents
            if not opp.isPacman and opp.getPosition() is not None and opp.scaredTimer <= 2
        ]

        # Hoever is het dichtstbijzijnde gevaarlijke spook van ons vandaan?
        ghost_dist = min([self.getMazeDistance(my_pos, g) for g in scary_ghosts], default=999)

        # We zetten het vakje van elk gevaarlijk spook én de 4 vakjes direct eromheen
        # op onze verboden lijst. Zo lopen we er met een boogje omheen.
        forbidden_cells = set()
        for g_pos in scary_ghosts:
            forbidden_cells.add(g_pos)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                forbidden_cells.add((g_pos[0] + dx, g_pos[1] + dy))

        # ------------------------------------------------------------------
        # TOESTAND 1: TERUG NAAR HUIS (Score veiligstellen)
        # ------------------------------------------------------------------
        # We kiezen bewust om al bij 3 stippen terug te gaan: beter vaak kleine
        # beetjes veilig inleveren dan te hebberig worden en alles kwijtraken.
        # We gaan ook terug als:
        # - we minstens 1 stip hebben en een spook op <= 4 stappen nadert,
        # - er nog maar 2 stippen op het bord liggen (dan winnen we het potje direct),
        # - de tijd bijna op is en we nog stippen op zak hebben.
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

        # ------------------------------------------------------------------
        # TOESTAND 2: KRACHTCAPSULE PAKKEN
        # ------------------------------------------------------------------
        # Als een spook ons opjaagt (afstand < 6), maar een krachtcapsule ligt
        # dichterbij dan het spook, halen we die capsule zodat de spoken bang worden.
        if capsules and ghost_dist < 6:
            nearest_capsule = min(capsules, key=lambda c: self.getMazeDistance(my_pos, c))
            if self.getMazeDistance(my_pos, nearest_capsule) < ghost_dist:
                return self.get_best_action_towards(gameState, nearest_capsule, forbidden_cells)

        # ------------------------------------------------------------------
        # TOESTAND 3: DICHTSTBIJZIJNDE STIP ETEN
        # ------------------------------------------------------------------
        if food_list:
            nearest_food = min(food_list, key=lambda f: self.getMazeDistance(my_pos, f))
            return self.get_best_action_towards(gameState, nearest_food, forbidden_cells)

        # Als er geen stippen meer zijn, lopen we gewoon terug naar de grens.
        nearest_border = min(self.border_crossings, key=lambda b: self.getMazeDistance(my_pos, b))
        return self.get_best_action_towards(gameState, nearest_border)


class SimpleDefenseAgent(SimpleBaseAgent):
    """
    Onze verdedigingsagent. Deze werkt ook met drie duidelijke toestanden:

    1. ONDERSCHEPPEN (INTERCEPT):
       Zien we een vijand op onze helft? Dan jagen we direct op hem om hem op te eten.
       (Behalve als we zelf 'scared' zijn: dan houden we ~2.5 stappen afstand.)
    2. INBREKER ALARM (ALARM):
       Omdat we door de mist tegenstanders pas binnen 5 vakjes zien, onthouden we
       elke beurt hoeveel eigen stippen we nog hebben. Verdwijnt er een stip? Dan
       weten we dat daar net iemand liep en gaan we direct kijken.
    3. GRENS BEWAKEN (PATROL):
       Is er niets aan de hand? Dan wachten we bij de middelste doorgang op de grens.
    """

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        # We slaan bij de start al ons eigen voedsel op, zodat we elke beurt kunnen
        # zien of er ergens een stip is opgegeten.
        self.last_defending_food = set(self.getFoodYouAreDefending(gameState).asList())
        self.alarm_pos = None

    def chooseAction(self, gameState):
        my_pos = gameState.getAgentPosition(self.index)
        my_state = gameState.getAgentState(self.index)
        defending_food = set(self.getFoodYouAreDefending(gameState).asList())

        # We vergelijken ons huidige voedsel met de vorige beurt.
        # Als er een stip weg is, zetten we een alarm op de dichtstbijzijnde verdwenen stip.
        missing_food = self.last_defending_food - defending_food
        if missing_food:
            self.alarm_pos = min(missing_food, key=lambda p: self.getMazeDistance(my_pos, p))
        self.last_defending_food = defending_food

        # We kijken of we een vijandelijke Pacman op onze helft zien.
        opponents = [gameState.getAgentState(i) for i in self.getOpponents(gameState)]
        invaders = [
            opp.getPosition() for opp in opponents
            if opp.isPacman and opp.getPosition() is not None
        ]

        # ------------------------------------------------------------------
        # TOESTAND 1: INDRINGER GEVONDEN -> ONDERSCHEPPEN
        # ------------------------------------------------------------------
        if invaders:
            target_invader = min(invaders, key=lambda inv: self.getMazeDistance(my_pos, inv))
            # Nu we hem zien, hebben we het oude voedsel-alarm niet meer nodig.
            self.alarm_pos = None

            # Als de tegenstander een krachtcapsule heeft gegeten, zijn we 'scared'.
            # Als we hem dan aanraken gaan wij dood en zijn we terug bij af.
            # Daarom blijven we op onze eigen helft op ~2.5 stappen afstand hangen
            # tot onze timer afloopt, zodat we hem blijven hinderen zonder dood te gaan.
            if my_state.scaredTimer > 0:
                legal_actions = gameState.getLegalActions(self.index)
                best_act = Directions.STOP
                best_score = -9999
                fallback_act = Directions.STOP
                max_safe_dist = -1

                for a in legal_actions:
                    if a == Directions.STOP:
                        continue
                    nxt = gameState.generateSuccessor(self.index, a).getAgentPosition(self.index)
                    # Als verdediger willen we niet per ongeluk zelf de grens oversteken.
                    if not self.is_home(nxt):
                        continue
                    d = self.getMazeDistance(nxt, target_invader)
                    if d > max_safe_dist:
                        max_safe_dist = d
                        fallback_act = a
                    if d >= 2:
                        score = -abs(d - 2.5)
                        if score > best_score:
                            best_score = score
                            best_act = a

                return best_act if best_act != Directions.STOP else fallback_act

            # Niet scared? Dan vol erop af om de indringer te pakken!
            return self.get_best_action_towards(gameState, target_invader)

        # ------------------------------------------------------------------
        # TOESTAND 2: INBREKER ALARM (Er is net een stip verdwenen)
        # ------------------------------------------------------------------
        if self.alarm_pos is not None:
            if self.getMazeDistance(my_pos, self.alarm_pos) <= 1:
                # We zijn aangekomen op de plek van de verdwenen stip: alarm wissen.
                self.alarm_pos = None
            else:
                return self.get_best_action_towards(gameState, self.alarm_pos)

        # ------------------------------------------------------------------
        # TOESTAND 3: PATROUILLEER DE GRENS
        # ------------------------------------------------------------------
        # Geen indringers en geen alarm: we gaan bij de middelste doorgang staan.
        central_border = self.border_crossings[len(self.border_crossings) // 2]
        return self.get_best_action_towards(gameState, central_border)
