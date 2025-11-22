from datetime import datetime

def generate_ics_event(day: dict, user_id: int) -> str:
    """
    Convert one training day JSON into an ICS event (Option B).
    """
    date = day["date"]                    # YYYY-MM-DD
    focus = day["workout_focus"]
    start, end = day["scheduled_time_block"].split("-")

    # Format ICS datetime
    dtstart = datetime.fromisoformat(f"{date}T{start}").strftime("%Y%m%dT%H%M")
    dtend = datetime.fromisoformat(f"{date}T{end}").strftime("%Y%m%dT%H%M")

    # Take 4 movements max (for readability)
    movement_lines = []
    for m in day["movements"][:4]:
        movement_lines.append(f"- {m['name']} {m['sets_reps']}")

    movement_text = "\\n".join(movement_lines)

    # Deep link to your app
    # link = f"https://fitai.fit/workout/{user_id}/{date}"

    description = (
        f"{focus}\\n"
        f"Movements:\\n"
        f"{movement_text}\\n\\n"
        f"Full instructions & videos:\\n"
        # f"{link}"
    )

    return f"""BEGIN:VEVENT
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:Workout – {focus}
DESCRIPTION:{description}
END:VEVENT
"""


def generate_ics_calendar(plan: dict, user_id: int) -> str:
    """
    Builds full .ics calendar string for all training days.
    """
    events = []
    for day in plan["training_days"]:
        events.append(generate_ics_event(day, user_id))

    return "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//FitAI Planner//EN\n" + \
           "\n".join(events) + "\nEND:VCALENDAR"
