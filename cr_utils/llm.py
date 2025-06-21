import re
import logging
import time
import yaml
import litellm
from litellm import Message, ModelResponse, Router
from tenacity import retry, wait_random_exponential, stop_never

from .logger import Logger
from .costmanager import CostManagers
from .function import custom_after_log
from .singleton import Singleton


logger = logging.getLogger(__name__)

# logging.getLogger("LiteLLM").setLevel(logging.WARNING)
# logging.getLogger("httpx").setLevel(logging.WARNING)
litellm.drop_params = True


class Chater(metaclass=Singleton):
    def __init__(self):
        self.cnt = 0
        with open("config/litellm.yaml", "r") as f:
            config = yaml.safe_load(f)
        self.router = Router(model_list=config["model_list"])

    def save_prompt(self, messages: list[dict], name: str = "all", path: str = "llm"):
        log = Logger()
        log.save_message(f"{path}/{self.cnt}-{name}.md", messages)
        self.cnt += 1
        return self.cnt - 1

    def save_rsp(self, rsp: str, cnt: int, name: str = "all", path: str = "llm"):
        log = Logger()
        log.save_text(f"{path}/{cnt}-{name}-rsp.md", rsp)

    def _process_response(self, response: ModelResponse, cnt: int, name: str, path: str, start_time: float) -> str:
        rsp_msg: Message = response.choices[0].message
        rsp_time = time.time() - start_time
        rsp = rsp_msg.content
        if getattr(rsp_msg, "reasoning_content", None) is not None:
            rsp = f"# Think\n\n{rsp_msg.reasoning_content}\n\n# Answer\n\n{rsp}"
        self.save_rsp(rsp, cnt, name, path)
        CostManagers().update_cost(
            response.usage.prompt_tokens, response.usage.completion_tokens,
            response._hidden_params["response_cost"], rsp_time, name
        )
        return rsp_msg.content

    @retry(stop=stop_never, wait=wait_random_exponential(multiplier=1, max=10), after=custom_after_log(logger, logging.INFO))
    def call_llm(self, prompt: str | dict, model='openai/gpt-4o', reasoning_effort=None, name="all", path="llm", **kwargs) -> str:
        messages = [{"content": prompt, "role": "user"}] if isinstance(prompt, str) else prompt
        cnt = self.save_prompt(messages, name, path)
        start_time = time.time()
        response: ModelResponse = self.router.completion(model=model, messages=messages, reasoning_effort=reasoning_effort, **kwargs)
        return self._process_response(response, cnt, name, path, start_time)


    @retry(stop=stop_never, wait=wait_random_exponential(multiplier=1, max=10), after=custom_after_log(logger, logging.INFO))
    async def acall_llm(self, prompt: str | dict, model='openai/gpt-4o', reasoning_effort=None, name="all", path="llm", **kwargs) -> str:
        messages = [{"content": prompt, "role": "user"}] if isinstance(prompt, str) else prompt
        cnt = self.save_prompt(messages, name, path)
        start_time = time.time()
        response: ModelResponse = await self.router.acompletion(model=model, messages=messages, reasoning_effort=reasoning_effort, **kwargs)
        return self._process_response(response, cnt, name, path, start_time)


def extract_any_blocks(response, block_type="python"):
    pattern_backticks = r"```" + block_type + r"\s*(.*?)\s*```"
    pattern_dashes = r"^-{3,}\s*\n(.*?)\n-{3,}"
    blocks = re.findall(pattern_backticks, response, re.DOTALL)
    blocks.extend(re.findall(pattern_dashes, response, re.DOTALL | re.MULTILINE))
    return blocks


def extract_code_blocks(response):
    pattern_backticks = r"```python\s*(.*?)\s*```"
    pattern_dashes = r"^-{3,}\s*\n(.*?)\n-{3,}"
    blocks = re.findall(pattern_backticks, response, re.DOTALL)
    blocks.extend(re.findall(pattern_dashes, response, re.DOTALL | re.MULTILINE))
    return blocks


def extract_json_blocks(response):
    pattern_backticks = r"```json\s*(.*?)\s*```"
    pattern_dashes = r"^-{3,}\s*\n(.*?)\n-{3,}"
    blocks = re.findall(pattern_backticks, response, re.DOTALL)
    blocks.extend(re.findall(pattern_dashes, response, re.DOTALL | re.MULTILINE))
    return blocks


def extract_sp(response, sp="answer"):
    pattern_backticks = r"<" + sp + r">\s*(.*?)\s*</" + sp + r">"
    blocks = re.findall(pattern_backticks, response, re.DOTALL)
    return blocks
