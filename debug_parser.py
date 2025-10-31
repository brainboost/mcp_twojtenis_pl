import json

from src.twojtenis_mcp.schedule_parser import ScheduleParser

# Load test input
with open("tests/data/test_input_1.json", encoding="utf-8") as f:
    test_input = json.load(f)

# Parse schedules
result = ScheduleParser.parse_schedules(json_str=json.dumps(test_input))

# Print result for debugging
assert result is not None
print(f"Number of schedules: {len(result)}")

for schedule in result:
    print(schedule["sport"])
    for court in schedule["data"]:
        print(court["number"])
        for time_slot, available in court["availability"].items():
            print(f"  {time_slot}: {available}")
