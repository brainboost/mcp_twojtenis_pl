import json

from src.twojtenis_mcp.schedule_parser import ScheduleParser

# Load test input
with open("tests/data/badm_021125.json", encoding="utf-8") as f:
    test_input = json.load(f)

html = test_input.get("schedule")

result = ScheduleParser.parse_schedules(html=html)

# Print result for debugging
assert result is not None
print(f"Number of schedules: {len(result)}")

for schedule in result:
    print(schedule["sport"])
    for court in schedule["data"]:
        print(court["number"])
        for time_slot, available in court["availability"].items():
            print(f"  {time_slot}: {available}")
