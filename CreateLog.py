from demoparser2 import DemoParser
parser = DemoParser("../heroic-vs-3dmax-m1-dust2.dem")
ticks = parser.parse_ticks(["tick", "name", "is_alive", "team_name","bomb_exploded"])

list_of_activities = ["name", "is_alive", "last_place_name"]

# print(ticks)

# print(parser.list_game_events())

#print(list(parser.columns.values))
#print(list(ticks))

# print(parser.parse_event("round_start"))
# print(parser.parse_event("round_end"))





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

    return dict(sorted(log_dict.items()))



# Returns a list of dictionaries, where each dictionary is the activity log for a round
def getListOfActivitiesPerRound():
    round_start = list(parser.parse_event("round_start")["tick"])
    round_end = list(parser.parse_event("round_end")["tick"])

    list_of_round_interval = []
    for i in range(len(round_start)):
        list_of_round_interval.append((round_start[i],round_end[i+1]))

    list_of_dict = []    
    for interval in list_of_round_interval:
        start_tick = interval[0]
        end_tick = interval[1]
        
        list_of_ticks_for_round_i = list(range(start_tick,end_tick+1))
        round_i_df = parser.parse_ticks(list_of_activities, ticks = list_of_ticks_for_round_i)
        activity_log_round_i = getActivityLog(list_of_activities, round_i_df)
        list_of_dict.append(activity_log_round_i)

    return list_of_dict


