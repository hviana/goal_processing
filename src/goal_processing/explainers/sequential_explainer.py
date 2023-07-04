from ..core import AbstractExplainer, State, AbstractExecutionHistory, Entity, Action


class SequentialExplainer(AbstractExplainer):
    def __init__(self, executionHistory: AbstractExecutionHistory):
        super().__init__(executionHistory)

    async def causalFunction(State, id: str) -> list[str]:
        if (not id in Entity.byId):
            return []
        if (Entity.byId[id].className() == "BeliefReviewFunction"):
            return list(map(lambda e: e.id, Entity.byId[id].attrs))
        if (Entity.byId[id].className() == "Action"):
            return list(map(lambda e: e.id, Entity.byId[id].plans))
        if (Entity.byId[id].className() == "Plan"):
            return list(map(lambda e: e.id, Entity.byId[id].goals))
        if (Entity.byId[id].className() == "Goal"):
            return list(map(lambda e: e.id, Entity.byId[id].conflicts + Entity.byId[id].promotions))
        if (Entity.byId[id].className() == "Conflict"):
            return list(map(lambda e: e.id, Entity.byId[id].goals))
        if ("Attribute" in Entity.byId[id].className()):
            return list(map(lambda e: e.id, Entity.byId[id].relations))
        if ("GoalPromotion" in Entity.byId[id].className()):
            return list(map(lambda e: e.id, Entity.byId[id].attrs))
        return []
