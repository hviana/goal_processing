from ..core import AbstractProcessor, DataContainer, Agent, State, AbstractExecutionHistory, DataContainer
import time
import bisect
import traceback as tb


class SequentialProcessor(AbstractProcessor):
    def __init__(self, agent: Agent, executionHistory: AbstractExecutionHistory) -> None:
        super().__init__(agent, executionHistory)

    async def deliberateAsync(self, data) -> None:
        self._enviroment = data
        envContainer = DataContainer("env", self._enviroment)
        for brf in self.agent.brfs:
            await brf.f(envContainer.createGet(self.executionHistory, brf.id), self.agent.beliefs.createGet(self.executionHistory, brf.id), self.agent.channel.createGet(self.executionHistory, brf.id), self.agent.beliefs.createSet(self.executionHistory, brf.id))
        for goal in self.agent.goals:
            # the same goal can be contained several times in the goal queue.
            clone = goal.getClone()
            for promotion in clone.promotions:
                incPriority = await promotion.f(self.agent.beliefs.createGet(self.executionHistory, promotion.id), clone.priority)
                if (incPriority is not None):
                    clone.promote(promotion.name, incPriority)
                    await self.executionHistory.addAsync(State(promotion.id, clone.id, time.time(), time.time(), {'incPriority': incPriority, 'cloneId': clone.cloneId}))
                else:
                    break
            if clone.isInFinalState():
                # ordered is important
                bisect.insort(self._intentions, clone)

    async def processIntentionsAsync(self) -> None:
        removedByConflict = set()
        while len(self._intentions) > 0:  # Goals in pursuit. sorted by priority
            # Pursue goals
            # Each time goals are removed/inserted, conflicts change.
            # So we need to redetect the conflicts at each iteration of the loop, due to sequential implementation.
            detectedConflicts = self._detectConflicts()
            goal = self._intentions.pop(0)  # get and remove first ordered
            if (not goal.cloneId in removedByConflict):
                for c in goal.conflicts:
                    if c.id in detectedConflicts:
                        for removedId in detectedConflicts[c.id]['toRemove']:
                            removedByConflict.add(removedId)
                            await self.executionHistory.addAsync(State(c.id, "", time.time(), time.time(), {'chosen': detectedConflicts[c.id]['chosen'], 'removed': removedId}))
            if (goal.cloneId in removedByConflict):
                removedByConflict.remove(goal.cloneId)  # clear RAM
                continue  # skip goal
            chosenPlan = goal.plans[0]
            for plan in goal.plans:
                if (goal.priority >= plan.priority):
                    if (plan.priority > chosenPlan.priority):
                        chosenPlan = plan
            await self.executionHistory.addAsync(State(goal.id, plan.id, time.time(), time.time(), {'cloneId': goal.cloneId, 'priority': goal.priority}))
            for action in plan.actions:
                try:
                    await action.f(DataContainer(self._enviroment).get, self.agent.beliefs.get)
                    await self.executionHistory.addAsync(State(plan.id, action.id, time.time(), time.time(), {'cloneId': goal.cloneId}))
                except Exception as e:
                    exceptionDict = {'cloneId': goal.cloneId, 'error': str(e), 'stack': ''.join(
                        tb.format_exception(None, e, e.__traceback__))}
                    await self.executionHistory.addAsync(State(plan.id, action.id, time.time(), time.time(), exceptionDict))
