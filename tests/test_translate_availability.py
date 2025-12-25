"""Test script for translate_availability function."""

from src.twojtenis_mcp.schedule_parser import ScheduleParser


def test_translate_availability():
    """Test the translate_availability function with the example from the task."""

    # Input from the task example
    input_data = {
        "07:00": 0,
        "07:30": 2,
        "08:00": 0,
        "08:30": 0,
        "09:00": 1,
        "09:30": 1,
        "10:00": 4,
        "10:30": 0,
        "11:00": 0,
        "11:30": 0,
    }

    # Expected output from the task example
    expected_output = {
        "07:00": True,
        "07:30": False,
        "08:00": False,
        "08:30": True,
        "09:00": False,
        "09:30": False,
        "10:00": False,
        "10:30": False,
        "11:00": False,
        "11:30": False,
    }

    # Call the function
    result = ScheduleParser._translate_availability(input_data)

    # Print results
    print("Input:")
    for time, value in input_data.items():
        print(f"  {time}: {value}")

    print("\nExpected Output:")
    for time, value in expected_output.items():
        print(f"  {time}: {value}")

    print("\nActual Output:")
    for time, value in result.items():
        print(f"  {time}: {value}")

    # Check if the result matches the expected output
    if result == expected_output:
        print("\n✅ Test PASSED!")
    else:
        print("\n❌ Test FAILED!")
        print("Differences:")
        for time in expected_output:
            if expected_output[time] != result.get(time):
                print(
                    f"  {time}: expected {expected_output[time]}, got {result.get(time)}"
                )


if __name__ == "__main__":
    test_translate_availability()
