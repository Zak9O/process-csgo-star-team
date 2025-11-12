from pm4py.objects.log.obj import EventLog, Trace, Event
from typing import Any
from demoparser2 import DemoParser
import pandas as pd
from pandas.core.api import DataFrame


class PlayerDeadException(Exception):
    pass


class Activity:
    def __init__(
        self, name: str, time: int, attributes: dict[str, object] = dict()
    ) -> None:
        self.name: str = name
        self.time: int = time
        self.attributes: dict[str, object] = attributes


class Case:
    def __init__(
        self, name: str, trace: list[Activity], attributes: dict[str, object] = dict()
    ) -> None:
        self.name: str = name
        self.trace: list[Activity] = trace
        self.attributes: dict[str, object] = attributes

class Parser:
    """
    Focuses on last_place_name
    """

    # The attributes we want on each trace
    ACTIVITY_ATTRIBUTES: list[str] = ["game_time"]
    CASE_ATTRIBUTES: list[str] = ["name"]

    def __init__(self, path: str) -> None:
        self.path: str = path
        self.parser: DemoParser = DemoParser(self.path)
        parser_attributes = ["total_rounds_played"]
        self.events_bomb_defused: pd.DataFrame = self.parser.parse_event(
            "bomb_defused", other=parser_attributes
        )
        self.events_bomb_planted: pd.DataFrame = self.parser.parse_event(
            "bomb_planted", other=parser_attributes
        )

    def parse(self) -> list[Case]:
        print(f"Considering {self.path}")

        traces: list[Case] = []
        rounds = self.events_bomb_defused["total_rounds_played"]
        count = len(rounds)

        print(f"  Found {count} rounds with bomb defusions!")
        for round in rounds:
            trace = self.parse_round(round)
            traces.extend(trace)
            print(f"  Parsed round {round}")

        return traces

    def parse_round(self, round: int) -> list[Case]:
        start_t, end_t = self.extract_ticks(round)

        df = self.get_scoped_df(start_t, end_t)
        df = self.filter_ct(df)

        # Defined here for optimization purposes. Takes O(N) to construct each dict
        alive_start_dict = self.get_alive_at_t_dict(df, start_t)
        alive_end_dict = self.get_alive_at_t_dict(df, end_t)

        players: list[str] = list(df["name"].unique())

        cases: list[Case] = []

        for player in players:
            try:
                case = self.parse_player(
                    player, df, alive_start_dict, alive_end_dict, round
                )
                cases.append(case)
            except PlayerDeadException:
                continue

        return cases

    def parse_player(
        self,
        player: str,
        df: DataFrame,
        alive_start_dict: dict[str, bool],
        alive_end_dict: dict[str, bool],
        round: int,
    ) -> Case:
        if not alive_start_dict[player]:
            raise PlayerDeadException
        df = self.mask_df_to_player(player, df)
        trace = self.parse_trace(player, df, alive_end_dict)

        attributes = self.get_case_attributes(df)

        return Case(self.path + str(round) + player, trace, attributes)

    def parse_trace(
        self, player: str, df: pd.DataFrame, alive_end_dict: dict[str, bool]
    ) -> list[Activity]:
        df = self.mask_df_to_location_changes(df)

        trace: list[Activity] = []

        for _, row in df.iterrows():
            name = row["last_place_name"]
            time = row["tick"]
            attributes = dict()
            for attr in self.ACTIVITY_ATTRIBUTES:
                attributes[attr] = row[attr]
            trace.append(Activity(name, time, attributes))
        if not alive_end_dict[player]:
            trace.append(Activity("Die", time))  # pyright: ignore[reportPossiblyUnboundVariable]
            time += 1  # pyright: ignore[reportPossiblyUnboundVariable]

        trace.append(Activity("Round End", time))  # pyright: ignore[reportPossiblyUnboundVariable]

        return trace

    def get_case_attributes(self, df: DataFrame) -> dict[str, object]:
        df: pd.Series[Any] = df.iloc[0]
        attributes:dict[str, object] = {}

        for attr in self.CASE_ATTRIBUTES:
            attributes[attr] = df[attr]

        return attributes


    def extract_ticks(self, round: int) -> tuple[int, int]:
        bomb_defused = self.events_bomb_defused[
            self.events_bomb_defused["total_rounds_played"] == round
        ].iloc[0]
        end_t = bomb_defused["tick"]

        bomb_planted = self.events_bomb_planted[
            self.events_bomb_planted["total_rounds_played"] == round
        ].iloc[0]
        start_t = bomb_planted["tick"]

        return (start_t, end_t)

    def get_scoped_df(self, start_t: int, end_t: int) -> pd.DataFrame:
        df = self.parser.parse_ticks(
            self.ACTIVITY_ATTRIBUTES
            + ["tick", "team_name", "is_alive", "last_place_name"],
            ticks=range(int(start_t), int(end_t + 1)),
        )
        return df

    def filter_ct(self, df: DataFrame) -> DataFrame:
        team_mask = df["team_name"] == "CT"
        df = df[team_mask]
        return df

    def get_alive_at_t_dict(self, df: pd.DataFrame, tick: int) -> dict[str, bool]:
        tick_mask = df["tick"] == tick
        df = df[tick_mask]
        return df[["name", "is_alive"]].set_index("name")["is_alive"].to_dict()

    def mask_df_to_player(self, player: str, df: pd.DataFrame) -> DataFrame:
        player_mask = df["name"] == player
        df = df[player_mask]
        return df

    def mask_df_to_location_changes(self, df: DataFrame) -> DataFrame:
        change_mask = df["last_place_name"] != df["last_place_name"].shift(1)
        df = df[change_mask]
        return df


def create_event_log(cases: list[Case]) -> EventLog:
    event_log = EventLog()
    event_log.attributes["concept:name"]= "csgo_demo_log"
    for case in cases:
        trace = Trace()
        trace.attributes["concept:name"] = case.name
        for attr, value in case.attributes.items():
            trace.attributes[attr] = value
        for activity in case.trace:
            event = Event()
            event['concept:name'] = activity.name

            # 0.0156 seconds per tick for a 64-tick server
            # 0.0078 seconds per tick for a 128-tick server
            event['time:seconds'] = int(activity.time *  0.0156)
            for attr, value in activity.attributes.items():
                event[attr] = value

            trace.append(event)

        event_log.append(trace)

    return event_log

