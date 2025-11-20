import parser
import pm4py
from parser import Parser
import re

parser_ = Parser("./Heroric_Dust2_demos/lp-vs-kru-m1-dust2.dem")
out = parser_.parse()

event_log = parser.create_event_log(out, True)

log_file_path = "./logs/single-file.xes"

pm4py.write_xes(event_log, log_file_path)

# Making the date field work
with open(log_file_path, "r") as f:
    log_content = f.read()
pattern = r'string key="time'
replacement = r'date key="time'
new_log_content = re.sub(pattern, replacement, log_content, flags=re.DOTALL)
with open(log_file_path, "w") as f:
    f.write(new_log_content)
