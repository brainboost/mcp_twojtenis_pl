import json

from bs4 import BeautifulSoup


def parse_schedule(json_str: str):
    """
    Parses a JSON string containing an HTML 'schedule' field and returns
    a list of badminton courts with half‐hour availability from 07:00 to 22:30.

    Args:
        json_str (str): JSON document as a string.

    Returns:
        list of dict: [
            {
                "number": int,
                "availability": {
                    "07:00": bool,
                    "07:30": bool,
                    ...,
                    "22:30": bool
                }
            }, ...
        ]
    """
    data = json.loads(json_str)
    html = data.get("schedule")
    if not html:
        raise ValueError("Missing 'schedule' field in JSON")

    soup = BeautifulSoup(html, "html.parser")

    # 1. Locate the schedule block for badminton courts
    badminton_div = None
    for sched in soup.find_all("div", class_="schedule"):
        header = sched.find("strong")
        if header and header.get_text().strip().lower().startswith("badminton"):
            badminton_div = sched
            break

    if badminton_div is None:
        raise RuntimeError("Badminton schedule not found in HTML")

    cols = badminton_div.find_all("div", class_="schedule_col")

    # 2. Extract the time axis from the first column
    time_col = cols[0]
    times = [
        elem.get_text().strip() for elem in time_col.find_all("div", class_="hourboxer")
    ]

    courts = []
    # 3. Middle columns represent each badminton court; last column is a mirror of the times
    for col in cols[1:-1]:
        # Court header: e.g. "Badminton 1"
        header = col.find("strong")
        if not header:
            continue
        name = header.get_text().strip()
        # Extract court number from header text
        parts = name.split()
        try:
            number = int(parts[-1])
        except ValueError:
            continue

        # Each .schedule_row corresponds to one timeslot, in the same order as `times`
        rows = col.find_all("div", class_="schedule_row")
        availability = {}
        for t, row in zip(times, rows, strict=False):
            classes = row.get("class", [])  # type: ignore
            # 'reservation_bg' ⇒ available, 'reservation_closed' ⇒ occupied
            available = "reservation_bg" in classes  # type: ignore
            availability[t] = available

        courts.append({"number": number, "availability": availability})

    return courts


if __name__ == "__main__":
    with open("shchedule.json", encoding="utf-8") as f:
        input_json = f.read()

    badminton_courts = parse_schedule(input_json)
    print(json.dumps(badminton_courts, indent=2, ensure_ascii=False))
