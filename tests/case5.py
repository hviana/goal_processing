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


async def brfAnalyzeAccident(getEnv, get, getChannel, set):
    if (await getEnv("accidents") and len(await getEnv("accidents")) > 0):
        await set("accident", (await getEnv("accidents")).pop())
    else:
        await set("accident", None)

# Goal "Rescue"
# "Rescue" goal promotions


async def goalPromotionRescueToExecutive(get, priority):
    if (await get("accident") is not None):
        if (await get("accident.risk") == "high"):
            return priority+1
        return priority
# "Rescue" plan1 actions


async def actionRescue(getEnv, get):
    print("Rescue from the accident at: " +
          str(get('accident'))+". Time:"+str(time.time()))

# References don't necessarily have to be functions. They can also be methods of classes/objects, lambda functions.
agent = Agent(
    beliefs=DataContainer("beliefs"),
    channel=DataContainer("channel"),
    brfs=[
        BeliefReviewFunction(f=brfAnalyzeAccident,
                             desc="Review environmental accidents"),
    ],
    goals=[
        Goal(
            desc="Rescue victims",
            promotions=[
                GoalPromotion(f=goalPromotionRescueToExecutive, desc="Rescue serious accidents",
                              name="executive")
            ],
            plans=[
                Plan(
                    desc="Rescue victims",
                    priority=0,
                    actions=[
                        Action(f=actionRescue, desc="Rescue victims")
                    ]
                )
            ]
        )
    ],
    conflicts=[],
)

processsor = SequentialProcessor(
    agent=agent,
    executionHistory=InMemoryExecutionHistory()
)

enviroment = {
    'accidents': [
        {
            'coordinates': [15, 30],
            'risk': 'medium'
        },
        {
            'coordinates': [20, 40],
            'risk': 'high'
        }
    ],
    'battery': 60
}
processsor.deliberate(enviroment)
processsor.processIntentions()
time.sleep(1)
processsor.deliberate(enviroment)
processsor.processIntentions()

explainer = SequentialExplainer(processsor.executionHistory)
lastStates = processsor.executionHistory.get(
    {'limit': 2, 'toIds': {agent.goals[0].plans[0].actions[0].id}})
for s in [lastStates[0]]:
    print("top: "+printState(s, s.toId))
    print("0: "+printState(s))
for st in explainer.xHistory(lastStates[0]):
    s = st[0]
    print(str(st[1]) + ": "+printState(s))
print()
for s in [lastStates[1]]:
    print("top: "+printState(s, s.toId))
    print("0: "+printState(s))
for st in explainer.xHistory(lastStates[1]):
    s = st[0]
    print(str(st[1]) + ": "+printState(s))
