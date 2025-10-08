from demoparser2 import DemoParser

parser = DemoParser("./heroic-vs-3dmax-m1-dust2.dem")
event_df = parser.parse_event("player_death", player=["X", "Y"], other=["total_rounds_played"])
ticks_df = parser.parse_ticks(["X", "Y"])
print(event_df)
