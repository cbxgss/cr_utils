import os, signal, psutil
import ipdb
import traceback
from bdb import BdbQuit
from typing import Callable, Awaitable, TypeVar, ParamSpec
from functools import partial, wraps
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


def killall_processes() -> None:
    current_pid = os.getpid()
    try:
        parent = psutil.Process(current_pid)
    except psutil.NoSuchProcess:
        print("[Cleanup] Current process not found.")
        return
    # 获取所有子进程组
    procs = parent.children(recursive=True)
    pgids = set()
    for p in procs:
        try:
            pgids.add(os.getpgid(p.pid))
        except Exception:
            ...
    print(f"[Cleanup] Found {len(procs)} subprocesses to kill.")
    # 杀死所有子进程组
    for pgid in pgids:
        try:
            print(f"[Cleanup] Killing process group {pgid}")
            os.killpg(pgid, signal.SIGKILL)
        except Exception as e:
            print(f"[Cleanup] Failed to kill pgid {pgid}: {e}")
    print("[Cleanup] All subprocesses killed.")
    os._exit(0)


def make_interrupt_handler(debug: bool = True):
    def handle_interrupt(signum, frame):
        print("\n[Signal] Ctrl+C received.")
        if debug:
            print("Entering debugger...")
            ipdb.set_trace(frame)
        else:
            print("Debug disabled. Cleaning up subprocesses...")
            killall_processes()
    return handle_interrupt


def make_main(func: Callable[P, T], debug: bool = True) -> Callable[P, T]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        signal.signal(signal.SIGINT, make_interrupt_handler(debug))
        try:
            return func(*args, **kwargs)
        except BdbQuit:
            print("[Make main] Exited debugger. Cleaning up subprocesses...")
            killall_processes()
        except Exception:
            print("[Make main] Exception occurred:")
            print(traceback.format_exc())
            ipdb.post_mortem()
            print("[Make main] Exiting debugger.")
            killall_processes()
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
