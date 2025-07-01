import sys
sys.path.append(".")
from cr_utils import Logger
import pandas as pd

df = pd.DataFrame({
    "name": ["你好", "Bob", "Charlie"],
    "age": [25, 30, 35],
    "city": ["New 好", "Los Angeles", "Chicago"]
})

logger = Logger()
logger.save_csv("test.csv", df)