import time
from demoparser2 import DemoParser

start = time.time()
# ticks = parser.parse_ticks(["tick", "name", "is_alive", "team_name","bomb_exploded"])


parser = DemoParser("heroic-vs-3dmax-m1-dust2.dem")
round_start = list(parser.parse_event("round_start")["tick"])
round_end = list(parser.parse_event("round_end")["tick"])


class Activity:
    def __init__(self, field, isStartTickImportant):
        self.isStartTickImportant = isStartTickImportant #is the state of the field obvious in the first tick?
        self.field = field

    def getField(self):
        return self.field
    

startTickNotImportant = ["is_alive"]
startTickImportant = ["last_place_name"]
activities_for_demoparser = startTickImportant + startTickNotImportant


activities = []
for field in startTickImportant:
    activities.append(Activity(field, True))

for field in startTickNotImportant:
    activities.append(Activity(field, False))
    
def getActivityFromField(activity:Activity, df) -> dict:
    """
    Parameter1: Is the activtiy that we want to track in the df
    Parameter2: df
    return: dictionary of players and their activites in a round.
    """
    field_dict = dict()
    for _, row in df.iterrows(): 
        team_name = row["team_name"] #CT or T
        player_name = row["name"]
        field_name = activity.getField()
        field_value = row[field_name]
        activity_label = team_name + "_" + str(field_value)
        tick = row["tick"]

        if player_name not in field_dict:
                field_dict[player_name] = [(activity_label, tick, field_name)]
        else:
            previous_activity_label, _, _ = field_dict[player_name][-1]
            if previous_activity_label != activity_label:
                field_dict[player_name].append((activity_label, tick, field_name))

                
    return field_dict



def getActivityLog(activities:list[Activity], df) -> dict:
    """
    Parameter1: List of activities that we want to track in the DF
    Parameter2: DF
    Return dictionary of ticks and activites - sorted by ticks.
    """
    log_dict = dict()
    for activity in activities:
        field_dict = getActivityFromField(activity, df)
                        
        for player in field_dict:
            player_activities = field_dict[player]    
            for activity_1 in player_activities:
                activity_label, tick, field_name = activity_1
                
                if not activity.isStartTickImportant:
                    if tick in round_start:
                        continue
                    
                if tick not in log_dict:
                    log_dict[tick] = [(activity_label, field_name, player)] #Remove player if unecessary
                else:
                    log_dict[tick].append((activity_label, field_name, player)) 
    return dict(sorted(log_dict.items()))

def getListOfActivitiesPerRound() -> list[dict]:
    """
    Return list of dictionaries with activites sorted by ticks for each round.
    """
    list_of_round_interval = []
    for i in range(len(round_start)):
        list_of_round_interval.append((round_start[i],round_end[i+1]))

    list_of_dictForEachRound = []   
    counter = 0
    for interval in list_of_round_interval:
        start_tick = interval[0]
        end_tick = interval[1]
        
        list_of_ticks_for_round_i = list(range(start_tick,end_tick+1))
        round_i_df = parser.parse_ticks(activities_for_demoparser + ["team_name"], ticks = list_of_ticks_for_round_i)
        activity_log_round_i = getActivityLog(activities, round_i_df)
        list_of_dictForEachRound.append(activity_log_round_i)
            
    return list_of_dictForEachRound

log = getListOfActivitiesPerRound()

for item in log:

    for i, j in item.items():
        print(i, j)

end = time.time()
time_ = end - start
print(time_)