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
    
    event_log.attributes["concept:name"]= "csgo_demo_log"
    
    Round=0
    
    parseList=[DemoParser("heroic-vs-3dmax-m1-dust2.dem"),DemoParser("heroic-vs-3dmax-m1-dust2.dem")]
    
    for parser in parseList:
        df = parser.parse_event("player_death", player=["last_place_name","team_name"],other=["total_rounds_played","tick"])
        tmp1 = df.groupby(["tick","total_rounds_played","user_name","user_team_name", "attacker_name"]).size().to_frame(name='total_kills').reset_index()

        # implement way to split into rounds, where each round is a trace, currently everything is just one large trace
        

        FB_df = parser.parse_event("player_death", player=["last_place_name","team_name"],other=["total_rounds_played","tick"])
        bomb_df = parser.parse_event("bomb_planted", player=["last_place_name"],other=["total_rounds_played","tick"])
        max_tick = parser.parse_event("round_end")
        
        for i in range(tmp1["total_rounds_played"].max()):
            #insert first blood logic, add general location of it.
            #check if it leads to loss, or bomb planted (and which site its planted)
            #check if player advantage matters in winning post plant for T
            #Maybe, check to see if CT flashes/smokes lead to defuse
            #Think of more conditions.
            #Event
                
            trace = Trace()
            
            trace.attributes["round"] = Round+1
            trace.attributes["concept:name"] = f"round_{Round+1}"
            
            # FIRST BLOOD
            #Round
            FB_Round = FB_df[FB_df["total_rounds_played"] == i]
            #Group by
            FB_group = FB_Round.groupby(["tick","total_rounds_played","user_name","user_team_name", "attacker_name","attacker_last_place_name"]).size().to_frame(name='total_kills').reset_index()
            #Into a dict
            FBDict=FB_group.to_dict('index')
            #Extra info
            VictimTeamName=FBDict[0]["user_team_name"]
            AttackerName=FBDict[0]["attacker_name"]
            PlaceName=FBDict[0]["attacker_last_place_name"]
            
            event = Event()
            event['concept:name'] = "First blood on " + VictimTeamName 
            event['concept:activity'] = "First_Kill"
            event['time:tick'] = FB_group["tick"].min()
            event['custom:value'] = AttackerName
            trace.append(event) 
            
            event = Event()
            event['concept:name'] = "FB on " + VictimTeamName + " at " + PlaceName
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
                    
                    advan_df=parser.parse_ticks(["is_alive", "team_name"], ticks=[BombDict[key]["tick"]+1])
                    dict_Advan=advan_df.to_dict('index')
                    CT_Adv=0
                    
                    for x in dict_Advan:
                        if dict_Advan[x]["is_alive"]==True:
                            if dict_Advan[x]["team_name"]=="CT":
                                CT_Adv+=1
                                #print(CT_Adv)
                            else:
                                CT_Adv-=1
                                #print(CT_Adv)
                    if CT_Adv>0:
                        event = Event()
                        event['concept:name'] = "CT Advantage"
                        event['concept:activity'] = "Advantage"
                        event['time:tick'] = BombDict[key]["tick"]+1
                        event['custom:value'] = 0
                        trace.append(event) 
                    elif CT_Adv<0:
                        event = Event()
                        event['concept:name'] = "Terrorist Advantage"
                        event['concept:activity'] = "Advantage"
                        event['time:tick'] = BombDict[key]["tick"]+1
                        event['custom:value'] = 0
                        trace.append(event) 
                    elif CT_Adv==0:
                        event = Event()
                        event['concept:name'] = "Equal Footing"
                        event['concept:activity'] = "Advantage"
                        event['time:tick'] = BombDict[key]["tick"]+1
                        event['custom:value'] = 0
                        trace.append(event) 
                        
                    break
            else:
                event = Event()
                event['concept:name'] = "No Plant" 
                event['concept:activity'] = "Bomb_Not_Planted"
                event['time:tick'] = max_tick.iloc[i+1]["tick"]-2
                event['custom:value'] = "Not_Planted"
                trace.append(event) 
            
            
            bombDef=parser.parse_event("bomb_defused",other=["total_rounds_played","tick"])
            bombGang = bombDef[bombDef["total_rounds_played"] == i]
            whoDed=parser.parse_ticks(["is_alive", "team_name"], ticks=[max_tick.iloc[i+1]["tick"]])
            whoDedDict=whoDed.to_dict('index')
            CTAlive=False
            if max_tick.iloc[i+1]["winner"] =="CT":
                
                if len((bombGang.to_dict('index')).keys())!=0:
                    event = Event()
                    event['concept:name'] = "Defused by CT"
                    event['concept:activity'] = "Win Type"
                    event['time:tick'] = max_tick.iloc[i+1]["tick"]-1
                    event['custom:value'] = "Who Won"
                    trace.append(event) 
                else:
                    event = Event()
                    event['concept:name'] = "T killed"
                    event['concept:activity'] = "Win Type"
                    event['time:tick'] = max_tick.iloc[i+1]["tick"]-1
                    event['custom:value'] = "Who Won"
                    trace.append(event) 
            else:
                for TD in whoDedDict:
                        if whoDedDict[TD]["is_alive"]==True:
                            if whoDedDict[TD]["team_name"]=="CT":
                                CTAlive=True
                                break
                if CTAlive==True:
                    event = Event()
                    event['concept:name'] = "Bomb Exploded"
                    event['concept:activity'] = "Win Type"
                    event['time:tick'] = max_tick.iloc[i+1]["tick"]-1
                    event['custom:value'] = "Who Won"
                    trace.append(event) 
                else:
                    event = Event()
                    event['concept:name'] = "CT killed"
                    event['concept:activity'] = "Win Type"
                    event['time:tick'] = max_tick.iloc[i+1]["tick"]-1
                    event['custom:value'] = "Who Won"
                    trace.append(event) 
                
            
            # WINNER OF THE ROUND
            event = Event()
            event['concept:name'] = "Won by " + max_tick.iloc[i+1]["winner"]
            event['concept:activity'] = "winner"
            event['time:tick'] = max_tick.iloc[i+1]["tick"]
            event['custom:value'] = "Who Won"
            trace.append(event) 

                    
            event_log.append(trace)
            Round=Round+1

        # Specify the path to your output XES file
    output_xes_file = 'csgo_MultiEventLogAbstract.xes'
     
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
