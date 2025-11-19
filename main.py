# main.py
from pathlib import Path
from CreateXESfile import CreateXES
from CreateLog import process_demo

DEMOS_DIR = "demo_files"         
OUT_XES = "csgo_EventLog.xes"       

all_rounds = []  

demo_dir = Path(DEMOS_DIR)
demo_files = sorted([p for p in demo_dir.iterdir() if p.suffix.lower() == ".dem"])

print(f"Found {len(demo_files)} demo(s). Processing...")

for demo_path in demo_files:
    print(f"Processing {demo_path.name} ...")
    rounds = process_demo(str(demo_path))
    print(f" -> built {len(rounds)} rounds from {demo_path.name}")
    all_rounds.extend(rounds)

print(f"Total rounds collected: {len(all_rounds)}")
print("Creating XES...")
event_log = CreateXES(all_rounds)  
print("Done. Log created successfully")
