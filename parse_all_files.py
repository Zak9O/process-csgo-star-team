from pathlib import Path
from parser import Parser, Decorator, create_event_log, Case
import pm4py

target_dir = Path('./Heroric_Dust2_demos') 
absolute_file_paths = [
    str(item.resolve())
    for item in target_dir.iterdir()
    if item.is_file() and 
    str(item.resolve()).endswith('.dem')
]
cases:list[Case] = []
for path in absolute_file_paths:
    decorator = Decorator([], [])
    parser = Parser(path, decorator)
    cases.extend(parser.parse())

log = create_event_log(cases)
pm4py.write_xes(log, "./logs/test.xes")
