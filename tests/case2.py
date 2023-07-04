from src.goal_processing.core import Entity, DataContainer, BeliefReviewFunction, Goal, State, Conflict, Agent, GoalPromotion, Plan, Action

from src.goal_processing.processors.sequential_processor import SequentialProcessor
from src.goal_processing.execution_history.in_memory_execution_history import InMemoryExecutionHistory
from src.goal_processing.explainers.sequential_explainer import SequentialExplainer

import time


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


async def brfSearchVictim(getEnv, get, getChannel, set):
    if (await getEnv("victims") and len(await getEnv("victims")) > 0):
        await set("victim", (await getEnv("victims")).pop())
    else:
        await set("victim", None)

# Goal "Locate"
# "Locate" goal promotions


async def goalPromotionLocateToExecutive(get, priority):
    if (await get("victim") is not None):
        return priority


async def goalReadVitalSignsToExecutive(get, priority):
    if (await get("victim.risk") == "high"):
        return priority+1

# "Rescue" plan1 actions


async def actionLocate(getEnv, get):
    time.sleep(0.2)
    pass
    # print("Recording victim coordinates. "+ "Time:"+str(time.time()))


async def actionReadVitalSigns(getEnv, get):
    time.sleep(0.2)
    pass
    # print("Read vital signs. "+ "Time:"+str(time.time()))

goal1 = Goal(
    desc="Locate Victim",
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

goal2 = Goal(
    desc="Read vital signs",
    promotions=[
        GoalPromotion(f=goalReadVitalSignsToExecutive,
                      name="executive", desc="Read vital signs only of serious casualties")
    ],
    plans=[
        Plan(
            desc="Read vital signs",
            priority=0,
            actions=[
                Action(f=actionReadVitalSigns, desc="Read vital signs")
            ]
        )
    ]
)

# References don't necessarily have to be functions. They can also be methods of classes/objects, lambda functions.
agent = Agent(
    beliefs=DataContainer("beliefs"),
    channel=DataContainer("channel"),
    brfs=[
        BeliefReviewFunction(f=brfSearchVictim, desc="Review victims found"),
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
    'victims': [
        {
            'coordinates': [20, 40],
            'risk': 'medium'
        }
    ],
    'battery': 25
}
processsor.deliberate(enviroment)
processsor.processIntentions()

# time.sleep(1)
explainer = SequentialExplainer(processsor.executionHistory)
lastStates = processsor.executionHistory.get(
    {'limit': 1, 'toIds': {agent.goals[0].plans[0].actions[0].id}})
for s in lastStates:
    print("top: "+printState(s, s.toId))
    print("0: "+printState(s))
for st in explainer.xHistory(lastStates[0]):
    s = st[0]
    print(str(st[1]) + ": "+printState(s))
print('--- xNot ---')
possibleHistState = State(
    agent.goals[1].plans[0].id, agent.goals[1].plans[0].actions[0].id, time.time(), time.time(), {})
for sTule in explainer.xNot(possibleHistState):
    s = sTule[0]
    print(str(sTule[2]) + ": "+'Score: '+str(sTule[1]) + ". " + printState(s))
print("0: "+printState(possibleHistState, possibleHistState.toId))
