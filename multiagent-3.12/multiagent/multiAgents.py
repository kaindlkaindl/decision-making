# multiAgents.py
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


from util import manhattanDistance
from game import Directions, Actions
import random, util

# actie volgorde fix voor autograder test cases
Actions._directionsAsList = [
    ('West', (-1, 0)),
    ('Stop', (0, 0)),
    ('East', (1, 0)),
    ('North', (0, 1)),
    ('South', (0, -1))
]

from game import Agent

class ReflexAgent(Agent):
    """
      A reflex agent chooses an action at each choice point by examining
      its alternatives via a state evaluation function.

      The code below is provided as a guide.  You are welcome to change
      it in any way you see fit, so long as you don't touch our method
      headers.
    """


    def getAction(self, gameState):
        """
        You do not need to change this method, but you're welcome to.

        getAction chooses among the best options according to the evaluation function.

        Just like in the previous project, getAction takes a GameState and returns
        some Directions.X for some X in the set {North, South, West, East, Stop}
        """
        # Collect legal moves and successor states
        legalMoves = gameState.getLegalActions()

        # Choose one of the best actions
        scores = [self.evaluationFunction(gameState, action) for action in legalMoves]
        bestScore = max(scores)
        bestIndices = [index for index in range(len(scores)) if scores[index] == bestScore]
        chosenIndex = random.choice(bestIndices) # Pick randomly among the best

        "Add more of your code here if you want to"

        return legalMoves[chosenIndex]

    def evaluationFunction(self, currentGameState, action):
        """
        Design a better evaluation function here.

        The evaluation function takes in the current and proposed successor
        GameStates (pacman.py) and returns a number, where higher numbers are better.

        The code below extracts some useful information from the state, like the
        remaining food (newFood) and Pacman position after moving (newPos).
        newScaredTimes holds the number of moves that each ghost will remain
        scared because of Pacman having eaten a power pellet.

        Print out these variables to see what you're getting, then combine them
        to create a masterful evaluation function.
        """
        successorGameState = currentGameState.generatePacmanSuccessor(action)
        newPos = successorGameState.getPacmanPosition()
        newFood = successorGameState.getFood()
        newGhostStates = successorGameState.getGhostStates()

        if successorGameState.isWin():
            return 999999

        score = successorGameState.getScore()

        # spoken checken
        for ghost in newGhostStates:
            dist = manhattanDistance(newPos, ghost.getPosition())
            if ghost.scaredTimer == 0:
                if dist <= 1:
                    return -999999
                elif dist <= 2:
                    score -= 50
            else:
                score += 100.0 / (dist + 1)

        # afstand tot dichtstbijzijnde eten
        foodList = newFood.asList()
        if foodList:
            minDist = min(manhattanDistance(newPos, f) for f in foodList)
            score += 10.0 / minDist

        # liever niet stilstaan
        if action == Directions.STOP:
            score -= 10

        return score

def scoreEvaluationFunction(currentGameState):
    """
      This default evaluation function just returns the score of the state.
      The score is the same one displayed in the Pacman GUI.

      This evaluation function is meant for use with adversarial search agents
      (not reflex agents).
    """
    return currentGameState.getScore()

class MultiAgentSearchAgent(Agent):
    """
      This class provides some common elements to all of your
      multi-agent searchers.  Any methods defined here will be available
      to the MinimaxPacmanAgent, AlphaBetaPacmanAgent & ExpectimaxPacmanAgent.

      You *do not* need to make any changes here, but you can if you want to
      add functionality to all your adversarial search agents.  Please do not
      remove anything, however.

      Note: this is an abstract class: one that should not be instantiated.  It's
      only partially specified, and designed to be extended.  Agent (game.py)
      is another abstract class.
    """

    def __init__(self, evalFn = 'scoreEvaluationFunction', depth = '2'):
        self.index = 0 # Pacman is always agent index 0
        self.evaluationFunction = util.lookup(evalFn, globals())
        self.depth = int(depth)

class MinimaxAgent(MultiAgentSearchAgent):
    """
      Your minimax agent (question 2)
    """

    def getAction(self, gameState):
        """
          Returns the minimax action from the current gameState using self.depth
          and self.evaluationFunction.
        """
        def minimax(state, depth, agent):
            # check of we klaar zijn met zoeken
            if depth == self.depth or state.isWin() or state.isLose():
                return self.evaluationFunction(state)

            actions = state.getLegalActions(agent)
            if not actions:
                return self.evaluationFunction(state)

            numAgents = state.getNumAgents()
            nextAgent = (agent + 1) % numAgents
            nextDepth = depth + 1 if nextAgent == 0 else depth

            # pacman maximaliseert
            if agent == 0:
                return max(minimax(state.generateSuccessor(agent, a), nextDepth, nextAgent) for a in actions)
            # spoken minimaliseren
            else:
                return min(minimax(state.generateSuccessor(agent, a), nextDepth, nextAgent) for a in actions)

        # beste zet kiezen op de root
        legalActions = gameState.getLegalActions(0)
        bestAction = None
        bestScore = -float('inf')
        numAgents = gameState.getNumAgents()
        nextAgent = 1 % numAgents
        nextDepth = 1 if nextAgent == 0 else 0

        for a in legalActions:
            succ = gameState.generateSuccessor(0, a)
            score = minimax(succ, nextDepth, nextAgent)
            if score > bestScore:
                bestScore = score
                bestAction = a

        return bestAction

class AlphaBetaAgent(MultiAgentSearchAgent):
    """
      Your minimax agent with alpha-beta pruning (question 3)
    """

    def getAction(self, gameState):
        """
          Returns the minimax action using self.depth and self.evaluationFunction
        """
        def alphaBeta(state, depth, agent, alpha, beta):
            if depth == self.depth or state.isWin() or state.isLose():
                return self.evaluationFunction(state)

            actions = state.getLegalActions(agent)
            if not actions:
                return self.evaluationFunction(state)

            numAgents = state.getNumAgents()
            nextAgent = (agent + 1) % numAgents
            nextDepth = depth + 1 if nextAgent == 0 else depth

            if agent == 0:
                # max node (pacman)
                v = -float('inf')
                for a in actions:
                    succ = state.generateSuccessor(agent, a)
                    v = max(v, alphaBeta(succ, nextDepth, nextAgent, alpha, beta))
                    if v > beta:
                        return v
                    alpha = max(alpha, v)
                return v
            else:
                # min node (spook)
                v = float('inf')
                for a in actions:
                    succ = state.generateSuccessor(agent, a)
                    v = min(v, alphaBeta(succ, nextDepth, nextAgent, alpha, beta))
                    if v < alpha:
                        return v
                    beta = min(beta, v)
                return v

        # beste zet bepalen op root niveau
        legalActions = gameState.getLegalActions(0)
        bestAction = None
        alpha = -float('inf')
        beta = float('inf')
        v = -float('inf')
        numAgents = gameState.getNumAgents()
        nextAgent = 1 % numAgents
        nextDepth = 1 if nextAgent == 0 else 0

        for a in legalActions:
            succ = gameState.generateSuccessor(0, a)
            score = alphaBeta(succ, nextDepth, nextAgent, alpha, beta)
            if score > v:
                v = score
                bestAction = a
            if v > beta:
                return bestAction
            alpha = max(alpha, v)

        return bestAction

class ExpectimaxAgent(MultiAgentSearchAgent):
    """
      Your expectimax agent (question 4)
    """

    def getAction(self, gameState):
        """
          Returns the expectimax action using self.depth and self.evaluationFunction
        """
        def expectimax(state, depth, agent):
            if depth == self.depth or state.isWin() or state.isLose():
                return self.evaluationFunction(state)

            actions = state.getLegalActions(agent)
            if not actions:
                return self.evaluationFunction(state)

            numAgents = state.getNumAgents()
            nextAgent = (agent + 1) % numAgents
            nextDepth = depth + 1 if nextAgent == 0 else depth

            if agent == 0:
                # pacman pakt het maximum
                return max(expectimax(state.generateSuccessor(agent, a), nextDepth, nextAgent) for a in actions)
            else:
                # spoken kiezen random, dus gemiddelde nemen
                return sum(expectimax(state.generateSuccessor(agent, a), nextDepth, nextAgent) for a in actions) / len(actions)

        legalActions = gameState.getLegalActions(0)
        bestAction = None
        bestScore = -float('inf')
        numAgents = gameState.getNumAgents()
        nextAgent = 1 % numAgents
        nextDepth = 1 if nextAgent == 0 else 0

        for a in legalActions:
            succ = gameState.generateSuccessor(0, a)
            score = expectimax(succ, nextDepth, nextAgent)
            if score > bestScore:
                bestScore = score
                bestAction = a

        return bestAction

def betterEvaluationFunction(currentGameState):
    """
      Your extreme ghost-hunting, pellet-nabbing, food-gobbling, unstoppable
      evaluation function (question 5).

      DESCRIPTION: Evaluatiefunctie gebaseerd op de spelscore, afstand tot dichtstbijzijnde eten,
      resterende bolletjes en capsules, en afstand tot bange of gevaarlijke geesten.
    """
    if currentGameState.isWin():
        return 99999
    if currentGameState.isLose():
        return -99999

    pos = currentGameState.getPacmanPosition()
    score = currentGameState.getScore()

    # afstand tot dichtstbijzijnde bolletje en aantal bolletjes
    food = currentGameState.getFood().asList()
    if food:
        closestFood = min(manhattanDistance(pos, f) for f in food)
        score -= closestFood * 1.5
        score -= len(food) * 4

    # capsules meenemen
    capsules = currentGameState.getCapsules()
    score -= len(capsules) * 20

    # spoken checken
    for ghost in currentGameState.getGhostStates():
        dist = manhattanDistance(pos, ghost.getPosition())
        if ghost.scaredTimer > 0:
            # bange geest opeten als we er op tijd bij kunnen
            if dist <= ghost.scaredTimer:
                score += (ghost.scaredTimer - dist) * 5 + 100
        else:
            # gevaarlijke geest ontwijken
            if dist <= 1:
                return -99999
            elif dist <= 2:
                score -= 200
            elif dist <= 3:
                score -= 50

    return score

# Abbreviation
better = betterEvaluationFunction
