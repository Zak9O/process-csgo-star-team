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
    stopCheck=False
    TTeam=("nilo","xfl0ud","LNZ","Alkaren","yxngstxr")
    CTTeam=("bodyy","Graviti","Ex3rcice","Lucky","Maka")

    # implement way to split into rounds, where each round is a trace, currently everything is just one large trace
    event_log.attributes["concept:name"]= "csgo_demo_log"
    
    for i, round in enumerate(rounds):
        trace = Trace()
        trace.attributes["round"] = i+1
        trace.attributes["concept:name"] = f"round_{i+1}"

        for tick in round:
            
            for activity in round[tick]:
                if activity[1]=="name":
                    continue
                event = Event()
                event['concept:name'] = activity[2]
                event['concept:activity'] = activity[1]
                event['time:tick'] = tick
                event['custom:value'] = activity[0]  
                trace.append(event)
                if  activity[0] in CTTeam and activity[1]=="is_alive"  and activity[2]=="False":
                    stopCheck=True
                
            if stopCheck==True :
                break
            
        event_log.append(trace)

    # Specify the path to your output XES file
    output_xes_file = 'csgo_EventLogFirstKill.xes'
     
    # Write the event log to the XES file
    pm4py.write_xes(event_log, output_xes_file)

#df=parser.parse_event("tick","player_death", player=["last_place_name", "team_name"])


#pd.set_option('display.max_rows', 500)


parser=DemoParser("heroic-vs-3dmax-m1-dust2.dem")


df = parser.parse_event("player_death", player=["last_place_name","team_name"],other=["total_rounds_played","tick"])

#df = df[df["total_rounds_played"] == 1]

#print(df.to_string())
tmp = df.groupby(["tick","total_rounds_played","user_name","user_team_name", "attacker_name"]).size().to_frame(name='total_kills').reset_index()
#print(tmp["tick"].min())
#logDict=tmp.to_dict('index')
print(tmp)

#FirstKillXES(logDict)

# group-by like in sql
#df = df.groupby(["total_rounds_played","user_name", "attacker_name"]).size().to_frame(name='total_kills').reset_index()
