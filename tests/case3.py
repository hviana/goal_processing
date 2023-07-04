from src.goal_processing.core import Entity, DataContainer, BeliefReviewFunction, Goal, State, Conflict, Agent, GoalPromotion, Plan, Action

from src.goal_processing.processors.sequential_processor import SequentialProcessor
from src.goal_processing.execution_history.in_memory_execution_history import InMemoryExecutionHistory
from src.goal_processing.explainers.sequential_explainer import SequentialExplainer

import time
import random


def printState(s: State, origin=None):
    ref = s.fromId
    if origin is not None:
        ref = origin
    res = ""
    res += Entity.byId[ref].className() + (" - " +
                                           Entity.byId[ref].desc if Entity.byId[ref].desc else "")
    if Entity.byId[ref].className() == "Goal" and 'priority' in s.value:
        res += " - Priority: " + str(s.value['priority'])
    if "GoalPromotion" in Entity.byId[ref].className() and 'incPriority' in s.value:
        res += " - Priority increment: " + str(s.value['incPriority'])
    if "Attribute" in Entity.byId[ref].className():
        res += " - " + str(s.value)
    if Entity.byId[ref].className() == "Action":
        res += (" - Error: " +
                str(s.value['error']) if "error" in s.value else "")
    res += " - time: " + str(s.time)
    return res

# Belief revision functions


async def brSearchAccident(getEnv, get, getChannel, set):
    if (await getEnv("accidents") and len(await getEnv("accidents")) > 0):
        await set("accident", (await getEnv("accidents")).pop())
    else:
        await set("accident", None)

# Goal "Locate"
# "Locate" goal promotions


async def goalPromotionLocateToExecutive(get, priority):
    if (await get("accident") is not None):
        if (await get("accident.risk") == "high"):
            return priority
        return priority

# "Locate" plan1 actions


async def actionLocate(getEnv, get):
    if random.random() < .5:
        raise Exception("Inaccessible victim")
    # print("Recording victim coordinates. "+ str(beliefs.get("accident")) +" ."+ "Time:"+str(time.time()))

goal1 = Goal(
    desc="Localizing victims",
    promotions=[
        GoalPromotion(f=goalPromotionLocateToExecutive,
                      name="executive", desc="Promote location")
    ],
    plans=[
        Plan(
            desc="Recording victim coordinates",
            priority=0,
            actions=[
                Action(f=actionLocate,
                       desc="Recording victim coordinates")
            ]
        )
    ]
)

# References don't necessarily have to be functions. They can also be methods of classes/objects, lambda functions.
agent = Agent(
    beliefs=DataContainer("beliefs"),
    channel=DataContainer("channel"),
    brfs=[
        BeliefReviewFunction(f=brSearchAccident,
                             desc="Review accidents found"),
    ],
    goals=[
        goal1
    ],
    conflicts=[]
)

processsor = SequentialProcessor(
    agent=agent,
    executionHistory=InMemoryExecutionHistory()
)

enviroment = {
    'accidents': [
        {
            'coordinates': [20, 30],
            'risk': 'high'
        },
        {
            'coordinates': [25, 40],
            'risk': 'high'
        }
    ],
    'battery': 65
}
processsor.deliberate(enviroment)
processsor.processIntentions()


explainer = SequentialExplainer(processsor.executionHistory)
lastStates = processsor.executionHistory.get(
    {'limit': 1, 'toIds': {agent.goals[0].plans[0].actions[0].id}})
for s in lastStates:
    print("top: "+printState(s, s.toId))
    print("0: "+printState(s))
for st in explainer.xHistory(lastStates[0]):
    s = st[0]
    print(str(st[1]) + ": "+printState(s))

processsor.deliberate(enviroment)
processsor.processIntentions()
print()


lastStates = processsor.executionHistory.get(
    {'limit': 1, 'toIds': {agent.goals[0].plans[0].actions[0].id}})
for s in lastStates:
    print("top: "+printState(s, s.toId))
    print("0: "+printState(s))
for st in explainer.xHistory(lastStates[0]):
    s = st[0]
    print(str(st[1]) + ": "+printState(s))
