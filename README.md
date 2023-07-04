# goal_processing

Library for processing agent goals. It also covers the generation of
explanations.

The Model to represent the goals is based on beliefs. DataContainer are
everything the Agent believes about the environment, about itself or other
agents. These beliefs are used to construct the agent's intentions, through
successive promotion of goals. Each promotion is based on a class of beliefs.
When going through all the stages of promotions, the goal becomes an intention.
That means, the agent executes the actions of that intention. This model of
successive promotion of goals based on belief categories was created by authors
[[1]](#1). However, unlike the authors [[1]](#1), are not fixed the goal
promotion categories or categories of beliefs. These categories are open to the
programmer.

Finally, the granularity of the construction process of the agent's intentions,
facilitates the generation of explanations. To build the explanation generator
algorithms, the processing steps of the goals are saved in a log. Example steps
are when a belief revision function (there are several belief revision
functions) changes a belief, or when a goal is promoted. The generation of
explanations model is based on the work of the authors [[2]](#2). For the
computational implementation of authors [[2]](#2) model, the precedence relation
between goals is implemented through the concept of priority. By promoting a
goal, the agent can increase the goal's priority. Goal plans also use this
priority. When defining a plan, it is possible to define with which minimum
priority such plan must be chosen.

Another feature that comes from the model of authors [[2]](#2) is that the
beliefs used in goal and plan rules are atomic with boolean values. That is,
they must be true or false. Belief revision functions must set the value of
these atomic beliefs. However, nothing prevents the agent from using complex
beliefs internally. But for reasons of explainability, there is this need for
atomic beliefs in the rules of goals/promotions and plans. The library even
works using complex beliefs in the rules of goals/promotions and plans, but it
makes explainability difficult.

Another characteristic that is particular to this computational implementation
is that the deliberation method is parallel to the goal processing method.
Therefore, care must be taken with beliefs. A belief that promoted a goal may no
longer be the same when that same goal is processed. In some cases, the actions
of a goal plan need information contained in beliefs. To solve this problem,
each goal promotion has the possibility to save beliefs that are important for
goal plans in a backup. This promotes a certain sophistication. It is possible,
for example, to insert a new goal in the queue of goals that are still being
processed. If this new goal has a higher priority, it is processed before the
others (which were chosen in previous stages of deliberation). Another
sophistication promoted is that the same goal can be contained several times in
the goal queue, with different contexts and priorities.

The core of the library was built with asyncronous abstractions. This was done
to promote the use of the library in network communication. In network
communication, asynchronous calls are common. Furthermore, the asynchronous
abstraction facilitates the creation of non-sequential processing models.
Furthermore, the core has additional methods that wrap important asyncronous
calls into synchronous calls. This makes it easier to use when calls are made in
synchronous context.

## Contents

- [Sample application](#sample-application)
  - [Defining conflicts](#defining-conflicts)
  - [Continuous agent execution](#continuous-agent-execution)
- [Generation of explanations](#generation-of-explanations)
- [References](#references)

## Sample application

```python
from src.goal_processing.core import Entity, Attribute, DataContainer, BeliefReviewFunction, Goal, State, Conflict, Agent, GoalPromotion, Plan, Action

from src.goal_processing.processors.sequential_processor import SequentialProcessor
from src.goal_processing.execution_history.in_memory_execution_history import InMemoryExecutionHistory
from src.goal_processing.explainers.sequential_explainer import SequentialExplainer

import time

# Belief revision functions


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
```

### Defining conflicts

To define the conflicts between goals, it is possible to write the code of the
form:

```python
#When instantiating a agent
conflicts = [
    Conflict (
        goals = [ goal1, goal2, ... ]
    )
    ...
]
```

If there are conflicts, the highest priority goal is chosen.

### Continuous agent execution

Calling the `processor.deliberate` and `processor.processIntentions` methods
manually can be useful when knowing if there are changes in the environment.
This manual call allows for greater control of the inference frequency. However,
you can automate the inference by running it in a loop:

```python
processor.runInLoop(enviromentDict, delay)
```

The `processor.runInLoop` method uses a Threading Timer and does not block
program execution.

## Generation of explanations

Example of explanation generation. In the `xHistory` procedure, the input is a
change of state, retrieved from the history. The procedure presents why such a
state change occurred. In procedure `xNot`, the input is a possible change of
state that did not occur. The procedure presents why such a state change did not
occur. In the `xNot` procedure, there is also a score that indicates the
relevance of the explanation section. The formula for this score is:
`1/(r)*(len(causes)/(len(possibleCauses)+1))`. This score also sums the scores
of the nested causes (the causes of the causes).

```python
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
```

## References

<a id="1">[1]</a> C. Castelfranchi and F. Paglieri. The role of beliefs in goal
dynamics: prolegomena to a constructive theory of intentions. Synthese, 155,
237–263, 2007. doi: https://doi.org/10.1007/s11229-006-9156-3

<a id="2">[2]</a> H. Jasinski and C. Tacla Denerating contrastive explanations
for BDI-based goal selection. url:
http://repositorio.utfpr.edu.br/jspui/handle/1/29522
