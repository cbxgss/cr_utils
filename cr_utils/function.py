import os, signal, psutil
import traceback
from bdb import BdbQuit
from typing import Callable, Awaitable, TypeVar, ParamSpec
from functools import partial, wraps
import json
import logging
import base64
from tenacity import RetryCallState
import threading
from concurrent.futures import ThreadPoolExecutor
import asyncio


P = ParamSpec('P')
K = TypeVar("K")
T = TypeVar("T")
U = TypeVar("U")


def set_variable_with_default(var_name, guidance, *default_values):
    num_options = len(default_values)

    # 打印所有选项
    for i, value in enumerate(default_values, start=1):
        print(f"{i}. {value}")

    user_input = input(f"input 1-{num_options} to choose a value for {guidance}: ")

    if user_input.isdigit() and 1 <= int(user_input) <= num_options:
        selected_index = int(user_input) - 1
        os.environ[var_name] = default_values[selected_index]
    elif user_input == "n":
        user_input = input(f"input a value for {guidance}: ")
        os.environ[var_name] = user_input
    else:
        os.environ[var_name] = user_input

    print(f"Selected {guidance}: {var_name} = {os.environ[var_name]}")
    print()


def make_cleanup(func: Callable[P, T]) -> Callable[P, T]:
    def killall_processes() -> None:
        current_pid = os.getpid()
        try:
            parent = psutil.Process(current_pid)
        except psutil.NoSuchProcess:
            print("[Cleanup] Current process not found.")
            return

        procs = parent.children(recursive=True)
        pgids = {os.getpgid(p.pid) for p in procs if p.is_running()}
        print(f"[Cleanup] Found process groups to kill: {pgids}")
        for pgid in pgids:
            try:
                print(f"[Cleanup] Killing process group {pgid}")
                os.killpg(pgid, signal.SIGKILL)
            except Exception as e:
                print(f"[Cleanup] Failed to kill pgid {pgid}: {e}")

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception:
            print("[Cleanup] Exception occurred during function execution:")
            print(traceback.format_exc())
            killall_processes()
            import sys
            sys.exit(0)

    return wrapper


def make_debugger(func: Callable[P, T], enable_ipdb: bool = True) -> Callable[P, T]:
    def handle_interrupt(signum, frame):
        print("\n[Signal] Ctrl+C received.")
        flag = input("Do you want to enter the debugger? (y/n): ").strip().lower()
        if flag == 'y':
            if enable_ipdb:
                import ipdb as pdb
            else:
                import pdb
            print("Entering debugger...")
            pdb.set_trace(frame)
        else:
            raise KeyboardInterrupt

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        signal.signal(signal.SIGINT, handle_interrupt)
        try:
            return func(*args, **kwargs)
        except BdbQuit:
            print("[Debugger] Exited debugger. Cleaning up subprocesses...")
            raise # 继续向上传递，让 cleanup 装饰器处理退出逻辑
        except Exception:
            print("[Debugger] Exception occurred:")
            print(traceback.format_exc())
            if enable_ipdb:
                import ipdb as pdb
            else:
                import pdb
            pdb.post_mortem()
            print("[Debugger] Exiting debugger.")
            raise  # 继续向上传递，让 cleanup 装饰器处理退出逻辑

    return wrapper


def make_async(func: Callable[P, T], executor: ThreadPoolExecutor = None) -> Callable[P, Awaitable[T]]:
    """Take a blocking function, and run it on in an executor thread.

    This function prevents the blocking function from blocking the
    asyncio event loop.
    The code in this function needs to be thread safe.
    """

    def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> asyncio.Future:
        loop = asyncio.get_event_loop()
        p_func = partial(func, *args, **kwargs)
        return loop.run_in_executor(executor=executor, func=p_func)

    return _async_wrapper


def make_sync(async_func: Callable[P, Awaitable[T]]) -> Callable[P, T]:
    @wraps(async_func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(async_func(*args, **kwargs))
        result = None
        exception = None
        def runner():
            nonlocal result, exception
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(async_func(*args, **kwargs))
            except Exception as e:
                exception = e
            finally:
                loop.close()
        thread = threading.Thread(target=runner)
        thread.start()
        thread.join()
        if exception:
            raise exception
        return result

    return wrapper


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


def read_jsonl(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]


def write_jsonl(data: dict, file_path: str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def union_two_dict(dict1: dict, dict2: dict):
    """Union two dict. Will throw an error if there is an item not the same object with the same key.

    Args:
        dict1:
        dict2:

    Returns:

    """
    for key, val in dict2.items():
        if key in dict1:
            assert dict2[key] == dict1[key], \
                f'{key} in meta_dict1 and meta_dict2 are not the same object'
        dict1[key] = val

    return dict1


def append_to_dict(data: dict, new_data: dict):
    for key, val in new_data.items():
        if key not in data:
            data[key] = []
        data[key].append(val)



def encode_image(image_path: str):
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
