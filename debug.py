import parser
import pm4py
from parser import Parser

parser_ = Parser("heroic-vs-3dmax-m1-dust2.dem")
out = parser_.parse()

event_log = parser.create_event_log(out)
pm4py.write_xes(event_log, "./logs/test.xes")
