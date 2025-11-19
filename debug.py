import parser
import pm4py
from parser import Parser, Decorator
import re
import pandas as pd

data = {
    "activity_name": "PlayerDied",
    "tick": [233],
}
pd.DataFrame(data)

data = {
    "activity_name": "RoundEnd",
    "tick": [123123],
}
pd.DataFrame(data)

parser_ = Parser("./Heroric_Dust2_demos/lp-vs-kru-m1-dust2.dem", Decorator([], []))
out = parser_.parse()

event_log = parser.create_event_log(out)

log_file_path = "./logs/test.xes"

pm4py.write_xes(event_log, log_file_path)

# Making the date field work
with open(log_file_path, "r") as f:
    log_content = f.read()
pattern = r'string key="time'
replacement = r'date key="time'
new_log_content = re.sub(pattern, replacement, log_content, flags=re.DOTALL)
with open(log_file_path, "w") as f:
    f.write(new_log_content)
