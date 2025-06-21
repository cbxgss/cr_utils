import os
import pandas as pd
import json
from typing import Callable
import logging
from tenacity import RetryCallState
from omegaconf import DictConfig

from .singleton import Singleton


def custom_before_log(logger: logging.Logger, log_level: int) -> Callable[[RetryCallState], None]:
    def log_it(retry_state: RetryCallState):
        if retry_state.attempt_number > 1:
            logger.log(log_level, f"Retrying {retry_state.fn} (attempt {retry_state.attempt_number})...")
    return log_it


def custom_after_log(logger: logging.Logger, log_level: int) -> Callable[[RetryCallState], None]:
    def log_it(retry_state: RetryCallState):
        if retry_state.outcome and retry_state.outcome.failed:
            exception = retry_state.outcome.exception()
            logger.log(
                log_level,
                f"Failed attempt {retry_state.attempt_number} of {retry_state.fn}: {exception}"
            )
    return log_it


class Logger(metaclass=Singleton):
    def __init__(self, cfg: DictConfig = None):
        self.cfg = cfg
        if cfg is None:
            self.cfg = DictConfig(
                {
                    "log_config": {
                        "base_log_dir": os.path.join(os.getcwd(), "outputs", "logs"),
                    }
                }
            )

    def dir(self, path: str = "") -> str:
        return os.path.join(self.cfg.log_config.base_log_dir, path)

    def mkdir(self, path: str):
        path = os.path.join(self.cfg.log_config.base_log_dir, path)
        os.makedirs(path, exist_ok=True)

    def save_csv(self, file_path: str, csv: pd.DataFrame):
        csv_path = os.path.join(self.cfg.log_config.base_log_dir, file_path)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        csv.to_csv(csv_path, index=False)

    def save_json(self, file_path: str, json_data: dict):
        json_path = os.path.join(self.cfg.log_config.base_log_dir, file_path)
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)

    def save_text(self, file_path: str, content: str):
        md_path = os.path.join(self.cfg.log_config.base_log_dir, file_path)
        os.makedirs(os.path.dirname(md_path), exist_ok=True)
        with open(md_path, "w") as f:
            f.write(content)

    def save_message(self, file_path: str, message: list[dict[str, str]]):
        md_content = []
        for m in message:
            role, content = m["role"], m["content"]
            md_content.append(f"# role: {role}\n\n{content}\n")
        md_content = "\n".join(md_content)
        self.save_text(file_path, md_content)

    def save_html(self, file_path: str, html: str):
        html_path = os.path.join(self.cfg.log_config.base_log_dir, file_path)
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        with open(html_path, "w") as f:
            f.write(html)
