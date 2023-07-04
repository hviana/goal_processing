import uuid
import copy
import time
from collections.abc import Awaitable
from typing import Self, Any, Iterator, AsyncIterator
from abc import ABC, abstractmethod
from deepdiff import DeepDiff
import asyncio
import nest_asyncio
from threading import Timer
nest_asyncio.apply()


class Entity (ABC):
    """
    Parent class of classes that represent goal processing entities.
    """
    byId: dict[str, Self] = {}

    def __init__(self, desc: str = "", id: str = ""):
        self.desc = desc
        if (id == ""):
            id = Entity.genId()
        self.id = id
        Entity.byId[id] = self

    def className(self):
        return self.__class__.__name__ + (": " + self.name if 'name' in self.__dict__ else "")

    @staticmethod
    def genId() -> str:
        return uuid.uuid4().hex

    def __eq__(self, other: Self):
        return self.id == other.id


class State:
    """
    This class represents a state value, for a given entity at a given time.
    """

    def __init__(self, fromId: str = "", toId: str = "", time: float = 0, activationTime: float = 0, value: dict = {}, id: str = Entity.genId()):
        """
        Constructor:
        @param fromId: Entity that had the change of state.
        @param toId: Subsequent entity that receives a change of state information.
                     May have an empty value if the state change is not propagated to a target entity.

        @param activationTime: There is where the change of state started.
        @param time: Has the state change completed.
        """
        self.fromId = fromId
        self.toId = toId
        self.time = time
        self.activationTime = activationTime
        self.value = value
        self.id = id

    def __str__(self) -> str:
        """
        Method for python to know how to convert the object to type "str".
        Useful for printouts.
        """
        return str({
            'id': self.id,
            'from': Entity.byId[self.fromId].className() if self.fromId in Entity.byId else "",
            'fromId': self.fromId,
            'to': Entity.byId[self.toId].className() if self.toId in Entity.byId else "",
            'toId': self.toId,
            'time': self.time,
            'activationTime': self.activationTime,
            'value': self.value
        })

    def __lt__(self, other: Self) -> bool:  # reverse order
        """
        Important for sorting algorithms.
        The order is reversed. That is, larger numbers are at the beginning.
        """
        return self.time > other.time


class Attribute(Entity):
    """
    This class represents a Enviroment Attribute or Belief.
    """

    def __init__(self, name: str, desc: str = "", id: str = ""):
        """
        Constructor:
        @param name: A string. Enviroment Attribute name.
        @param desc (optional): Textual description of what the belief revision function does.
        @param id (optional): Entity identifier in the form of a string. If not specified, one will be generated.
        """
        super().__init__(desc, id)
        self.name = name
        self.relations: list[Entity] = list()


class AbstractExecutionHistory(ABC):
    """
    This class represents a way to save inference states.
    """
    @abstractmethod
    def __init__(self, params: dict = {}):
        """
        Constructor:
        @param params: A dict structure that contains initialization information.
        """
    @abstractmethod
    async def addAsync(self, state: State) -> None:
        """
        Save a state to the executionHistory.
        @param state: Instance of class State.
        """
        pass

    @abstractmethod
    async def getAsync(self, filters: dict) -> list[State]:
        """
        Returns a list of saved states.
        @param filters: A dict structure that contains the filters to return the states.
                        Filters can be different for each implementation of this abstract class.
                        It is important that the implementations of this class describe the filters that can be used in this method.
                        Recommended filters:
                        {
                            'id': State id,
                            'fromIds': Entity ids (set) originating the modifications,
                            'toIds': Entity ids (set) for the modifications,
                            'time': State time,
                            'value': value content,
                            'minTime': Lower limit for time,
                            'maxTime': Upper limit for time,
                            'minActivationTime': Lower limit for activation time,
                            'maxActivationTime': Upper limit for activation time,
                            'limit': Maximum number of states to return,
                            'order': 'asc' or 'desc'. If history is a time-ordered vector, traverse the vector from beginning to end (asc) or end to beginning (desc)
                            ...
                        }
        """
        pass

    def add(self, state: State) -> None:
        """
        Wraps the "addAsync" method for synchronous calls
        """
        return asyncio.run(self.addAsync(state))

    def get(self, filters: dict) -> list[State]:
        """
        Wraps the "getAsync" method for synchronous calls
        """
        return asyncio.run(self.getAsync(filters))


class DataContainer:
    """
    Agent's beliefs/enviroment
    """

    def __init__(self, name: str = "", data: dict = {}):
        """
        Constructor:
        @param data: Agent's initial beliefs/enviroment, in a dict structure.
        """
        self.data = data
        self.name = name
        self.attrs: dict[str, Entity] = {}

    def set(self, path: str, value: Any) -> None:
        """
        list a belief.
        @param path: Path of beliefs/enviroment. Ex; 'attr1.subAttr2'.
        @param value: Beliefs/enviroment value. Must be "True" or "False" for beliefs used in goals/promotion and plan rules (recommended for explainability).
        @return: A boolean value that, if True, indicates that there has been a change in beliefs/enviroment.
        """
        hasChange = False
        if path == "":
            if (len(DeepDiff(self.data, value)) > 0):
                hasChange = True
                self.data = copy.deepcopy(value)
            return hasChange
        else:
            d = self.data
            keys = path.split('.')
            for key in keys[:-1]:
                if (not key in d):
                    d[key] = {}
                elif (not (isinstance(d[key], dict))):
                    d[key] = {}
                d = d[key]
            if (keys[-1] in d):
                if (len(DeepDiff(d[keys[-1]], value)) > 0):
                    hasChange = True
            else:
                hasChange = True
            if (hasChange):
                d[keys[-1]] = copy.deepcopy(value)
            return hasChange

    def get(self, path: str) -> Any:
        """
        @param path: Path of beliefs/enviroment. Ex; 'attr1.subAttr2'.
        @return: the value of a beliefs/enviroment. If the beliefs/enviroment does not exist, its value is assumed to be "False".
        """
        d = self.data
        keys = path.split('.')
        for key in keys:
            if (d is None or not key in d):
                return False
            else:
                d = d[key]
        return d

    def createSet(self, hist: AbstractExecutionHistory, fromId: str) -> Awaitable:
        """
        Creates the asynchronous function "list". This function is used to change beliefs/env.
        @param hist: AbstractExecutionHistory implementation.
        """
        async def set(path: str, value: Any) -> Any:
            hasChange = self.set(path, value)
            if hasChange:
                attrName = self.name + "." + path
                if (not attrName in self.attrs):
                    self.attrs[attrName] = Attribute(name=attrName)
                if (not self.attrs[attrName] in Entity.byId[fromId].attrs):
                    Entity.byId[fromId].attrs.append(self.attrs[attrName])
                    self.attrs[attrName].relations.append(Entity.byId[fromId])
                await hist.addAsync(State(fromId, self.attrs[attrName].id, time.time(), time.time(), copy.deepcopy(value)))
        return set

    def createGet(self, hist: AbstractExecutionHistory, toId: str, lastVal: Any = None) -> Awaitable:
        """
        Creates the asynchronous function "get". This function is used to access beliefs/env.
        @param hist: AbstractExecutionHistory implementation.
        """
        async def get(path: str) -> Any:
            attrName = self.name + "." + path
            if (not attrName in self.attrs):
                self.attrs[attrName] = Attribute(name=attrName)
            if (not self.attrs[attrName] in Entity.byId[toId].attrs):
                Entity.byId[toId].attrs.append(self.attrs[attrName])
                self.attrs[attrName].relations.append(Entity.byId[toId])
            value = self.get(path)
            if (len(DeepDiff(value, lastVal)) > 0):
                await hist.addAsync(State(self.attrs[attrName].id, toId, time.time(), time.time(), copy.deepcopy(value)))
            return value
        return get


class BeliefReviewFunction(Entity):
    """
    This class represents a belief revision function.
    The agent can have multiple belief revision functions.
    The important thing in separating the belief review into several functions is to separate the responsibilities in these functions in a coherent way.
    """

    def __init__(self, f: Awaitable, desc: str = "", id: str = ""):
        """
        Constructor:
        @param f: Belief revision function. It is a reference to a function. 
                  Its input is a Dict structure that contains the enviroment input, a Dict structure that contains the beliefs and a "list" function.
                  This "list" function is for changing the beliefs from a path. 
                  Examples: 
                  await list('attr1', val1)
                  await list('attr1.subAttr2', val2)
        @param desc (optional): Textual description of what the belief revision function does.
        @param id (optional): Entity identifier in the form of a string. If not specified, one will be generated.
        """
        super().__init__(desc, id)
        self.f = f
        self.agents: list[Agent] = list()
        self.attrs: list[Attribute] = list()


class Action(Entity):
    """
    Represents an action by an agent.
    @param f: Reference to a function/method that will be called to complete the action.
    """

    def __init__(self, f: Awaitable, desc: str = "", id: str = ""):
        super().__init__(desc, id)
        self.f = f
        self.plans: list[Plan] = list()


class GoalPromotion(Entity):
    """
    This class represents a promotion of a goal.
    """

    def __init__(self, name: str, f: Awaitable, desc: str = "", id: str = ""):
        """
        Constructor:
        @param name: A string. Contains the name of the goal promotion.
                     The name "sleeping" cannot be used as it is the initial state of every goal.
        @param f: Promotion function. It is a reference to a function.
                  Its input is a Dict structure that contains the beliefs and an integer that is the priority of the goal.
                  Must return priority. Otherwise, the goal will not be promoted.
                  The priority value returned will be the goal's new priority.
        @param desc (optional): Textual description of what the belief revision function does.
        @param id (optional): Entity identifier in the form of a string. If not specified, one will be generated.
        """
        super().__init__(desc, id)
        self.name = name
        self.f = f
        self.goals: list[Goal] = list()
        self.attrs: list[Attribute] = list()


class Plan(Entity):
    """
    Represents an plan for actions.
        @param priority: Minimum priority for the plan to be chosen
        @param actions: List of instances of the Action class.
        @param desc (optional): Textual description of what the belief revision function does.
        @param id (optional): Entity identifier in the form of a string. If not specified, one will be generated.
    """

    def __init__(self, priority: int, actions: list[Action], desc: str = "", id: str = ""):
        super().__init__(desc, id)
        self.priority = priority
        self.actions = list(actions)
        self.goals = list()
        for action in self.actions:
            action.plans.append(self)


class Goal(Entity):
    """
    This class represents a goal.
    """

    def __init__(self, promotions: list[GoalPromotion], plans: list[Plan], desc: str = "", id: str = ""):
        """
        Constructor:
        @param promotions: A list of instances of the GoalPromotion class. They are the target promotions.
                           They must be ordered, exactly in the order in which the goal is successively promoted.
        @param plans: List of instances of the Plan class.
        @param desc (optional): Textual description of what the belief revision function does.
        @param id (optional): Entity identifier in the form of a string. If not specified, one will be generated.
        """
        super().__init__(desc, id)
        self.promotions = list(promotions)
        for promotion in self.promotions:
            promotion.goals.append(self)
        self.plans = list(plans)
        for plan in self.plans:
            plan.goals.append(self)
        self.initialState()
        self.conflicts: list[Conflict] = list()
        self.agents: list[Agent] = list()
        self.cloneId: str = ""

    def __lt__(self, other: Self) -> bool:  # reverse order
        """
        Important for sorting algorithms.
        """
        # change to self.priority > other.priority if use PriorityQueue
        return self.priority > other.priority

    def isInFinalState(self) -> bool:
        return len(self.promotions) == len(self.status)

    def getClone(self) -> Self:
        clone = copy.deepcopy(self)
        clone.initialState()
        clone.cloneId = Entity.genId()
        return clone

    def initialState(self) -> None:
        self.priority = 0
        self.status = list()

    def promote(self, status: str, priority: int) -> None:
        if (not status in self.status):
            self.status.append(status)
        self.priority = priority


class Conflict(Entity):
    """
    This class represents a conflict between goals.
    """

    def __init__(self, goals: list[Goal], desc: str = "", id: str = ""):
        """
        Constructor:
        @param goals: List of goals that cannot be performed together.
                      If there are conflicts, the highest priority goal is chosen.
        @param desc (optional): Textual description of what the belief revision function does.
        @param id (optional): Entity identifier in the form of a string. If not specified, one will be generated.
        """
        super().__init__(desc, id)
        self.goals = list(goals)
        self.goalsIds = list(map(lambda g: g.id, self.goals))
        self.agents: list[Agent] = list()
        for goal in self.goals:
            goal.conflicts.append(self)


class Agent(Entity):
    """
    This class represents a goal.
    """

    def __init__(self, beliefs: DataContainer, channel: DataContainer, brfs: list[BeliefReviewFunction], goals: list[Goal], conflicts: list[Conflict], desc: str = "", id: str = ""):
        """
        Constructor:
        @param beliefs: Instances of the DataContainer class.
        @param brfs: A list of instances of the class BeliefReviewFunction. Represents the agent's belief revisions.
        @param goals: A list of instances of the class Goal. Represents agent goals.
        @param conflicts: Conflicts between goals. Ex: 
                            conflicts = [
                                Conflict (
                                    goals = [ goal1, goal2, ... ]
                                )
                                ...
                            ]
        @param desc (optional): Textual description of what the belief revision function does.
        @param id (optional): Entity identifier in the form of a string. If not specified, one will be generated.
        """
        super().__init__(desc, id)
        self.beliefs = beliefs
        self.channel = channel
        self.brfs = list(brfs)
        for brf in self.brfs:
            brf.agents.append(self)
        self.goals = list(goals)
        for goal in self.goals:
            goal.agents.append(self)
        self.conflicts = list(conflicts)
        for conflict in self.conflicts:
            conflict.agents.append(self)


class AbstractProcessor(ABC):
    """
    Goal processor.
    This processor performs only one processing iteration.
    Each call of "deliberate" is an iteration.
    """

    def __init__(self, agent: Agent, executionHistory: AbstractExecutionHistory):
        """
        Constructor:
        @param agent: A instance of the class Agent.
        @param executionHistory: A instance of the type AbstractExecutionHistory subclass.
        """
        self.agent = agent
        self._enviroment = DataContainer()
        # PrioriryQueue cannot be used in the self._intentions, as the array needs to be traversed non-destructively in the conflict detection method.
        self._intentions: list[Goal] = []  # Ordered queue of goals
        self._deliberateTimer = None
        self._intentionsTimer = None
        self.executionHistory = executionHistory

    @abstractmethod
    async def deliberateAsync(self, data: dict) -> None:
        """
        Receives new data from the environment, able to update goals.
        If the processor is sequential:
                -- Save changes to environment (optional)
            1) It will first revise the beliefs, according to new data from the environment and existing beliefs.
                -- Save belief state changes
            2) After that, goals can be promoted.
                -- Save state changes that represent goal promotions
            3) After that, goals queue will be updated.

        @param data: A Structure of type Dict. Contains the new environment data.
        """
        pass

    @abstractmethod
    async def processIntentionsAsync(self) -> None:
        """
        Processes the queue of goals (_intentions), which are ordered by priority.
            1) For each goal removed from the queue (which is sorted by priority of these goals):
                2) Get conflicts by method "_detectConflicts".
                3) Skip the goal if it was removed because it was a conflict.
                    -- Save state changes that represent that the objective was removed by conflicts
                4) Select a plan for the goal.
                    -- Save selected plan as a state change
                5) Performs plan Actions:
                    -- Save action performed in the form of a state change
                    -- When detecting a failure or impossibility in an action, save "on goal fail" state.
        """
        pass

    def _detectConflicts(self) -> dict:
        """
        Detect conflicts.
        returns an dict with goals prioritized over others.
        Example:
        {
            conflictId: {
                'chosen': goal1Id,
                'toRemove': { goal2Id, goal3Id, ... }
            }
        }
        This method needs to return a global view of conflicts, as not all "processors" are sequential.
        """
        res = {}
        for conflict in self.agent.conflicts:
            resItem = {}
            for goal in self._intentions:  # Use ordered _intentions, prioritize those with higher priority
                if goal.id in conflict.goalsIds:
                    if not 'chosen' in resItem:
                        resItem['chosen'] = goal.cloneId
                    else:
                        if not 'toRemove' in resItem:
                            resItem['toRemove'] = set()
                        resItem['toRemove'].add(goal.cloneId)
            if 'chosen' in resItem and 'toRemove' in resItem:
                res[conflict.id] = resItem
        return res

    def deliberate(self, data: dict) -> None:
        """
        Wraps the "deliberateAsync" method for synchronous calls.
        """
        return asyncio.run(self.deliberateAsync(data))

    def processIntentions(self) -> None:
        """
        Wraps the "processIntentionsAsync" method for synchronous calls.
        """
        return asyncio.run(self.processIntentionsAsync())

    def _runDeliberateTimer(self, data: dict, delay: float = 0.5) -> None:
        """
        Deliberate repetitively with a Thread timer.
        @param data: A Structure of type Dict. Contains the environment data.
        @param delay: Delay between each inference iteration in seconds. The default is 0.5.
        """
        self.deliberate(data)
        self._deliberateTimer = Timer(
            delay, self._runDeliberateTimer, [data, delay])
        self._deliberateTimer.start()

    def _runProcessIntentionsTimer(self, delay: float = 0.5) -> None:
        """
        Process the goal queue repetitively with a Thread timer.
        @param data: A Structure of type Dict. Contains the environment data.
        @param delay: Delay between each inference iteration in seconds. The default is 0.5.
        """
        self.processIntentions()
        self._intentionsTimer = Timer(
            delay, self._runProcessIntentionsTimer, [delay])
        self._intentionsTimer.start()

    def runInLoop(self, data: dict, delay: float = 0.5) -> None:
        """
        Runs loop inference.
        @param data: A Structure of type Dict. Contains the environment data.
        @param delay: Delay between each inference iteration in seconds. The default is 0.5.
        """
        self._runDeliberateTimer(data, delay)
        self._runProcessIntentionsTimer(delay)

    def stopLoop(self) -> None:
        """
        Stop loop inference.
        """
        if self._deliberateTimer is not None:
            self._deliberateTimer.cancel()
            self._deliberateTimer = None
        if self._intentionsTimer is not None:
            self._intentionsTimer.cancel()
            self._intentionsTimer = None


class AbstractExplainer(ABC):
    """
    Represents an explanation generator.
    """

    def __init__(self, executionHistory: AbstractExecutionHistory):
        """
        Constructor:
        @param executionHistory: Object responsible for saving inference states.
        """
        self._executionHistory = executionHistory
    # The "ExecutionHistory" interface already has its functionality supplied by the "executionHistory" object.
    # The "Description" interface is already supplied by the "desc" property of entities.

    @abstractmethod
    async def causalFunction(self, state: State) -> list[str]:
        """
        Associates possible causes to certain effects.
        For example, every belief is a possible cause for a goal.
        Every goal is a possible cause for plans related to that goal.
        Every plan is a possible cause for actions related to that plan.
        """
        pass

    async def xHistoryAsync(self, effectHistEntry: State, r: int = 1, past: list[str] = set()) -> AsyncIterator[tuple[State, int]]:
        """
        Why did state X (eg: Goal Promotion) happen?.
        @param effectHistEntry: instance of a subclass of the State class.
        """
        if (effectHistEntry.fromId in past):
            pass  # return
        else:
            past.add(effectHistEntry.fromId)
        causes: list[State] = []
        for c in await self.causalFunction(effectHistEntry.fromId):
            hist = await self._executionHistory.getAsync(
                {'fromIds': {c}, 'toIds': {effectHistEntry.fromId, ""}, 'maxTime': effectHistEntry.activationTime, 'limit': 1, 'order': 'desc'})
            if (len(hist) > 0):
                causes.append(hist[0])
        causes.sort()
        for causeHist in causes:
            yield [causeHist, r]
            async for nestedCause in self.xHistoryAsync(causeHist, r+1, past):
                yield nestedCause

    async def xNotAsync(self, effectHistEntry: State, r: int = 1, past: list[str] = set()) -> AsyncIterator[tuple[State, float, int]]:
        """
        Explains why state Z did not occur.
        @param effectHistEntry: instance of a subclass of the State class.
        @params inContrast: iterable tuples "[histEntry, r]"
        """
        if (effectHistEntry.fromId in past):
            return
        else:
            past.add(effectHistEntry.fromId)
        causes: list[State] = []
        toExplore: list[str] = []
        nanoSecond = 1e-6
        minTime = 0
        score = 0
        lastSimilarHist = await self._executionHistory.getAsync({'toIds': {effectHistEntry.toId}, 'maxActivationTime': effectHistEntry.activationTime - nanoSecond, 'limit': 1, 'order': 'desc'})
        if (len(lastSimilarHist) > 0):
            minTime = lastSimilarHist[0].activationTime + nanoSecond
        possibleCauses = await self.causalFunction(effectHistEntry.fromId)
        for c in possibleCauses:
            hist = await self._executionHistory.getAsync({'fromIds': {c}, 'toIds': {effectHistEntry.fromId, ""}, 'minTime': minTime, 'maxTime': effectHistEntry.activationTime, 'limit': 1, 'order': 'desc'})
            if (len(hist) > 0):
                causes.append(hist[0])
            else:
                toExplore.append(c)
        score = 1/(r)*(len(causes)/(len(possibleCauses)+1))
        for c in toExplore:
            possibleHist = State(fromId=c, toId=effectHistEntry.fromId,
                                 activationTime=effectHistEntry.activationTime)
            async for resTuple in self.xNotAsync(possibleHist, r+1):
                score += resTuple[1]
                yield resTuple
            past.add(effectHistEntry.fromId)
        yield [effectHistEntry, score, r]

    def xHistory(self, effectHistEntry: State) -> Iterator[tuple[State, int]]:
        """
        Wraps the "whyAsync" method for synchronous calls.
        """
        gen = self.xHistoryAsync(effectHistEntry)
        while True:
            try:
                yield asyncio.run(gen.__anext__())
            except StopAsyncIteration:
                break

    def xNot(self, effectHistEntry: State) -> AsyncIterator[tuple[State, float, int]]:
        """
        Wraps the "whyInsteadOfAsync" method for synchronous calls.
        """
        gen = self.xNotAsync(effectHistEntry)
        while True:
            try:
                yield asyncio.run(gen.__anext__())
            except StopAsyncIteration:
                break
