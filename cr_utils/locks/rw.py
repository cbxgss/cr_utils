import threading


class RWLock:
    """可重入的读写锁（读可并发，写独占，写线程可重入）。"""
    def __init__(self):
        self._readers = 0
        self._writer = None            # 当前写线程的 thread id
        self._writer_count = 0         # 当前写线程重入计数
        self._cond = threading.Condition()

    def _acquire_read(self):
        me = threading.get_ident()
        with self._cond:
            while self._writer is not None and self._writer != me:
                self._cond.wait()
            self._readers += 1

    def _release_read(self):
        with self._cond:
            self._readers -= 1
            if self._readers == 0:
                self._cond.notify_all()

    def _acquire_write(self):
        me = threading.get_ident()
        with self._cond:
            if self._writer == me:
                # 写线程重入
                self._writer_count += 1
                return
            while self._writer is not None or self._readers > 0:
                self._cond.wait()
            self._writer = me
            self._writer_count = 1

    def _release_write(self):
        with self._cond:
            self._writer_count -= 1
            if self._writer_count == 0:
                self._writer = None
                self._cond.notify_all()

    # --- 上下文管理器 ---
    class _ReadCtx:
        def __init__(self, lock): self._lock = lock
        def __enter__(self): self._lock._acquire_read()
        def __exit__(self, exc_type, exc_val, exc_tb): self._lock._release_read()

    class _WriteCtx:
        def __init__(self, lock): self._lock = lock
        def __enter__(self): self._lock._acquire_write()
        def __exit__(self, exc_type, exc_val, exc_tb): self._lock._release_write()

    def read(self):
        return RWLock._ReadCtx(self)

    def write(self):
        return RWLock._WriteCtx(self)



if __name__ == "__main__":
    import time
    import random

    rwlock = RWLock()

    def reader(id, delay=0.1):
        time.sleep(random.uniform(0, delay))
        with rwlock.read():
            print(f"Reader {id} started reading")
            time.sleep(random.uniform(0.1, 0.5))
            print(f"Reader {id} finished reading")

    def writer(id, delay=0.1):
        time.sleep(random.uniform(0, delay))
        with rwlock.write():
            print(f"Writer {id} started writing")
            time.sleep(random.uniform(0.2, 0.6))
            print(f"Writer {id} finished writing")

    threads = []
    for i in range(5):
        t = threading.Thread(target=reader, args=(i,))
        threads.append(t)
        t.start()

    for i in range(2):
        t = threading.Thread(target=writer, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
