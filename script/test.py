import sys
import time
import asyncio
sys.path.append(".")  # Adjust the path to import from the parent directory


def main():
    cnt = 1
    while True:
        print(f"Running main function {cnt} times")
        cnt += 1
        time.sleep(1)


async def amain():
    cnt = 1
    while True:
        print(f"Running async main function {cnt} times")
        cnt += 1
        await asyncio.sleep(1)


if __name__ == "__main__":
    # main()
    asyncio.run(amain())
