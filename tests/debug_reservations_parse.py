from src.twojtenis_mcp.schedule_parser import ScheduleParser

with open("tests/data/reservations.html", encoding="utf-8") as f:
    data = f.read()

result = ScheduleParser.parse_reservations(input=data)

assert result is not None
print(f"Number of reservations: {len(result)}")

for resrv in result:
    print(resrv)
