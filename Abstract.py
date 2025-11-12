import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event
from datetime import datetime, timedelta
import random
import xml.etree.cElementTree as ET
from demoparser2 import DemoParser
import pandas as pd
import glob


def AbstractXES():
    event_log = EventLog()
    
    parser=DemoParser("heroic-vs-3dmax-m1-dust2.dem")
    df = parser.parse_event("player_death", player=["last_place_name","team_name"],other=["total_rounds_played","tick"])
    tmp1 = df.groupby(["tick","total_rounds_played","user_name","user_team_name", "attacker_name"]).size().to_frame(name='total_kills').reset_index()

    # implement way to split into rounds, where each round is a trace, currently everything is just one large trace
    event_log.attributes["concept:name"]= "csgo_demo_log"
    
    FB_df = parser.parse_event("player_death", player=["last_place_name","team_name"],other=["total_rounds_played","tick"])
    bomb_df = parser.parse_event("bomb_planted", player=["last_place_name"],other=["total_rounds_played","tick"])
    max_tick = parser.parse_event("round_end")
    
    for i in range( tmp1["total_rounds_played"].max()):
        #insert first blood logic, add general location of it.
        #check if it leads to loss, or bomb planted (and which site its planted)
        #check if player advantage matters in winning post plant for T
        #Maybe, check to see if CT flashes/smokes lead to defuse
        #Think of more conditions.
        #Event
              
        trace = Trace()
        trace.attributes["round"] = i+1
        trace.attributes["concept:name"] = f"round_{i+1}"
        
        # FIRST BLOOD
        #Round
        FB_Round = FB_df[FB_df["total_rounds_played"] == i]
        #Group by
        FB_group = FB_Round.groupby(["tick","total_rounds_played","user_name","user_team_name", "attacker_name"]).size().to_frame(name='total_kills').reset_index()
        #Into a dict
        FBDict=FB_group.to_dict('index')
        #Extra info
        VictimTeamName=FBDict[0]["user_team_name"]
        AttackerName=FBDict[0]["attacker_name"]
        
        event = Event()
        event['concept:name'] = "First_Blood on " + VictimTeamName
        event['concept:activity'] = "First_Kill"
        event['time:tick'] = FB_group["tick"].min()
        event['custom:value'] = AttackerName
        trace.append(event) 
        
        # BOMB PLANTED
        #Round
        Bomb_Round = bomb_df[bomb_df["total_rounds_played"] == i]
        #Into a dict
        BombDict=Bomb_Round.to_dict('index')
        #Extra info
        if(len(BombDict.keys())!=0):
            for key in BombDict:
                Bomb_planted=BombDict[key]["user_last_place_name"]
                event = Event()
                event['concept:name'] = "Plant " + Bomb_planted
                event['concept:activity'] = "Bomb_Planted"
                event['time:tick'] = BombDict[key]["tick"]
                event['custom:value'] = BombDict[key]["user_name"]
                trace.append(event) 
                        
                #print(Bomb_planted)
                break
        else:
            event = Event()
            event['concept:name'] = "No Plant" 
            event['concept:activity'] = "Bomb_Not_Planted"
            event['time:tick'] = max_tick.iloc[i+1]["tick"]-1
            event['custom:value'] = "Not_Planted"
            trace.append(event) 
            
            
        # WINNER OF THE ROUND
        event = Event()
        event['concept:name'] = "Won by " + max_tick.iloc[i+1]["winner"]
        event['concept:activity'] = "winner"
        event['time:tick'] = max_tick.iloc[i+1]["tick"]
        event['custom:value'] = "Who Won"
        trace.append(event) 

                
        event_log.append(trace)

    # Specify the path to your output XES file
    output_xes_file = 'csgo_EventLogAbstract.xes'
     
    # Write the event log to the XES file
    pm4py.write_xes(event_log, output_xes_file)
    return True


runcheck=AbstractXES()
print(runcheck)



#df=parser.parse_event("tick","player_death", player=["last_place_name", "team_name"])


#pd.set_option('display.max_rows', 500)


# parser=DemoParser("heroic-vs-3dmax-m1-dust2.dem")


# df = parser.parse_event("player_death", player=["last_place_name","team_name"],other=["total_rounds_played","tick"])

# df = df[df["total_rounds_played"] == 0]

# #print(df.to_string())
# tmp = df.groupby(["tick","total_rounds_played","user_name","user_team_name", "attacker_name"]).size().to_frame(name='total_kills').reset_index()
# print(tmp["tick"].min())
# #logDict=tmp.to_dict('index')
# print(tmp)

# #FirstKillXES(logDict)

# # group-by like in sql
# #df = df.groupby(["total_rounds_played","user_name", "attacker_name"]).size().to_frame(name='total_kills').reset_index()
