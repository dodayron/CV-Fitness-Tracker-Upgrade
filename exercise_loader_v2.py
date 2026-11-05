import json
import os
# CHANGE: Importing from the v2 file
from exercise_v2 import Exercise

def load_exercise(name):
    # CHANGE: Loading the v2 json file
    json_file = "exercises_v2.json"
    
    if not os.path.exists(json_file):
         raise FileNotFoundError(f"{json_file} not found")

    with open(json_file, "r") as f:
        configs = json.load(f)

    if name not in configs:
        raise ValueError(f"Unknown exercise: {name}")

    return Exercise(configs[name])
