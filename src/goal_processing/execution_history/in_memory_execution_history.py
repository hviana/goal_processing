from ..core import AbstractExecutionHistory, State
import copy
import bisect
from deepdiff import DeepDiff


class InMemoryExecutionHistory(AbstractExecutionHistory):
    """
    A executionHistory that saves all states in RAM. Useful for academic purposes.
    For an application in production, it can generate a prohibitive cost of RAM memory.
    """

    def __init__(self, params={}):
        super().__init__(params)
        self.states: list[State] = []

    async def getAsync(self, filters: dict) -> list[State]:
        res: list[State] = []
        arr = self.states
        if ('order' in filters):
            if (filters['order'] == 'asc'):
                arr = arr[::-1]  # reversing using list slicing
        for state in self.states:
            satisfyConditions = True
            if ('id' in filters):
                if (state.id != filters['id']):
                    satisfyConditions = False
            if ('fromIds' in filters):
                if (not state.fromId in filters['fromIds']):
                    satisfyConditions = False
            if ('toIds' in filters):
                if (not state.toId in filters['toIds']):
                    satisfyConditions = False
            if ('time' in filters):
                if (state.time != filters['time']):
                    satisfyConditions = False
            if ('value' in filters):
                if (len(DeepDiff(state.value, filters['value'])) > 0):
                    satisfyConditions = False
            if ('minTime' in filters):
                if (state.time < filters['minTime']):
                    satisfyConditions = False
            if ('maxTime' in filters):
                if (state.time > filters['maxTime']):
                    satisfyConditions = False
            if ('minActivationTime' in filters):
                if (state.activationTime < filters['minActivationTime']):
                    satisfyConditions = False
            if ('maxActivationTime' in filters):
                if (state.activationTime > filters['maxActivationTime']):
                    satisfyConditions = False
            if ('limit' in filters):
                if (len(res) >= filters['limit']):
                    satisfyConditions = False
                    break
            if (satisfyConditions):
                res.append(state)
        return res

    async def addAsync(self, state: State) -> None:
        # Insert order is essential
        bisect.insort(self.states, copy.deepcopy(state))
