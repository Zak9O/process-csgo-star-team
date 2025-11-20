from pathlib import Path
from parser import Parser, Attributes, create_event_log, Case
import pm4py
import re


target_dir = Path("./Heroric_Dust2_demos")
absolute_file_paths = [
    str(item.resolve())
    for item in target_dir.iterdir()
    if item.is_file() and str(item.resolve()).endswith(".dem")
]
cases: list[Case] = []
for path in absolute_file_paths:
    parser = Parser(path)
    cases.extend(parser.parse())

log = create_event_log(cases, True)
log_file_path = "./logs/path-to-end-rum.xes"

pm4py.write_xes(log, log_file_path)

# Making the date field work
with open(log_file_path, "r") as f:
    log_content = f.read()
pattern = r'string key="time'
replacement = r'date key="time'
new_log_content = re.sub(pattern, replacement, log_content, flags=re.DOTALL)
with open(log_file_path, "w") as f:
    f.write(new_log_content)

log = create_event_log(cases, False)
log_file_path = "./logs/path-to-end.xes"

pm4py.write_xes(log, log_file_path)

# Making the date field work
with open(log_file_path, "r") as f:
    log_content = f.read()
pattern = r'string key="time'
replacement = r'date key="time'
new_log_content = re.sub(pattern, replacement, log_content, flags=re.DOTALL)
with open(log_file_path, "w") as f:
    f.write(new_log_content)
