from demoparser2 import DemoParser
import pandas as pd
import numpy as np
from collections import defaultdict
import math
import os
from pathlib import Path

# directory containing .dem files
DEMOS_DIR = "demo_files"
ASSUMED_TPS = 64

def _dist_point_to_aabb(px, py, pz, minx, miny, minz, maxx, maxy, maxz):
    """Euclidean distance from point to AABB (0 if inside)."""
    dx = 0.0
    if px < minx:
        dx = minx - px
    elif px > maxx:
        dx = px - maxx

    dy = 0.0
    if py < miny:
        dy = miny - py
    elif py > maxy:
        dy = py - maxy

    dz = 0.0
    if pz < minz:
        dz = minz - pz
    elif pz > maxz:
        dz = pz - maxz

    return math.sqrt(dx*dx + dy*dy + dz*dz)

def point_to_place_name(x, y, z):
    """
    Return the place_name whose bounding box is nearest to (x,y,z).
    If the point is inside any box the distance is 0 and that box will be returned.
    """
    boxes = [
        ("TSpawn", (-1784.000122, -1247.999969, -48.000015), (536.000122, -616.000031, 254.400009)),
        ("TSpawn", (-1776.000092, -648.000000, 116.000000), (-879.999908, -136.000000, 284.000000)),
        ("TRamp", (-2264.000000, -1072.000000, -24.000000), (-1776.000000, -95.999878, 296.000000)),
        ("OutsideTunnel", (-2056.000000, -128.000000, -5.000000), (-1208.000000, 704.000000, 296.000000)),
        ("UpperTunnel", (-1720.000000, 704.000000, 32.000000), (-1600.000000, 960.000000, 248.000000)),
        ("UpperTunnel", (-2199.999969, 1039.999969, 24.000000), (-1288.000031, 1408.000031, 408.000000)),
        ("UpperTunnel", (-1296.000015, 1168.000000, 48.000000), (-1159.999985, 1272.000000, 392.000000)),
        ("UpperTunnel", (-1176.000000, 1167.999878, 32.000000), (-1152.000000, 1279.999878, 408.000000)),
        ("UpperTunnel", (-1296.000015, 1152.000000, 40.000000), (-1151.999985, 1168.000000, 392.000000)),
        ("TunnelStairs", (-1280.000000, 1032.000000, 0.000000), (-1152.000000, 1152.000000, 408.000000)),
        ("TunnelStairs", (-1176.000000, 1048.000000, -16.000000), (-1072.000000, 1168.000000, 432.000062)),
        ("TunnelStairs", (-1152.000000, 1048.000000, -120.000000), (-1024.000000, 1272.000000, 544.000000)),
        ("LowerTunnel", (-1232.000000, 1272.000000, -112.000000), (-512.000000, 1544.000000, 112.000000)),
        ("Middle", (-508.000000, 767.999939, -128.000000), (-260.000000, 1504.000061, 248.000062)),
        ("TopofMid", (-760.000000, -616.000000, 0.000000), (64.000000, 768.000000, 544.000000)),
        ("OutsideLong", (64.000000, -624.000000, 0.000000), (768.000000, 248.000000, 248.000000)),
        ("OutsideLong", (64.000000, 248.000000, 0.000000), (480.000000, 480.000000, 248.000000)),
        ("LongDoors", (504.000000, 247.999969, 0.000000), (1272.000000, 1216.000031, 256.000000)),
        ("LongDoors", (944.000000, 192.000000, 8.000000), (1248.000000, 248.000000, 256.000000)),
        ("LongA", (1248.000000, 783.999878, -8.000000), (1608.000000, 2304.000122, 320.000000)),
        ("LongA", (1608.000000, 1399.999939, 0.000000), (1792.000000, 2288.000061, 256.000000)),
        ("ARamp", (1279.999969, 2304.000000, -8.000000), (1640.000031, 3088.000000, 328.000000)),
        ("BombsiteA", (800.000015, 2400.000000, 96.000000), (1279.999985, 3096.000000, 328.000000)),
        ("BombsiteA", (1024.000000, 2304.000000, 96.000000), (1288.000000, 2408.000000, 256.000000)),
        ("UnderA", (536.000000, 2008.000000, -144.000000), (1248.000000, 2304.000000, 320.000000)),
        ("UnderA", (536.000031, 2304.000000, -136.000031), (1023.999969, 2400.000000, 320.000000)),
        ("ExtendedA", (256.000000, 2400.000000, 96.000000), (800.000000, 2784.000000, 328.000000)),
        ("ExtendedA", (256.000000, 1960.000000, 96.000000), (536.000000, 2400.000000, 328.000000)),
        ("ShortStairs", (256.000008, 1327.999939, -8.000000), (511.999992, 1960.000061, 328.000000)),
        ("Catwalk", (-256.000000, 1319.999969, 0.000000), (256.000000, 1600.000031, 328.000000)),
        ("Catwalk", (-256.000000, 768.000031, 0.000000), (-72.000000, 1319.999969, 328.000000)),
        ("MidDoors", (-512.000000, 1504.000183, -128.000000), (-256.000000, 2568.000061, 320.000000)),
        ("MidDoors", (-743.999992, 1648.000031, -120.000008), (-512.000008, 2607.999969, 319.999992)),
        ("BDoors", (-1344.000000, 2040.000000, -40.000000), (-744.000000, 2592.000000, 312.000000)),
        ("CTSpawn", (-256.000000, 1983.999939, -128.000000), (535.999938, 2568.000061, 80.000000)),
        ("BDoors", (-1231.999901, 2592.000000, -40.000000), (-1047.999855, 2720.000000, 312.000000)),
        ("Hole", (-1400.000000, 2600.000000, -40.000000), (-1232.000000, 2720.000000, 472.000000)),
        ("BombsiteB", (-2204.000153, 1800.000000, -8.000000), (-1344.000092, 2600.000000, 448.000000)),
        ("BombsiteB", (-2119.999817, 2719.999969, 32.000000), (-1327.999939, 3136.000031, 448.000000)),
        ("BombsiteB", (-2127.999969, 2600.000004, 32.000000), (-1400.000031, 2719.999996, 448.000000)),
        ("UpperTunnel", (-2048.000000, 1408.000000, 32.000000), (-1920.000000, 1800.000000, 288.000000)),
        ("Pit", (1272.000000, 128.000000, -232.000000), (1600.000000, 784.000000, 264.000000)),
        ("Side", (1608.000000, 312.000122, -8.000000), (1808.000000, 1040.000122, 264.000000)),
    ]

    best_name = None
    best_dist = float("inf")

    for name, (minx, miny, minz), (maxx, maxy, maxz) in boxes:
        d = _dist_point_to_aabb(x, y, z, minx, miny, minz, maxx, maxy, maxz)
        if d < best_dist:
            best_dist = d
            best_name = name

    return best_name

# ---- per-demo processing ----
def process_demo(demo_path):
    """
    Parse a single demo and return the list of rounds (each round is a dict tick -> list-of-events).
    """
    parser = DemoParser(demo_path)

    # ticks and last-place/team maps
    ticks = parser.parse_ticks(["tick", "name", "team_name", "is_alive", "last_place_name", "bomb_exploded"])

    _name_to_tick_arr = {}
    _name_to_team_arr = {}
    _name_to_place_arr = {}
    for name, grp in ticks.groupby("name", sort=False):
        _name_to_tick_arr[name] = grp["tick"].values
        _name_to_team_arr[name] = grp["team_name"].fillna("").values
        _name_to_place_arr[name] = grp["last_place_name"].fillna("").values

    def team_at_tick(name, tick):
        if not isinstance(name, str) or name not in _name_to_tick_arr: return None
        arr = _name_to_tick_arr[name]; idx = np.searchsorted(arr, tick, side="right") - 1
        if idx < 0: return None
        raw = _name_to_team_arr[name][idx]
        if not isinstance(raw, str) or raw == "": return None
        ru = raw.upper()
        if ru.startswith("CT"): return "CT"
        if ru.startswith("T"): return "T"
        return None

    def place_at_tick_local(name, tick):
        if not isinstance(name, str) or name not in _name_to_tick_arr: return None
        arr = _name_to_tick_arr[name]; idx = np.searchsorted(arr, tick, side="right") - 1
        if idx < 0: return None
        p = _name_to_place_arr[name][idx]
        return p if isinstance(p, str) and p != "" else None

    # local read_event bound to this parser
    def read_event(name):
        raw = None
        try:
            raw = parser.parse_event(name)
        except Exception:
            return pd.DataFrame()
        if isinstance(raw, pd.DataFrame): return raw.copy()
        if isinstance(raw, list):
            try: return pd.DataFrame(raw)
            except Exception: return pd.DataFrame([x if isinstance(x, dict) else {"v": x} for x in raw])
        if isinstance(raw, dict): return pd.DataFrame([raw])
        return pd.DataFrame()

    # read events
    round_start_df = read_event("round_start")
    round_end_df   = read_event("round_end")
    plants_df      = read_event("bomb_planted")
    purchases_df   = read_event("item_purchase")
    deaths_df      = read_event("player_death")
    hurt_df        = read_event("player_hurt")

    for df in (deaths_df, purchases_df, plants_df, round_start_df, round_end_df):
        if not df.empty and "tick" in df.columns:
            df.sort_values("tick", inplace=True)

    # grenades
    GRENADE_EVENTS = ["hegrenade_detonate","flashbang_detonate","smokegrenade_detonate","smokegrenade_expired",
                      "molotov_detonate","decoy_detonate","decoy_started","tagrenade_detonate"]
    _gs = []
    for ev in GRENADE_EVENTS:
        gr = read_event(ev)
        if gr.empty: continue
        gr = gr.copy(); gr["event_name"] = ev
        _gs.append(gr)
    grenades_df = pd.concat(_gs, ignore_index=True) if _gs else pd.DataFrame(columns=["tick","event_name"])

    # round intervals
    round_starts = list(round_start_df["tick"]) if ("tick" in round_start_df.columns and not round_start_df.empty) else []
    round_ends   = list(round_end_df["tick"])   if ("tick" in round_end_df.columns and not round_end_df.empty) else []

    PRICE_MAP = {"ak47":2700,"m4a1":3100,"m4a4":3100,"awp":4750,"ssg08":1700,"aug":3300,"sg556":3000,"famas":2250,
                 "galil":2000,"mp9":1250,"mp7":1700,"ump45":1200,"p90":2350,"xm1014":2000,"mag7":1800,"nova":1050,
                 "negev":1700,"m249":5200,"deserteagle":700,"deagle":700,"usp":200,"glock":200,"p250":300,"cz75":500,
                 "revolver":600,"knife":0,"kevlar":650,"helmet":350,"defuser":400,"hegrenade":300,"flashbang":200,"smokegrenade":300}

    def _get_price_from_purchase_row(row):
        for c in ("price","cost","item_cost"):
            if c in row and pd.notna(row[c]):
                try: return int(row[c])
                except: pass
        for c in ("weapon","item","weapon_name","classname"):
            if c in row and pd.notna(row[c]):
                w = str(row[c]).lower().replace("weapon_","").replace("weapon","").replace(" ","").replace("-","").replace("_","")
                if w in PRICE_MAP: return PRICE_MAP[w]
                for k in PRICE_MAP:
                    if k in w: return PRICE_MAP[k]
        return 0

    # core builder (very similar to your previous implementation but bound to local variables)
    def getListOfActivitiesPerRound(max_rounds: int = 5):
        # robustly match each start to the first following end tick (avoid index errors)
        if not round_starts or not round_ends:
            return []

        # build intervals by finding for each start the first end >= start
        intervals = []
        for s in round_starts:
            # find first end tick >= s
            candidate = None
            for e in round_ends:
                if e >= s:
                    candidate = e
                    break
            if candidate is not None:
                intervals.append((s, candidate))
            # if no candidate found: skip this start (corrupt/partial data)

        if not intervals:
            return []

        # apply max_rounds limit
        limit = min(max_rounds, len(intervals))
        intervals = intervals[:limit]

        out = []
        for start_tick, end_tick in intervals:
            log_i = defaultdict(list)
            log_i[start_tick].append(("round","round_start","round_start"))

            # deaths
            if not deaths_df.empty and "tick" in deaths_df.columns:
                rdeaths = deaths_df[(deaths_df["tick"]>=start_tick)&(deaths_df["tick"]<=end_tick)].sort_values("tick")
                for _, row in rdeaths.iterrows():
                    d_tick = int(row["tick"])
                    # inline first-of logic: prefer user_name, then userid_name, then name
                    victim = row.get("user_name")
                    team = team_at_tick(victim, d_tick) if isinstance(victim, str) else None
                    val = f"{team}_Died" if team in ("CT","T") else "Died"
                    log_i[d_tick].append((victim, "player_death", val))

            # bomb planted
            if not plants_df.empty and "tick" in plants_df.columns:
                rplants = plants_df[(plants_df["tick"]>=start_tick)&(plants_df["tick"]<=end_tick)]
                for _, r in rplants.iterrows():
                    pt = int(r["tick"])
                    planter = r.get("user_name")
                    site = place_at_tick_local(planter, pt)
                    log_i[pt].append(("round","bomb_planted", f"bomb_planted|{site}" if site else "bomb_planted"))

            # purchases -> spent
            spent_CT = spent_T = 0
            if not purchases_df.empty and "tick" in purchases_df.columns:
                rbuys = purchases_df[(purchases_df["tick"]>=start_tick)&(purchases_df["tick"]<=end_tick)]
                if not rbuys.empty:
                    prices = rbuys.apply(_get_price_from_purchase_row, axis=1)
                    if "user_name" in rbuys.columns:
                        buyers = rbuys["user_name"].copy()
                        if "name" in rbuys.columns: buyers = buyers.fillna(rbuys["name"])
                    elif "name" in rbuys.columns:
                        buyers = rbuys["name"].copy()
                    else:
                        buyers = pd.Series([None]*len(rbuys), index=rbuys.index)
                    for price, buyer, bt in zip(prices, buyers, rbuys["tick"]):
                        if not isinstance(buyer, str): continue
                        team = team_at_tick(buyer, int(bt))
                        if team == "CT": spent_CT += int(price)
                        elif team == "T": spent_T += int(price)

            # hurt -> damage
            if not hurt_df.empty and "tick" in hurt_df.columns:
                rh = hurt_df[(hurt_df["tick"]>=start_tick)&(hurt_df["tick"]<=end_tick)]
                for _, row in rh.iterrows():
                    weapon = str(row.get("weapon","")).lower()
                    # prefer userid_name or user_name (some parsers differ)
                    victim = row.get("userid_name") or row.get("user_name") or row.get("name")
                    t = int(row["tick"]); team = team_at_tick(victim, t)
                    dmg = None
                    for dmg_col in ("dmg_health", "damage", "dmg", "hitgroup_damage"):
                        if dmg_col in row and pd.notna(row[dmg_col]):
                            try:
                                dmg = int(row[dmg_col])
                            except Exception:
                                try:
                                    dmg = int(float(row[dmg_col]))
                                except Exception:
                                    dmg = 0
                            break
                    # compute last place name for the victim at this tick
                    last_place = place_at_tick_local(victim, t) if isinstance(victim, str) else None
                    last_place = last_place if last_place else ""
                    # skip if no valid victim or zero damage
                    if not isinstance(victim, str) or not dmg:
                        continue
                    util_types = ["hegrenade","molotov","inferno","incgrenade","grenade","flashbang","smokegrenade","decoy"]
                    exc = ["fall","world","unknown"]
                    # detect which utility caused the damage (if any)
                    util_kind = ""
                    for u in util_types:
                        if u in weapon:
                            util_kind = u
                            break

                    if any(x in weapon for x in util_types):
                        tag = f"{team}_took_utility_damage" if team in ("CT","T") else "took_utility_damage"
                        extra = {
                            "damage": int(dmg),
                            "last_place_name": last_place,
                            "utility_kind": util_kind
                        }
                        log_i[t].append((victim,"utility_damage",tag,extra))
                    elif not any(x in weapon for x in util_types+exc):
                        tag = f"{team}_took_weapon_damage" if team in ("CT","T") else "took_weapon_damage"
                        extra = {
                            "damage": int(dmg),
                            "last_place_name": last_place,
                            "utility_kind": ""
                        }
                        log_i[t].append((victim,"weapon_damage",tag,extra))

            # first kill (simplified)
            if not deaths_df.empty and "tick" in deaths_df.columns:
                rdeaths = deaths_df[(deaths_df["tick"]>=start_tick)&(deaths_df["tick"]<=end_tick)].sort_values("tick")
            else:
                rdeaths = pd.DataFrame()
            if 'rdeaths' in locals() and not rdeaths.empty:
                fk = rdeaths.iloc[0]; fk_tick = int(fk["tick"])
                killer = fk.get("attacker_name")
                victim = fk.get("user_name")
                team_k = team_at_tick(killer, fk_tick) if isinstance(killer, str) else None
                # find weapon from available columns
                weapon_fk = None
                for kcol in ("weapon","weapon_name","attacker_weapon","killer_weapon","weaponid"):
                    if kcol in fk and pd.notna(fk[kcol]):
                        weapon_fk = fk[kcol]
                        break
                # place at tick for victim
                place_fk = place_at_tick_local(victim, fk_tick) if isinstance(victim, str) else None
                if team_k in ("CT","T"):
                    extra = {"first_kill_place": place_fk, "killer_weapon": weapon_fk}
                    log_i[fk_tick].append(("round","first_kill",f"first_kill_{team_k}", extra))

            # utility_exploded from grenades
            if not grenades_df.empty and "tick" in grenades_df.columns:
                rgren = grenades_df[(grenades_df["tick"]>=start_tick)&(grenades_df["tick"]<=end_tick)].sort_values("tick")
                for _, gr in rgren.iterrows():
                    gt = int(gr["tick"])
                    ev = str(gr.get("event_name","grenade")).lower()
                    x = float(gr.get("x", 0.0))
                    y = float(gr.get("y", 0.0))
                    z = float(gr.get("z", 0.0))
                    thrower = None
                    for col in ("user_name", "userid_name", "attacker_name", "name"):
                        if col in gr and pd.notna(gr[col]) and str(gr[col]).strip() != "":
                            thrower = str(gr[col])
                            break
                    thrower_team = None
                    if isinstance(thrower, str):
                        thrower_team = team_at_tick(thrower, gt)  # returns 'CT', 'T' or None
                    place = point_to_place_name(x, y, z)
                    extra = {
                        "grenade_type": ev,
                        "place_exploded": place,
                        "thrower_team": thrower_team
                    }
                    log_i[gt].append(("round","utility_exploded",f"utility_exploded_{thrower_team}", extra))

            # round end metadata
            winner = "UNKNOWN"; reason = "UNKNOWN"
            if not round_end_df.empty and "tick" in round_end_df.columns:
                er = round_end_df[round_end_df["tick"]==end_tick]
                if not er.empty:
                    er0 = er.iloc[0]
                    try:
                        w = int(er0.get("winner","")); winner = "T" if w==2 else "CT" if w==3 else str(w)
                    except Exception:
                        winner = str(er0.get("winner","UNKNOWN"))
                    reason = str(er0.get("reason","UNKNOWN"))
            winner_spent = spent_T if winner=="T" else (spent_CT if winner=="CT" else 0)
            log_i[end_tick].append(("round","round_end",f"round_end|winner={winner}",{"winner_spent":int(winner_spent),"round_end_reason":reason}))

            out.append({k: log_i[k] for k in sorted(log_i.keys())})
        return out

    # run and return
    rounds = getListOfActivitiesPerRound(max_rounds=9999)
    return rounds

if __name__ == "__main__":
    demo_dir = Path(DEMOS_DIR)
    if not demo_dir.exists() or not demo_dir.is_dir():
        print(f"Demo directory '{DEMOS_DIR}' does not exist.")
    else:
        demo_files = sorted([p for p in demo_dir.iterdir() if p.suffix.lower() == ".dem"])
        if not demo_files:
            print(f"No .dem files found in {DEMOS_DIR}")
        for demo in demo_files:
            print(f"\nProcessing demo: {demo.name} ...")
            try:
                rounds = process_demo(str(demo))
                print(f" Built {len(rounds)} rounds for {demo.name}")
            except Exception as e:
                print(f" Error while processing {demo.name}: {e}")
