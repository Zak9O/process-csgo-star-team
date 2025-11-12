# field is a string that explains the activity we want to look at (for example last_place_name or is_alive)
# this will look for a change in values, if a player is alive in 1 tick, and dead in another this will be noted in a dictionary
import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event
from datetime import datetime, timedelta
import random
import xml.etree.cElementTree as ET
from demoparser2 import DemoParser
import pandas as pd
import glob



def FirstKillXES(rounds):
    event_log = EventLog()
    #stopCheck=False
    #TTeam=("nilo","xfl0ud","LNZ","Alkaren","yxngstxr")
    #CTTeam=("bodyy","Graviti","Ex3rcice","Lucky","Maka")
    parser=DemoParser("heroic-vs-3dmax-m1-dust2.dem")
    df = parser.parse_event("player_death", player=["last_place_name","team_name"],other=["total_rounds_played","tick"])


    # implement way to split into rounds, where each round is a trace, currently everything is just one large trace
    event_log.attributes["concept:name"]= "csgo_demo_log"
    
    for i, round in enumerate(rounds):
        
        Check = df[df["total_rounds_played"] == i]

        tmp = Check.groupby(["tick","total_rounds_played","user_name","user_team_name", "attacker_name"]).size().to_frame(name='total_kills').reset_index()
        logDict=tmp.to_dict('index')
        VictimTeamName=logDict[0]["user_team_name"]
        AttackerName=logDict[0]["attacker_name"]
        if VictimTeamName=="TERRORIST":
            continue
        stopCheck=False
        
        trace = Trace()
        trace.attributes["round"] = i+1
        trace.attributes["concept:name"] = f"round_{i+1}"

        for tick in round:
            for activity in round[tick]:
                if (stopCheck==True):
                    break
                if activity[0] != AttackerName :
                    continue
                if(tmp["tick"].min()<tick):
                    stopCheck=True
                    event = Event()
                    event['concept:name'] = "First_Blood"
                    event['concept:activity'] = "First_Kill"
                    event['time:tick'] = tmp["tick"].min()
                    event['custom:value'] = AttackerName
                    trace.append(event) 
                else:
                    event = Event()
                    event['concept:name'] = activity[2]
                    event['concept:activity'] = activity[1]
                    event['time:tick'] = tick
                    event['custom:value'] = activity[0]  
                    trace.append(event)
                
                
            if(stopCheck==True):
                break
            
                
                
        event_log.append(trace)

    # Specify the path to your output XES file
    output_xes_file = 'csgo_EventLogFirstKill.xes'
     
    # Write the event log to the XES file
    pm4py.write_xes(event_log, output_xes_file)


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
                event['concept:name'] = activity[2]
                event['concept:activity'] = activity[1]
                event['time:tick'] = tick
                event['custom:value'] = activity[0]  
                trace.append(event)
            
        event_log.append(trace)

    # Specify the path to your output XES file
    output_xes_file = 'csgo_EventLog.xes'
     
    # Write the event log to the XES file
    pm4py.write_xes(event_log, output_xes_file)

