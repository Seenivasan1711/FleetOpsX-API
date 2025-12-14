class PlannerInterface:
    def plan_day(self, context):
        raise NotImplementedError

    def replan(self, context):
        raise NotImplementedError
