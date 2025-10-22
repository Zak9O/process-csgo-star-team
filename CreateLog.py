#field is a string that explains the activity we want to look at (for example last_place_name or is_alive)
# this will look for a change in values, if a player is alive in 1 tick, and dead in another this will be noted in a dictionary
import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event
from datetime import datetime, timedelta
import random
import xml.etree.cElementTree as ET

def creatXes(dict_log):
    event_log = EventLog()
    # implement way to split into rounds, where each round is a trace, currently everything is just one large trace
    newtrace=False
    trace = Trace()
    for tick in dict_log:

        for x in range(0,len(dict_log[tick])):
            if dict_log[tick][x][1]=='is_alive' and dict_log[tick][x][2]==True:
                newtrace=True
                trace = Trace()
                break

        for action in range(0,len(dict_log[tick])):
            event = Event()
            event['user:playername'] = dict_log[tick][action][0]
            event['concept:activity'] = dict_log[tick][action][1]
            event['time:tick'] = tick
            event['custom:change'] = dict_log[tick][action][2]  
            trace.append(event)
            
        if newtrace==True:
            event_log.append(trace)
            newtrace=False

    # Specify the path to your output XES file
    output_xes_file = 'csgo_EventLog.xes'
     
    # Write the event log to the XES file
    pm4py.write_xes(event_log, output_xes_file)


def getActivityFromField(field:str, df):

    field_dict = dict()

    for _, row in df.iterrows():
        name = row["name"]
        field_value = row[field]
        # We found some anomalies, where no zone was given, we are disregarding these
        if field_value == "":
            continue 
        tick = row["tick"]

        if name not in field_dict:
            field_dict[name] = [(field, field_value, tick)]

        else:
            _, previous_field_value,_ = field_dict[name][-1]
            if previous_field_value != field_value:
                field_dict[name].append((field, field_value,tick))


    return field_dict

# this function itterates over the list of activities given, for example ["is_alive", "last_place_name"]. And then makes a new dictionary
# where each 
def getActivityLog(activities:list[str], df):
    log_dict = dict()
    for activity in activities:
        field_dict = getActivityFromField(activity, df)
        for player in field_dict:
            player_activities = field_dict[player]
            for activity in player_activities:
                field, field_value, tick = activity
                if tick not in log_dict:
                    log_dict[tick] = [(player, field, field_value)]
                else:
                    log_dict[tick].append((player, field, field_value))

    return log_dict





# print(getActivityLog(["is_alive", "last_place_name"], df))
