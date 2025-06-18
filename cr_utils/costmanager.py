from dataclasses import dataclass
import logging
from prettytable import PrettyTable

from cr_utils import Singleton


logger = logging.getLogger(__name__)


@dataclass
class Costs:
    cnt: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost: float
    total_time: float


class CostManager:
    def __init__(self, name: str):
        self.name = name
        self.cnt = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0
        self.total_time = 0

    def update_cost(self, prompt_tokens=0, completion_tokens=0, cost=0, rsp_time=0):
        """
        Update the total cost, prompt tokens, and completion tokens.

        Args:
        prompt_tokens (int): The number of tokens used in the prompt.
        completion_tokens (int): The number of tokens used in the completion.
        model (str): The model used for the API call.
        """
        self.cnt += 1
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost += cost if cost else 0
        self.total_time += rsp_time

    def get_costs(self) -> Costs:
        """Get all costs"""
        return Costs(
            self.cnt,
            self.total_prompt_tokens,
            self.total_completion_tokens,
            self.total_cost,
            self.total_time,
        )


class CostManagers(metaclass=Singleton):
    def __init__(self):
        self.cost_managers: dict[str, CostManager] = {}

    def manager(self, name: str) -> CostManager:
        if name not in self.cost_managers:
            self.cost_managers[name] = CostManager(name)
        return self.cost_managers[name]

    def update_cost(self, prompt_tokens, completion_tokens, cost, rsp_time, name: str = "all"):
        self.manager("all").update_cost(prompt_tokens, completion_tokens, cost, rsp_time)
        if name != "all":
            self.manager(name).update_cost(prompt_tokens, completion_tokens, cost, rsp_time)

    def show_cost(self):
        table = PrettyTable()
        table.field_names = ["Name", "cnt", "prompt tokens", "completion tokens", "cost", "time"]
        for name, cost_manager in self.cost_managers.items():
            cost = cost_manager.get_costs()
            table.add_row([name, cost.cnt, cost.total_prompt_tokens, cost.total_completion_tokens, cost.total_cost, cost.total_time])
        logger.info(f"cost table:\n{table}")
