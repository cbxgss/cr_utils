import os
import re
import logging
import time
import datetime
import yaml
import litellm
from litellm import Message, ModelResponse, Router, Choices
from tenacity import retry, wait_random_exponential, stop_after_attempt

from .logger import Logger, custom_after_log
from .costmanager import CostManagers
from .singleton import Singleton


logger = logging.getLogger(__name__)

# logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("LiteLLM").setLevel(logging.WARNING)
# logging.getLogger("LiteLLM Router").setLevel(logging.WARNING)
litellm.drop_params = True


class CallCnt(metaclass=Singleton):
    def __init__(self):
        self.cnt = -1

    def __call__(self):
        self.cnt += 1
        return self.cnt


class Chater(metaclass=Singleton):
    def __init__(self, config_path: str = "config/litellm.yaml"):
        self.cnt = CallCnt()
        self.router = Router()
        self._config_path = config_path
        self._config_time: float = None
        self.init()

    def init(self):
        mtime = os.path.getmtime(self._config_path)
        if mtime != self._config_time:
            mtime_readable = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            config_time_readable = datetime.datetime.fromtimestamp(self._config_time).strftime("%Y-%m-%d %H:%M:%S") if self._config_time else "Never"
            logger.info(f"Loading LiteLLM config from {self._config_path} ({config_time_readable} -> {mtime_readable})")
            with open(self._config_path, "r") as f:
                config = yaml.safe_load(f)
            self.router.set_model_list(config["model_list"])
            self._config_time = mtime

    def save_prompt(self, messages: list[dict], name: str = "all", path: str = "llm"):
        log = Logger()
        cnt = self.cnt()
        log.save_message(f"{path}/{cnt}-{name}.md", messages)
        return cnt

    def save_rsp(self, rsp: str, cnt: int, name: str = "all", path: str = "llm"):
        log = Logger()
        log.save_text(f"{path}/{cnt}-{name}-rsp.md", rsp)

    def _process_response(self, response: ModelResponse, cnt: int, name: str, path: str, start_time: float, return_all=False) -> str | Choices:
        rsp_msg: Message = response.choices[0].message
        rsp_time = time.time() - start_time
        rsp = rsp_msg.content
        if getattr(rsp_msg, "reasoning_content", None) is not None:
            rsp = f"<think>\n{rsp_msg.reasoning_content}\n</think>\n{rsp}"
        self.save_rsp(rsp, cnt, name, path)
        CostManagers().update_cost(
            response.usage.prompt_tokens, response.usage.completion_tokens,
            response._hidden_params["response_cost"], rsp_time, name
        )
        return response.choices[0] if return_all else rsp

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=1, max=10), after=custom_after_log(logger, logging.INFO))
    def call_llm(self, prompt: str | dict, model='openai/gpt-4o', reasoning_effort=None, name="all", path="llm", return_all=False, **kwargs) -> str | Choices:
        self.init()
        messages = [{"content": prompt, "role": "user"}] if isinstance(prompt, str) else prompt
        cnt = self.save_prompt(messages, name, path)
        start_time = time.time()
        response: ModelResponse = self.router.completion(model=model, messages=messages, reasoning_effort=reasoning_effort, **kwargs)
        return self._process_response(response, cnt, name, path, start_time, return_all)


    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=1, max=10), after=custom_after_log(logger, logging.INFO))
    async def acall_llm(self, prompt: str | dict, model='openai/gpt-4o', reasoning_effort=None, name="all", path="llm", return_all=False, **kwargs) -> str | Choices:
        self.init()
        messages = [{"content": prompt, "role": "user"}] if isinstance(prompt, str) else prompt
        cnt = self.save_prompt(messages, name, path)
        start_time = time.time()
        response: ModelResponse = await self.router.acompletion(model=model, messages=messages, reasoning_effort=reasoning_effort, **kwargs)
        return self._process_response(response, cnt, name, path, start_time, return_all)

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=1, max=10), after=custom_after_log(logger, logging.INFO))
    def call_embedding(self, text: str | list[str], model='openai/text-embedding-3-small', **kwargs) -> list[list[float]]:
        self.init()
        if isinstance(text, str):
            texts = [text]
        else:
            texts = text
        response = self.router.embedding(model=model, input=texts, **kwargs)
        CostManagers().update_cost(0, 0, response._hidden_params["response_cost"], 0, "embedding")
        return [data["embedding"] for data in response.data]

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=1, max=10), after=custom_after_log(logger, logging.INFO))
    async def acall_embedding(self, text: str | list[str], model='openai/text-embedding-3-small', **kwargs) -> list[list[float]]:
        self.init()
        if isinstance(text, str):
            texts = [text]
        else:
            texts = text
        response = await self.router.aembedding(model=model, input=texts, **kwargs)
        CostManagers().update_cost(0, 0, response._hidden_params["response_cost"], 0, "embedding")
        return [data["embedding"] for data in response.data]


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
