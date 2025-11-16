from src.twojtenis_mcp.schedule_parser import ScheduleParser

# Load test input
with open("tests/data/blonia_sport.html", encoding="utf-8") as f:
    data = f.read()

result = ScheduleParser.parse_schedules(html=data)

# Print result for debugging
assert result is not None
print(f"Number of schedules: {len(result)}")

for schedule in result:
    print(schedule["sport"])
    for court in schedule["data"]:
        print(court["number"])
        for time_slot, available in court["availability"].items():
            print(f"  {time_slot}: {available}")

info = ScheduleParser.parse_club_info(html=data)
if info is not None:
    print(info)
