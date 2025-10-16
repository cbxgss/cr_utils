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
        if not cfg:
            cfg = DictConfig({
                "log_config": {
                    "base_log_dir": os.path.join(os.getcwd(), "outputs", "logs"),
                },
                "workspace": "tmp",
            })
        self.cfg = cfg

    def dir(self, path: str = "", workspace: bool = False) -> str:
        base_dir = self.cfg.log_config.base_log_dir if not workspace else self.cfg.workspace
        return os.path.join(base_dir, path)

    def mkdir(self, path: str, workspace: bool = False):
        os.makedirs(self.dir(path, workspace), exist_ok=True)

    def save_csv(self, file_path: str, csv: pd.DataFrame, workspace: bool = False):
        csv_path = self.dir(file_path, workspace)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        csv.to_csv(csv_path, index=False, encoding="utf-8")

    def save_excel(self, file_path: str, df: pd.DataFrame, workspace: bool = False):
        excel_path = self.dir(file_path, workspace)
        os.makedirs(os.path.dirname(excel_path), exist_ok=True)
        df.to_excel(excel_path, index=False, encoding="utf-8")

    def save_json(self, file_path: str, json_data: dict, workspace: bool = False):
        json_path = self.dir(file_path, workspace)
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)

    def save_jsonl(self, file_path: str, json_list: list[dict], workspace: bool = False):
        jsonl_path = self.dir(file_path, workspace)
        os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for item in json_list:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def save_text(self, file_path: str, content: str, workspace: bool = False):
        md_path = self.dir(file_path, workspace)
        os.makedirs(os.path.dirname(md_path), exist_ok=True)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)

    def save_message(self, file_path: str, message: list[dict[str, str]], workspace: bool = False):
        md_content = []
        for m in message:
            role, content = m["role"], m["content"]
            md_content.append(f"# role: {role}\n\n{content}\n")
        md_content = "\n".join(md_content)
        self.save_text(file_path, md_content, workspace)

    def save_html(self, file_path: str, html: str, workspace: bool = False):
        html_path = self.dir(file_path, workspace)
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
