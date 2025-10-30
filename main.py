from CreateXESfile import creatXes
from CreateLog import getListOfActivitiesPerRound
from demoparser2 import DemoParser

#BigRedButton
def getEventLog():
    print("Creating log...")
    rounds = [4]
    activities_in_rounds = getListOfActivitiesPerRound(round_numbers = rounds)
    event_log = creatXes(activities_in_rounds)
    print("Done. Log created succesfully")



if __name__ == "__main__":
    getEventLog()