# field is a string that explains the activity we want to look at (for example last_place_name or is_alive)
# this will look for a change in values, if a player is alive in 1 tick, and dead in another this will be noted in a dictionary
import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event
from datetime import datetime, timedelta
import random
import xml.etree.cElementTree as ET


def creatXes(rounds):
    event_log = EventLog()
    # implement way to split into rounds, where each round is a trace, currently everything is just one large trace
    event_log.attributes["concept:name"]= "csgo_demo_log"
    for i, round in enumerate(rounds):
        trace = Trace()
        trace.attributes["round"] = i+1
        trace.attributes["concept:name"] = f"round_{i+1}"

        for tick in round:
            for activity in round[tick]:
                event = Event()
                event['user:playername'] = activity[0]
                event['concept:activity'] = activity[1]
                event['time:tick'] = tick
                event['custom:value'] = activity[2]  
                trace.append(event)
            
        event_log.append(trace)

    # Specify the path to your output XES file
    output_xes_file = 'csgo_EventLog.xes'
     
    # Write the event log to the XES file
    pm4py.write_xes(event_log, output_xes_file)

