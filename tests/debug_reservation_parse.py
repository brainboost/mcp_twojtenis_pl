from src.twojtenis_mcp.schedule_parser import ScheduleParser

with open("tests/data/reservation.html", encoding="utf-8") as f:
    data = f.read()

result = ScheduleParser.parse_reservation(input=data)

assert result is not None
print(result)
