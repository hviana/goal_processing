from src.goal_processing.core import Entity, DataContainer, BeliefReviewFunction, Goal, State, Conflict, Agent, GoalPromotion, Plan, Action

from src.goal_processing.processors.sequential_processor import SequentialProcessor
from src.goal_processing.execution_history.in_memory_execution_history import InMemoryExecutionHistory
from src.goal_processing.explainers.sequential_explainer import SequentialExplainer

import time

# Belief revision functions


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


async def brSearchAccident(getEnv, get, getChannel, set):
    if (await getEnv("accidents") and len(await getEnv("accidents")) > 0):
        await set("accident", (await getEnv("accidents")).pop())
    else:
        await set("accident", None)


async def brfAnalyzeBattery(getEnv, get, getChannel, set):
    if (await getEnv("battery") < 30):
        await set("resources.battery", "low")
    elif (await getEnv("battery") >= 30 and await getEnv("battery") < 70):
        await set("resources.battery", "medium")
    elif (await getEnv("battery") >= 70):
        await set("resources.battery", "high")

# Goal "Locate"
# "Locate" goal promotions


async def goalPromotionLocateToExecutive(get, priority):
    if (await get("accident") is not None):
        if (await get("accident.risk") == "high"):
            return priority
        return priority


async def goalRechargeBatteryToExecutive(get, priority):
    if (await get("resources.battery") == "low"):
        return priority+1

# "Locate" plan1 actions


async def actionLocate(getEnv, get):
    time.sleep(0.2)
    pass
    # print("Recording victim coordinates. "+ "Time:"+str(time.time()))


async def actionRechargeBattery(getEnv, get):
    time.sleep(0.2)
    pass
    # print("Recharging battery. "+ "Time:"+str(time.time()))

goal1 = Goal(
    desc="Localizing victims",
    promotions=[
        GoalPromotion(f=goalPromotionLocateToExecutive,
                      name="executive", desc="Promoting accident by risk")
    ],
    plans=[
        Plan(
            desc="Localizing victims coordinates",
            priority=0,
            actions=[
                Action(f=actionLocate,
                       desc="Recording victim coordinates")
            ]
        )
    ]
)

goal2 = Goal(
    desc="Go to base",
    promotions=[
        GoalPromotion(f=goalRechargeBatteryToExecutive,
                      name="executive", desc="Promote if battery level is low")
    ],
    plans=[
        Plan(
            desc="Recharge battery in base",
            priority=0,
            actions=[
                Action(f=actionRechargeBattery,
                       desc="Recharge battery in base")
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
        BeliefReviewFunction(f=brfAnalyzeBattery, desc="Review battery level")
    ],
    goals=[
        goal1, goal2
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
            'coordinates': [20, 40],
            'risk': 'low'
        }
    ],
    'battery': 25
}
processsor.runInLoop(enviroment)

time.sleep(1)
explainer = SequentialExplainer(processsor.executionHistory)
lastStates = processsor.executionHistory.get(
    {'limit': 1, 'toIds': {agent.goals[0].plans[0].actions[0].id}})
for s in lastStates:
    print("top: "+printState(s, s.toId))
    print("0: "+printState(s))
for st in explainer.xHistory(lastStates[0]):
    s = st[0]
    print(str(st[1]) + ": "+printState(s))

print()

lastStates = processsor.executionHistory.get(
    {'limit': 1, 'toIds': {agent.goals[1].plans[0].actions[0].id}})
for s in lastStates:
    print("top: "+printState(s, s.toId))
    print("0: "+printState(s))
for st in explainer.xHistory(lastStates[0]):
    s = st[0]
    print(str(st[1]) + ": "+printState(s))
