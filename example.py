from src.goal_processing.core import Entity, Attribute, DataContainer, BeliefReviewFunction, Goal, State, Conflict, Agent, GoalPromotion, Plan, Action

from src.goal_processing.processors.sequential_processor import SequentialProcessor
from src.goal_processing.execution_history.in_memory_execution_history import InMemoryExecutionHistory
from src.goal_processing.explainers.sequential_explainer import SequentialExplainer

import time

# Belief revision functions


async def brfAnalyzeAccident(getEnv, get, getChannel, set):
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

# Goal "Rescue"
# "Rescue" goal promotions


async def goalPromotionRescueToActive(get, priority):
    if (await get("accident") is not None):
        if (await get("accident.risk") == "high"):
            return priority+1
        return priority


async def goalPromotionRescueToExecutive(get, priority):
    if (await get("resources.battery") != "low"):
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
        BeliefReviewFunction(f=brfAnalyzeAccident),
        BeliefReviewFunction(f=brfAnalyzeBattery)
    ],
    goals=[
        Goal(
            promotions=[
                GoalPromotion(f=goalPromotionRescueToActive, name="active"),
                GoalPromotion(f=goalPromotionRescueToExecutive,
                              name="executive")
            ],
            plans=[
                Plan(
                    priority=0,
                    actions=[
                        Action(f=actionRescue)
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
            'coordinates': [20, 40],
            'risk': 'high'
        },
        {
            'coordinates': [15, 30],
            'risk': 'medium'
        }
    ],
    'battery': 60
}
processsor.runInLoop(enviroment)

time.sleep(1)
explainer = SequentialExplainer(processsor.executionHistory)

lastStates = processsor.executionHistory.get(
    {'limit': 1, 'toIds': {agent.goals[0].plans[0].actions[0].id}})
for s in lastStates:
    print("0: "+str(s))
for st in explainer.xHistory(lastStates[0]):
    print(str(st[1]) + ": "+str(st[0]))

print('--- xNot ---')
possibleHistState = State(
    agent.goals[0].plans[0].id, agent.goals[0].plans[0].actions[0].id, time.time(), time.time(), {})
for sTule in explainer.xNot(possibleHistState):
    print(str(sTule[2]) + ": "+'Score: '+str(sTule[1]) + ". " + str(sTule[0]))
print("0: "+str(possibleHistState))
