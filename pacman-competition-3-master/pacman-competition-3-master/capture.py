# capture.py
# ----------
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


# capture.py
# ----------
# Licensing Information: Please do not distribute or publish solutions to this
# project. You are free to use and extend these projects for educational
# purposes. The Pacman AI projects were developed at UC Berkeley, primarily by
# John DeNero (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# For more info, see http://inst.eecs.berkeley.edu/~cs188/sp09/pacman.html

"""
Capture.py holds the logic for Pacman capture the flag.

  (i)  Your interface to the pacman world:
          Pacman is a complex environment.  You probably don't want to
          read through all of the code we wrote to make the game runs
          correctly.  This section contains the parts of the code
          that you will need to understand in order to complete the
          project.  There is also some code in game.py that you should
          understand.

  (ii)  The hidden secrets of pacman:
          This section contains all of the logic code that the pacman
          environment uses to decide who can move where, who dies when
          things collide, etc.  You shouldn't need to read this section
          of code, but you can if you want.

  (iii) Framework to start a game:
          The final section contains the code for reading the command
          you use to set up the game, then starting up a new game, along with
          linking in all the external parts (agent functions, graphics).
          Check this section out to see all the options available to you.

To play your first game, type 'python capture.py' from the command line.
The keys are
  P1: 'a', 's', 'd', and 'w' to move
  P2: 'l', ';', ',' and 'p' to move
"""
import importlib.util
import importlib.machinery
import random
import sys
import time
from typing import Any
from typing import Self
from typing import TYPE_CHECKING

import keyboardAgents
import mazeGenerator
from game import Actions
from game import Agent
from game import Configuration
from game import Game
from game import GameStateData
from game import Grid
from layout import Layout
from util import manhattanDistance
from util import nearestPoint

if TYPE_CHECKING:
  from game import Action
  from game import AgentState
  from textDisplay import Graphics


# If you change these, you won't affect the server, so you can't cheat
KILL_POINTS = 0
SONAR_NOISE_RANGE = 13 # Must be odd
SONAR_NOISE_VALUES = [i - (SONAR_NOISE_RANGE - 1)/2 for i in range(SONAR_NOISE_RANGE)]
SIGHT_RANGE = 5 # Manhattan distance
MIN_FOOD = 2
TOTAL_FOOD = 60

DUMP_FOOD_ON_DEATH = True # if we have the gameplay element that dumps dots on death

SCARED_TIME = 40

def noisyDistance(pos1: tuple[int, int], pos2: tuple[int, int]) -> int:
  return int(manhattanDistance(pos1, pos2) + random.choice(SONAR_NOISE_VALUES))

###################################################
# YOUR INTERFACE TO THE PACMAN WORLD: A GameState #
###################################################

class GameState:
  """
  A GameState specifies the full game state, including the food, capsules,
  agent configurations and score changes.

  GameStates are used by the Game object to capture the actual state of the game and
  can be used by agents to reason about the game.

  Much of the information in a GameState is stored in a GameStateData object.  We
  strongly suggest that you access that data via the accessor methods below rather
  than referring to the GameStateData object directly.
  """

  ####################################################
  # Accessor methods: use these to access state data #
  ####################################################

  def getLegalActions(self, agentIndex: int = 0) -> list['Action']:
    """
    Returns the legal actions for the agent specified.
    """
    return AgentRules.getLegalActions(self, agentIndex)

  def generateSuccessor(self, agentIndex: int, action: 'Action') -> Self:
    """
    Returns the successor state (a GameState object) after the specified agent takes the action.
    """
    # Copy current state
    state = GameState(self)

    # Find appropriate rules for the agent
    AgentRules.applyAction( state, action, agentIndex )
    AgentRules.checkDeath(state, agentIndex)
    AgentRules.decrementTimer(state.data.agentStates[agentIndex])

    # Book keeping
    state.data._agentMoved = agentIndex
    state.data.score += state.data.scoreChange
    state.data.timeleft = self.data.timeleft - 1
    return state

  def getAgentState(self, index: int) -> 'AgentState':
    return self.data.agentStates[index]

  def getAgentPosition(self, index: int) -> tuple[int, int]:
    """
    Returns a location tuple if the agent with the given index is observable;
    if the agent is unobservable, returns None.
    """
    agentState = self.data.agentStates[index]
    ret = agentState.getPosition()
    if ret:
      return tuple(int(x) for x in ret)
    return ret

  def getNumAgents(self) -> int:
    return len(self.data.agentStates)

  def getScore(self) -> int:
    """
    Returns a number corresponding to the current score.
    """
    return self.data.score

  def getRedFood(self) -> Grid:
    """
    Returns a matrix of food that corresponds to the food on the red team's side.
    For the matrix m, m[x][y]=true if there is food in (x,y) that belongs to
    red (meaning red is protecting it, blue is trying to eat it).
    """
    return halfGrid(self.data.food, red = True)

  def getBlueFood(self) -> Grid:
    """
    Returns a matrix of food that corresponds to the food on the blue team's side.
    For the matrix m, m[x][y]=true if there is food in (x,y) that belongs to
    blue (meaning blue is protecting it, red is trying to eat it).
    """
    return halfGrid(self.data.food, red = False)

  def getRedCapsules(self) -> list[tuple[int, int]]:
    return halfList(self.data.capsules, self.data.food, red = True)

  def getBlueCapsules(self) -> list[tuple[int, int]]:
    return halfList(self.data.capsules, self.data.food, red = False)

  def getWalls(self) -> Grid:
    """
    Just like getFood but for walls
    """
    return self.data.layout.walls

  def hasFood(self, x: int, y: int) -> bool:
    """
    Returns true if the location (x,y) has food, regardless of
    whether it's blue team food or red team food.
    """
    return self.data.food[x][y]

  def hasWall(self, x: int, y: int) -> bool:
    """
    Returns true if (x,y) has a wall, false otherwise.
    """
    return self.data.layout.walls[x][y]

  def isOver(self) -> bool:
    return self.data._win

  def getRedTeamIndices(self) -> list[int]:
    """
    Returns a list of agent index numbers for the agents on the red team.
    """
    return self.redTeam[:]

  def getBlueTeamIndices(self) -> list[int]:
    """
    Returns a list of the agent index numbers for the agents on the blue team.
    """
    return self.blueTeam[:]

  def isOnRedTeam(self, agentIndex: int) -> bool:
    """
    Returns true if the agent with the given agentIndex is on the red team.
    """
    return self.teams[agentIndex]

  def getAgentDistances(self) -> list[int] | None:
    """
    Returns a noisy distance to each agent.
    """
    if 'agentDistances' in dir(self) :
      return self.agentDistances
    else:
      return None

  def getDistanceProb(self, trueDistance: int, noisyDistance: int) -> float:
    "Returns the probability of a noisy distance given the true distance"
    if noisyDistance - trueDistance in SONAR_NOISE_VALUES:
      return 1.0/SONAR_NOISE_RANGE
    else:
      return 0

  def getInitialAgentPosition(self, agentIndex: int) -> tuple[int, int]:
    "Returns the initial position of an agent."
    return self.data.layout.agentPositions[agentIndex][1]

  def getCapsules(self) -> list[tuple[int, int]]:
    """
    Returns a list of positions (x,y) of the remaining capsules.
    """
    return self.data.capsules

  #############################################
  #             Helper methods:               #
  # You shouldn't need to call these directly #
  #############################################

  def __init__(self, prevState: Self | None = None):
    """
    Generates a new state by copying information from its predecessor.
    """
    if prevState != None: # Initial state
      self.data: GameStateData = GameStateData(prevState.data)
      self.blueTeam: list[int] = prevState.blueTeam
      self.redTeam: list[int] = prevState.redTeam
      self.data.timeleft: int = prevState.data.timeleft

      self.teams = prevState.teams
      self.agentDistances = prevState.agentDistances
    else:
      self.data = GameStateData()
      self.agentDistances = []

  def deepCopy( self ):
    state = GameState( self )
    state.data = self.data.deepCopy()
    state.data.timeleft = self.data.timeleft

    state.blueTeam = self.blueTeam[:]
    state.redTeam = self.redTeam[:]
    state.teams = self.teams[:]
    state.agentDistances = self.agentDistances[:]
    return state

  def makeObservation(self, index: int) -> Self:
    state = self.deepCopy()

    # Adds the sonar signal
    pos = state.getAgentPosition(index)
    n = state.getNumAgents()
    distances = [noisyDistance(pos, state.getAgentPosition(i)) for i in range(n)]
    state.agentDistances = distances

    # Remove states of distant opponents
    if index in self.blueTeam:
      team = self.blueTeam
      otherTeam = self.redTeam
    else:
      otherTeam = self.blueTeam
      team = self.redTeam

    for enemy in otherTeam:
      seen = False
      enemyPos = state.getAgentPosition(enemy)
      for teammate in team:
        if manhattanDistance(enemyPos, state.getAgentPosition(teammate)) <= SIGHT_RANGE:
          seen = True
      if not seen: state.data.agentStates[enemy].configuration = None
    return state

  def __eq__( self, other ) -> bool:
    """
    Allows two states to be compared.
    """
    if other == None: return False
    return self.data == other.data

  def __hash__( self ):
    """
    Allows states to be keys of dictionaries.
    """
    return int(hash( self.data ))

  def __str__( self ):

    return str(self.data)

  def initialize( self, layout: Layout, numAgents: int):
    """
    Creates an initial game state from a layout array (see layout.py).
    """
    self.data.initialize(layout, numAgents)
    positions = [a.configuration for a in self.data.agentStates]
    self.blueTeam: list[tuple[int, tuple[int, int]]] = [i for i,p in enumerate(positions) if not self.isRed(p)]
    self.redTeam: list[tuple[int, tuple[int, int]]] = [i for i,p in enumerate(positions) if self.isRed(p)]
    self.teams: list[bool] = [self.isRed(p) for p in positions]
    #This is usually 60 (always 60 with random maps)
    #However, if layout map is specified otherwise, it could be less
    global TOTAL_FOOD
    TOTAL_FOOD = layout.totalFood

  def isRed(self, configOrPos: Configuration | tuple[int, int]) -> bool:
    width = self.data.layout.width
    if type(configOrPos) == type( (0,0) ):
      return configOrPos[0] < width // 2
    else:
      return configOrPos.pos[0] < width // 2

def halfGrid(grid: Grid, red: bool) -> Grid:
  halfway = grid.width // 2
  halfgrid = Grid(grid.width, grid.height, False)
  if red:    xrange = range(halfway)
  else:       xrange = range(halfway, grid.width)

  for y in range(grid.height):
    for x in xrange:
      if grid[x][y]: halfgrid[x][y] = True

  return halfgrid

def halfList(l: list[tuple[int, int]], grid: Grid, red: bool) -> list:
  halfway = grid.width // 2
  newList = []
  for x,y in l:
    if red and x <= halfway: newList.append((x,y))
    elif not red and x > halfway: newList.append((x,y))
  return newList

############################################################################
#                     THE HIDDEN SECRETS OF PACMAN                         #
#                                                                          #
# You shouldn't need to look through the code in this section of the file. #
############################################################################

COLLISION_TOLERANCE = 0.7 # How close ghosts must be to Pacman to kill

class CaptureRules:
  """
  These game rules manage the control flow of a game, deciding when
  and how the game starts and ends.
  """

  def __init__(self, quiet: bool = False):
    self.quiet = quiet

  def newGame(self,
              layout: Layout,
              agents: list[Agent],
              display: 'Graphics',
              length: int,
              muteAgents: bool,
              catchExceptions: bool) -> Game:
    initState = GameState()
    initState.initialize( layout, len(agents) )
    starter = random.randint(0,1)
    print('%s team starts' % ['Red', 'Blue'][starter])
    game = Game(agents, display, self, startingIndex=starter, muteAgents=muteAgents, catchExceptions=catchExceptions)
    game.state = initState
    game.length = length
    game.state.data.timeleft = length
    if 'drawCenterLine' in dir(display):
      display.drawCenterLine()
    self._initBlueFood = initState.getBlueFood().count()
    self._initRedFood = initState.getRedFood().count()
    return game

  def process(self, state: GameState, game: Game) -> None:
    """
    Checks to see whether it is time to end the game.
    """
    if 'moveHistory' in dir(game):
      if len(game.moveHistory) == game.length:
        state.data._win = True

    if state.isOver():
      game.gameOver = True
      if not game.rules.quiet:
        redCount = 0
        blueCount = 0
        foodToWin = (TOTAL_FOOD/2) - MIN_FOOD
        for index in range(state.getNumAgents()):
          agentState = state.data.agentStates[index]
          if index in state.getRedTeamIndices():
            redCount += agentState.numReturned
          else:
            blueCount += agentState.numReturned
        
        if blueCount >= foodToWin:#state.getRedFood().count() == MIN_FOOD:
          print ('The Blue team has returned at least %d of the opponents\' dots.' % foodToWin)
        elif redCount >= foodToWin:#state.getBlueFood().count() == MIN_FOOD:
          print ('The Red team has returned at least %d of the opponents\' dots.' % foodToWin)
        else:#if state.getBlueFood().count() > MIN_FOOD and state.getRedFood().count() > MIN_FOOD:
          print ('Time is up.')
          if state.data.score == 0: print ('Tie game!')
          else:
            winner = 'Red'
            if state.data.score < 0: winner = 'Blue'
            print ('The %s team wins by %d points.' % (winner, abs(state.data.score)))

  def getProgress(self, game: Game) -> float:
    blue = 1.0 - (game.state.getBlueFood().count() / float(self._initBlueFood))
    red = 1.0 - (game.state.getRedFood().count() / float(self._initRedFood))
    moves = len(self.moveHistory) / float(game.length)

    # return the most likely progress indicator, clamped to [0, 1]
    return min(max(0.75 * max(red, blue) + 0.25 * moves, 0.0), 1.0)

  def agentCrash(self, game: Game, agentIndex: int) -> None:
    if agentIndex % 2 == 0:
      print ("Red agent crashed", file=sys.stderr)
      game.state.data.score = -1
    else:
      print ("Blue agent crashed", file=sys.stderr)
      game.state.data.score = 1

  def getMaxTotalTime(self, agentIndex: int) -> int:
    return 900  # Move limits should prevent this from ever happening

  def getMaxStartupTime(self, agentIndex: int) -> int:
    return 15 # 15 seconds for registerInitialState

  def getMoveWarningTime(self, agentIndex: int) -> int:
    return 1  # One second per move

  def getMoveTimeout(self, agentIndex: int) -> int:
    return 3  # Three seconds results in instant forfeit

  def getMaxTimeWarnings(self, agentIndex: int) -> int:
    return 2  # Third violation loses the game

class AgentRules:
  """
  These functions govern how each agent interacts with her environment.
  """

  @staticmethod
  def getLegalActions(state: GameState, agentIndex: int) -> list['Action']:
    """
    Returns a list of legal actions (which are both possible & allowed)
    """
    agentState = state.getAgentState(agentIndex)
    conf = agentState.configuration
    possibleActions = Actions.getPossibleActions( conf, state.data.layout.walls )
    return AgentRules.filterForAllowedActions( agentState, possibleActions)

  @staticmethod
  def filterForAllowedActions(agentState: 'AgentState', possibleActions: list['Action']) -> list['Action']:
    return possibleActions


  @staticmethod
  def applyAction(state: GameState, action: 'Action', agentIndex: int) -> None:
    """
    Edits the state to reflect the results of the action.
    """
    legal = AgentRules.getLegalActions( state, agentIndex )
    if action not in legal:
      raise Exception("Illegal action " + str(action))

    # Update Configuration
    agentState = state.data.agentStates[agentIndex]
    speed = 1.0
    # if agentState.isPacman: speed = 0.5
    vector = Actions.directionToVector( action, speed )
    oldConfig = agentState.configuration
    agentState.configuration = oldConfig.generateSuccessor( vector )

    # Eat
    next = agentState.configuration.getPosition()
    nearest = nearestPoint( next )

    if next == nearest:
      isRed = state.isOnRedTeam(agentIndex)
      # Change agent type
      agentState.isPacman = [isRed, state.isRed(agentState.configuration)].count(True) == 1
      # if he's no longer pacman, he's on his own side, so reset the num carrying timer
      #agentState.numCarrying *= int(agentState.isPacman)
      if agentState.numCarrying > 0 and not agentState.isPacman:
        score = agentState.numCarrying if isRed else -1*agentState.numCarrying
        state.data.scoreChange += score

        agentState.numReturned += agentState.numCarrying
        agentState.numCarrying = 0

        redCount = 0
        blueCount = 0
        for index in range(state.getNumAgents()):
          agentState = state.data.agentStates[index]
          if index in state.getRedTeamIndices():
            redCount += agentState.numReturned
          else:
            blueCount += agentState.numReturned
        if redCount >= (TOTAL_FOOD/2) - MIN_FOOD or blueCount >= (TOTAL_FOOD/2) - MIN_FOOD:
          state.data._win = True


    if agentState.isPacman and manhattanDistance( nearest, next ) <= 0.9 :
      AgentRules.consume( nearest, state, state.isOnRedTeam(agentIndex) )


  @staticmethod
  def consume(position: tuple[int, int], state: GameState, isRed: bool) -> None:
    x,y = position
    # Eat food
    if state.data.food[x][y]:

      # blue case is the default
      teamIndicesFunc = state.getBlueTeamIndices
      score = -1
      if isRed:
        # switch if its red
        score = 1
        teamIndicesFunc = state.getRedTeamIndices

      # go increase the variable for the pacman who ate this
      agents = [state.data.agentStates[agentIndex] for agentIndex in teamIndicesFunc()]
      for agent in agents:
        if agent.getPosition() == position:
          agent.numCarrying += 1
          break # the above should only be true for one agent...

      # do all the score and food grid maintainenace 
      #state.data.scoreChange += score
      state.data.food = state.data.food.copy()
      state.data.food[x][y] = False
      state.data._foodEaten = position
      #if (isRed and state.getBlueFood().count() == MIN_FOOD) or (not isRed and state.getRedFood().count() == MIN_FOOD):
      #  state.data._win = True

    # Eat capsule
    if isRed: myCapsules = state.getBlueCapsules()
    else: myCapsules = state.getRedCapsules()
    if( position in myCapsules ):
      state.data.capsules.remove( position )
      state.data._capsuleEaten = position

      # Reset all ghosts' scared timers
      if isRed: otherTeam = state.getBlueTeamIndices()
      else: otherTeam = state.getRedTeamIndices()
      for index in otherTeam:
        state.data.agentStates[index].scaredTimer = SCARED_TIME


  @staticmethod
  def decrementTimer(state: GameState) -> None:
    timer = state.scaredTimer
    if timer == 1:
      state.configuration.pos = nearestPoint( state.configuration.pos )
    state.scaredTimer = max( 0, timer - 1 )

  @staticmethod
  def dumpFoodFromDeath(state: GameState, agentState: 'AgentState', agentIndex: int) -> None:
    if not (DUMP_FOOD_ON_DEATH):
      # this feature is not turned on
      return

    if not agentState.isPacman:
      raise Exception('something is seriously wrong, this agent isnt a pacman!')

    # ok so agentState is this:
    if (agentState.numCarrying == 0):
      return
    
    # first, score changes!
    # we HACK pack that ugly bug by just determining if its red based on the first position
    # to die...
    dummyConfig = Configuration(agentState.getPosition(), 'North')
    isRed = state.isRed(dummyConfig)

    # the score increases if red eats dots, so if we are refunding points,
    # the direction should be -1 if the red agent died, which means he dies
    # on the blue side
    scoreDirection = (-1)**(int(isRed) + 1)
    #state.data.scoreChange += scoreDirection * agentState.numCarrying

    def onRightSide(state: GameState, x: int, y: int) -> bool:
      dummyConfig = Configuration((x, y), 'North')
      return state.isRed(dummyConfig) == isRed

    # we have food to dump
    # -- expand out in BFS. Check:
    #   - that it's within the limits
    #   - that it's not a wall
    #   - that no other agents are there
    #   - that no power pellets are there
    #   - that it's on the right side of the grid
    def allGood(state: GameState, x: int, y: int) -> bool:
      width, height = state.data.layout.width, state.data.layout.height
      food, walls = state.data.food, state.data.layout.walls

      # bounds check
      if x >= width or y >= height or x <= 0 or y <= 0:
        return False

      if walls[x][y]:
        return False
      if food[x][y]:
        return False

      # dots need to be on the side where this agent will be a pacman :P
      if not onRightSide(state, x, y):
        return False

      if (x,y) in state.data.capsules:
        return False

      # loop through agents
      agentPoses = [state.getAgentPosition(i) for i in range(state.getNumAgents())]
      if (x,y) in agentPoses:
        return False

      return True

    numToDump = agentState.numCarrying
    state.data.food = state.data.food.copy()
    foodAdded = []

    def genSuccessors(x: int, y: int) -> list[tuple[int, int]]:
      DX = [-1, 0, 1]
      DY = [-1, 0, 1]
      return [(x + dx, y + dy) for dx in DX for dy in DY]

    # BFS graph search
    positionQueue = [agentState.getPosition()]
    seen = set()
    while numToDump > 0:
      if not len(positionQueue):
        raise Exception('Exhausted BFS! uh oh')
      # pop one off, graph check
      popped = positionQueue.pop(0)
      if popped in seen:
        continue
      seen.add(popped)

      x, y = popped[0], popped[1]
      x = int(x)
      y = int(y)
      if (allGood(state, x, y)):
        state.data.food[x][y] = True
        foodAdded.append((x, y))
        numToDump -= 1

      # generate successors
      positionQueue = positionQueue + genSuccessors(x, y)

    state.data._foodAdded = foodAdded
    # now our agentState is no longer carrying food
    agentState.numCarrying = 0
    pass


  @staticmethod
  def checkDeath(state: GameState, agentIndex: int) -> None:
    agentState = state.data.agentStates[agentIndex]
    if state.isOnRedTeam(agentIndex):
      otherTeam = state.getBlueTeamIndices()
    else:
      otherTeam = state.getRedTeamIndices()
    if agentState.isPacman:
      for index in otherTeam:
        otherAgentState = state.data.agentStates[index]
        if otherAgentState.isPacman: continue
        ghostPosition = otherAgentState.getPosition()
        if ghostPosition == None: continue
        if manhattanDistance( ghostPosition, agentState.getPosition() ) <= COLLISION_TOLERANCE:
          # award points to the other team for killing Pacmen
          if otherAgentState.scaredTimer <= 0:
            AgentRules.dumpFoodFromDeath(state, agentState, agentIndex)

            score = KILL_POINTS
            if state.isOnRedTeam(agentIndex):
              score = -score
            state.data.scoreChange += score
            agentState.isPacman = False
            agentState.configuration = agentState.start
            agentState.scaredTimer = 0
          else:
            score = KILL_POINTS
            if state.isOnRedTeam(agentIndex):
              score = -score
            state.data.scoreChange += score
            otherAgentState.isPacman = False
            otherAgentState.configuration = otherAgentState.start
            otherAgentState.scaredTimer = 0
    else: # Agent is a ghost
      for index in otherTeam:
        otherAgentState = state.data.agentStates[index]
        if not otherAgentState.isPacman: continue
        pacPos = otherAgentState.getPosition()
        if pacPos == None: continue
        if manhattanDistance( pacPos, agentState.getPosition() ) <= COLLISION_TOLERANCE:
          #award points to the other team for killing Pacmen
          if agentState.scaredTimer <= 0:
            AgentRules.dumpFoodFromDeath(state, otherAgentState, agentIndex)

            score = KILL_POINTS
            if not state.isOnRedTeam(agentIndex):
              score = -score
            state.data.scoreChange += score
            otherAgentState.isPacman = False
            otherAgentState.configuration = otherAgentState.start
            otherAgentState.scaredTimer = 0
          else:
            score = KILL_POINTS
            if state.isOnRedTeam(agentIndex):
              score = -score
            state.data.scoreChange += score
            agentState.isPacman = False
            agentState.configuration = agentState.start
            agentState.scaredTimer = 0

  @staticmethod
  def placeGhost(state: GameState, ghostState: 'AgentState') -> None:
    ghostState.configuration = ghostState.start

#############################
# FRAMEWORK TO START A GAME #
#############################

def default(str: str) -> str:
  return str + ' [Default: %default]'

def parseAgentArgs(str: str) -> str:
  if str == None or str == '': return {}
  pieces = str.split(',')
  opts = {}
  for p in pieces:
    if '=' in p:
      key, val = p.split('=')
    else:
      key,val = p, 1
    opts[key] = val
  return opts

def readCommand(argv: list[str]) -> dict[str, Any]:
  """
  Processes the command used to run pacman from the command line.
  """
  from optparse import OptionParser
  usageStr = """
  USAGE:      python pacman.py <options>
  EXAMPLES:   (1) python capture.py
                  - starts a game with two baseline agents
              (2) python capture.py --keys0
                  - starts a two-player interactive game where the arrow keys control agent 0, and all other agents are baseline agents
              (3) python capture.py -r baselineTeam -b myTeam
                  - starts a fully automated game where the red team is a baseline team and blue team is myTeam
  """
  parser = OptionParser(usageStr)

  parser.add_option('-r', '--red', help=default('Red team'),
                    default='baselineTeam')
  parser.add_option('-b', '--blue', help=default('Blue team'),
                    default='baselineTeam')
  parser.add_option('--red-name', help=default('Red team name'),
                    default='Red')
  parser.add_option('--blue-name', help=default('Blue team name'),
                    default='Blue')
  parser.add_option('--redOpts', help=default('Options for red team (e.g. first=keys)'),
                    default='')
  parser.add_option('--blueOpts', help=default('Options for blue team (e.g. first=keys)'),
                    default='')
  parser.add_option('--keys0', help='Make agent 0 (first red player) a keyboard agent', action='store_true',default=False)
  parser.add_option('--keys1', help='Make agent 1 (second red player) a keyboard agent', action='store_true',default=False)
  parser.add_option('--keys2', help='Make agent 2 (first blue player) a keyboard agent', action='store_true',default=False)
  parser.add_option('--keys3', help='Make agent 3 (second blue player) a keyboard agent', action='store_true',default=False)
  parser.add_option('-l', '--layout', dest='layout',
                    help=default('the LAYOUT_FILE from which to load the map layout; use RANDOM for a random maze; use RANDOM<seed> to use a specified random seed, e.g., RANDOM23'),
                    metavar='LAYOUT_FILE', default='defaultCapture')
  parser.add_option('-t', '--textgraphics', action='store_true', dest='textgraphics',
                    help='Display output as text only', default=False)

  parser.add_option('-q', '--quiet', action='store_true',
                    help='Display minimal output and no graphics', default=False)

  parser.add_option('-Q', '--super-quiet', action='store_true', dest="super_quiet",
                    help='Same as -q but agent output is also suppressed', default=False)

  parser.add_option('-z', '--zoom', type='float', dest='zoom',
                    help=default('Zoom in the graphics'), default=1)
  parser.add_option('-i', '--time', type='int', dest='time',
                    help=default('TIME limit of a game in moves'), default=1200, metavar='TIME')
  parser.add_option('-n', '--numGames', type='int',
                    help=default('Number of games to play'), default=1)
  parser.add_option('-f', '--fixRandomSeed', action='store_true',
                    help='Fixes the random seed to always play the same game', default=False)
  parser.add_option('--record', action='store_true',
                    help='Writes game histories to a file (named by the time they were played)', default=False)
  
  parser.add_option('--recordLog', action='store_true',
                    help='Writes game log  to a file (named by the time they were played)', default=False)
  parser.add_option('--replay', default=None,
                    help='Replays a recorded game file.')
  parser.add_option('--replayq', default=None,
                    help='Replays a recorded game file without display to generate result log.')
  parser.add_option('--delay-step', type='float', dest='delay_step',
                    help=default('Delay step in a play or replay.'), default=0.03)                      
  parser.add_option('-x', '--numTraining', dest='numTraining', type='int',
                    help=default('How many episodes of the played games (numGames) are training (suppresses output)'), default=0)
  parser.add_option('-c', '--catchExceptions', action='store_true', default=False,
                    help='Catch exceptions and enforce time limits')

  options, otherjunk = parser.parse_args(argv)
  assert len(otherjunk) == 0, "Unrecognized options: " + str(otherjunk)
  args = dict()

  # Choose a display format
  #if options.pygame:
  #   import pygameDisplay
  #    args['display'] = pygameDisplay.PacmanGraphics()
  if options.textgraphics:
    import textDisplay
    args['display'] = textDisplay.PacmanGraphics()
  elif options.quiet or options.replayq:
    import textDisplay
    args['display'] = textDisplay.NullGraphics()
  elif options.super_quiet:
    import textDisplay
    args['display'] = textDisplay.NullGraphics()
    args['muteAgents'] = True
  else:
    import captureGraphicsDisplay
    # Hack for agents writing to the display
    captureGraphicsDisplay.FRAME_TIME = 0
    args['display'] = captureGraphicsDisplay.PacmanGraphics(options.red, options.red_name, options.blue,
                                                            options.blue_name, options.zoom, 0, capture=True)
    import __main__
    __main__.__dict__['_display'] = args['display']


  args['redTeamName'] = options.red_name
  args['blueTeamName'] = options.blue_name

  if options.fixRandomSeed: random.seed('cs188')

  if options.recordLog:
    sys.stdout = open('log-0', 'w')
    sys.stderr = sys.stdout

  # Special case: recorded games don't use the runGames method or args structure
  if options.replay != None:
    print('Replaying recorded game %s.' % options.replay)
    import pickle
    recorded = pickle.load(open(options.replay,'rb'),encoding="bytes")
    recorded['display'] = args['display']
    recorded['delay'] = options.delay_step
    recorded['redTeamName'] = options.red
    recorded['blueTeamName'] = options.blue
    recorded['waitEnd'] = False

    replayGame(**recorded)
    sys.exit(0)

  # Special case: recorded games don't use the runGames method or args structure
  if options.replayq != None:
    print('Replaying recorded game %s.' % options.replay)
    import pickle
    recorded = pickle.load(open(options.replayq,'rb'),encoding="bytes")
    recorded['display'] = args['display']
    recorded['delay'] = 0.0
    recorded['redTeamName'] = options.red
    recorded['blueTeamName'] = options.blue
    recorded['waitEnd'] = False

    replayGame(**recorded)
    sys.exit(0)

  # Choose a pacman agent
  redArgs, blueArgs = parseAgentArgs(options.redOpts), parseAgentArgs(options.blueOpts)
  if options.numTraining > 0:
    options.numTraining = min(options.numTraining, options.numGames)
    redArgs['numTraining'] = options.numTraining
    blueArgs['numTraining'] = options.numTraining
  nokeyboard = options.textgraphics or options.quiet or options.numTraining > 0
  print ('\nRed team %s with %s:' % (options.red, redArgs))
  redAgents = loadAgents(True, options.red, nokeyboard, redArgs)
  print ('\nBlue team %s with %s:' % (options.blue, blueArgs))
  blueAgents = loadAgents(False, options.blue, nokeyboard, blueArgs)
  args['agents'] = sum([list(el) for el in zip(redAgents, blueAgents)],[]) # list of agents

  if None in blueAgents or None in redAgents:
    if None in blueAgents:
      print ('\nBlue team failed to load!\n')
    if None in redAgents:
      print ('\nRed team failed to load!\n')
    raise Exception('No teams found!')

  numKeyboardAgents = 0
  for index, val in enumerate([options.keys0, options.keys1, options.keys2, options.keys3]):
    if not val: continue
    if numKeyboardAgents == 0:
      agent = keyboardAgents.KeyboardAgent(index)
    elif numKeyboardAgents == 1:
      agent = keyboardAgents.KeyboardAgent2(index)
    else:
      raise Exception('Max of two keyboard agents supported')
    numKeyboardAgents += 1
    args['agents'][index] = agent

  # Choose a layout
  import layout
  layouts = []
  for i in range(options.numGames):
    if options.layout == 'RANDOM':
      l = layout.Layout(randomLayout().split('\n'))
    elif options.layout.startswith('RANDOM'):
      l = layout.Layout(randomLayout(int(options.layout[6:])).split('\n'))
    elif options.layout.lower().find('capture') == -1:
      raise Exception( 'You must use a capture layout with capture.py')
    else:
      l = layout.getLayout( options.layout )
    if l == None: raise Exception("The layout " + options.layout + " cannot be found")
    
    layouts.append(l)
    
  args['layouts'] = layouts
  args['length'] = options.time
  args['numGames'] = options.numGames
  args['numTraining'] = options.numTraining
  args['record'] = options.record
  args['catchExceptions'] = options.catchExceptions
  args['delay_step'] = options.delay_step
  return args

def randomLayout(seed = None) -> mazeGenerator.Maze:
  if not seed:
    seed = random.randint(0,99999999)
  # layout = 'layouts/random%08dCapture.lay' % seed
  # print 'Generating random layout in %s' % layout
  return mazeGenerator.generateMaze(seed)

import traceback
def loadAgents(isRed: bool,
               factory: str,
               textgraphics: bool,
               cmdLineArgs: list) -> list[Agent | None]:
  "Calls agent factories and returns lists of agents"
  try:
    if not factory.endswith(".py"):
      factory += ".py"
    
    print(factory)
    #module = imp.load_source('player' + str(int(isRed)), factory)
    ## Replacement code for above line, since module imp is removed.
    ## From https://docs.python.org/3/whatsnew/3.12.html#whatsnew312-removed-imp
    modname = 'player' + str(int(isRed))
    loader = importlib.machinery.SourceFileLoader(modname, factory)
    spec = importlib.util.spec_from_file_location(modname, factory, loader=loader)
    module = importlib.util.module_from_spec(spec)
    # The module is always executed and not cached in sys.modules.
    # Uncomment the following line to cache the module.
    # sys.modules[module.__name__] = module
    loader.exec_module(module)
  except (NameError, ImportError):
    print('Error: The team "' + factory + '" could not be loaded! ', file=sys.stderr)
    traceback.print_exc()
    return [None for i in range(2)]
  except IOError:
    print('Error: The team "' + factory + '" could not be loaded! ', file=sys.stderr)
    traceback.print_exc()
    return [None for i in range(2)]

  args = dict()
  args.update(cmdLineArgs)  # Add command line args with priority

  print ("Loading Team:", factory)
  print ("Arguments:", args)

  # if textgraphics and factoryClassName.startswith('Keyboard'):
  #   raise Exception('Using the keyboard requires graphics (no text display, quiet or training games)')

  try:
    createTeamFunc = getattr(module, 'createTeam')
  except AttributeError:
    print('Error: The team "' + factory + '" could not be loaded! ', file=sys.stderr)
    traceback.print_exc()
    return [None for i in range(2)]

  indexAddend = 0
  if not isRed:
    indexAddend = 1
  indices = [2*i + indexAddend for i in range(2)]
  return createTeamFunc(indices[0], indices[1], isRed, **args)

def replayGame(layout: Layout,
               agents: list[Agent],
               actions: list['Action'],
               display: 'Graphics',
               length: int,
               redTeamName: str,
               blueTeamName: str,
               waitEnd: bool =True,
               delay: int = 1) -> None:
    rules = CaptureRules()
    game = rules.newGame( layout, agents, display, length, False, False )
    state = game.state
    display.redTeam = redTeamName
    display.blueTeam = blueTeamName
    display.initialize(state.data)

    for action in actions:
      # Execute the action
      state = state.generateSuccessor( *action )
      # Change the display
      display.update( state.data )
      # Allow for game specific conditions (winning, losing, etc.)
      rules.process(state, game)
      time.sleep(delay)

    game.gameOver = True
    if not game.rules.quiet:
      redCount = 0
      blueCount = 0
      foodToWin = (TOTAL_FOOD/2) - MIN_FOOD
      for index in range(state.getNumAgents()):
        agentState = state.data.agentStates[index]
        if index in state.getRedTeamIndices():
          redCount += agentState.numReturned
        else:
          blueCount += agentState.numReturned

      if blueCount >= foodToWin:#state.getRedFood().count() == MIN_FOOD:
        print('The Blue team has returned at least %d of the opponents\' dots.' % foodToWin)
      elif redCount >= foodToWin:#state.getBlueFood().count() == MIN_FOOD:
        print('The Red team has returned at least %d of the opponents\' dots.' % foodToWin)
      else:#if state.getBlueFood().count() > MIN_FOOD and state.getRedFood().count() > MIN_FOOD:
        print('Time is up.')
        if state.data.score == 0: print('Tie game!')
        else:
          winner = 'Red'
          if state.data.score < 0: winner = 'Blue'
          print('The %s team wins by %d points.' % (winner, abs(state.data.score)))

    if waitEnd == True:
      print("END")
      try:
        wait = input("PRESS ENTER TO CONTINUE")
      except:
        print("END")

    display.finish()


def runGames(layouts: list[Layout],
             agents: list[Agent],
             display: 'Graphics',
             length: int,
             numGames: int,
             record: bool,
             numTraining: int,
             redTeamName: str,
             blueTeamName: str,
             muteAgents: bool = False,
             catchExceptions: bool = False,
             delay_step: int = 0) -> list[Game]:

  rules = CaptureRules()
  games = []

  if numTraining > 0:
    print ('Playing %d training games' % numTraining)

  for i in range( numGames ):
    beQuiet = i < numTraining
    layout = layouts[i]
    if beQuiet:
        # Suppress output and graphics
        import textDisplay
        gameDisplay = textDisplay.NullGraphics()
        rules.quiet = True
    else:
        gameDisplay = display
        rules.quiet = False
    g = rules.newGame( layout, agents, gameDisplay, length, muteAgents, catchExceptions )
    g.run(delay=delay_step)
    if not beQuiet: games.append(g)

    g.record = None
    if record:
      import pickle, game
      #fname = ('recorded-game-%d' % (i + 1)) +  '-'.join([str(t) for t in time.localtime()[1:6]])
      #f = file(fname, 'w')
      components = {'layout': layout, 'agents': [Agent() for a in agents], 'actions': g.moveHistory, 'length': length, 'redTeamName': redTeamName, 'blueTeamName':blueTeamName }
      #f.close()
      print("recorded")
      g.record = pickle.dumps(components)
      with open('replay-%d'%i,'wb') as f:
        f.write(g.record)

  if numGames > 1:
    scores = [game.state.data.score for game in games]
    redWinRate = [s > 0 for s in scores].count(True)/ float(len(scores))
    blueWinRate = [s < 0 for s in scores].count(True)/ float(len(scores))
    print( 'Average Score:', sum(scores) / float(len(scores)))
    print ('Scores:       ', ', '.join([str(score) for score in scores]))
    print ('Red Win Rate:  %d/%d (%.2f)' % ([s > 0 for s in scores].count(True), len(scores), redWinRate))
    print ('Blue Win Rate: %d/%d (%.2f)' % ([s < 0 for s in scores].count(True), len(scores), blueWinRate))
    print ('Record:       ', ', '.join([('Blue', 'Tie', 'Red')[max(0, min(2, 1 + s))] for s in scores]))
  return games

def save_score(game: Game) -> None:
    with open('score', 'w') as f:
        print(game.state.data.score, file=f)

if __name__ == '__main__':
  """
  The main function called when pacman.py is run
  from the command line:

  > python capture.py

  See the usage string for more details.

  > python capture.py --help
  """
  start_time = time.time()
  options = readCommand( sys.argv[1:] ) # Get game components based on input
  games = runGames(**options)

  save_score(games[0])
  print('\nTotal Time Game: %s'% round(time.time() - start_time, 0))
  # import profile
  # profile.run('runGames( **options )', 'profile')
