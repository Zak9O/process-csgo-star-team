from demoparser2 import DemoParser
import pandas as pd


def extract_player_deaths(demo_path: str) -> pd.DataFrame:
    """
    Return every player_death event in the demo, with ALL columns
    provided by demoparser2 for that event.
    """
    parser = DemoParser(demo_path)

    # pull raw kill events
    deaths_df = parser.parse_event("player_death").copy()
    flashbang_df = parser.parse_event("flashbang_detonate").copy()
    print(flashbang_df)
    # handle 'no deaths / not supported'
    if deaths_df is None or len(deaths_df) == 0:
        return pd.DataFrame()

    # sort chronologically
    if "tick" in deaths_df.columns:
        deaths_df = deaths_df.sort_values("tick")
    
    if "tick" in deaths_df.columns:
        flashbang_df = flashbang_df.sort_values("tick")

    deaths_df = deaths_df.reset_index(drop=True)
    return deaths_df


if __name__ == "__main__":
    demo_path = "heroic-vs-3dmax-m1-dust2.dem"

    df_deaths = extract_player_deaths(demo_path)

    # save full detail for inspection
    # df_deaths.to_csv("player_deaths.csv", index=False)

    # print("✅ Saved player_deaths.csv")
    print(df_deaths.head())  # quick preview in console
