import importlib.util
from pathlib import Path

ics_path = Path(__file__).resolve().parents[1] / "ics_generator.py"
spec = importlib.util.spec_from_file_location("ics_module", ics_path)
ics = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(ics)


def test_generate_event_includes_summary_and_times():
    day = {
        "date": "2024-01-02",
        "scheduled_time_block": "07:00-08:00",
        "workout_focus": "Legs",
        "movements": [
            {"name": "Back Squat", "sets_reps": "3x5", "equipment": "barbell", "coaching_notes": ""},
            {"name": "Lunge", "sets_reps": "3x10", "equipment": "dumbbell", "coaching_notes": ""},
        ],
        "conditioning_or_cardio": None,
        "recovery": "stretch",
    }

    event = ics.generate_ics_event(day, user_id=1)

    assert "DTSTART:20240102T0700" in event
    assert "SUMMARY:Workout" in event
    assert "- Back Squat 3x5" in event


def test_generate_calendar_wraps_events():
    plan = {"training_days": []}
    for idx in range(2):
        plan["training_days"].append(
            {
                "date": f"2024-01-0{idx+1}",
                "scheduled_time_block": "07:00-08:00",
                "workout_focus": "Full Body",
                "movements": [{"name": "Pushup", "sets_reps": "3x10", "equipment": None, "coaching_notes": ""}],
                "conditioning_or_cardio": None,
                "recovery": "stretch",
            }
        )

    ics_text = ics.generate_ics_calendar(plan, user_id=7)

    assert ics_text.startswith("BEGIN:VCALENDAR")
    assert ics_text.strip().endswith("END:VCALENDAR")
    assert ics_text.count("BEGIN:VEVENT") == 2
