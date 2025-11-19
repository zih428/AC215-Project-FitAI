# Calendar Agent — Local Test Guide

This README explains how to test the Calendar Agent running inside the
`calendar-agent` Docker service. The service powers two flows:

1. `/process_calendar` — uses GPT-4o Vision to OCR a calendar screenshot.
2. `/planner` — reads a user's profile from Postgres and asks OpenAI to craft
   a training plan that aligns with the detected availability.

---

## 1. Start the Calendar Agent Service

From the project root (where `docker-compose.yml` resides):

```bash
# foreground
docker compose up calendar-agent

# background
docker compose up -d calendar-agent
```

When the service is ready, you should see logs like:

```
Uvicorn running on http://0.0.0.0:8004
Application startup complete.
```

---

## 2. Test Health Endpoint

In a new terminal:

```bash
curl http://localhost:8004/health
```

Expected response:

```json
{"status":"ok"}
```

If this returns `{"status":"ok"}` → Calendar Agent is running.

---

## 3. Prepare a Test Calendar Image

There is a test image at:

```
services/calendar-agent/calendar_image/calendar.png
```

Or use any path — adjust the curl command accordingly.

Verify the file exists:

```bash
ls -al calendar_image
```

---
## 4.1. Test the Process Calendar (read calendar image) API
Test code
```bash
curl -X POST "http://localhost:8004/process_calendar" \
    -F "file=@services/calendar-agent/calendar_image/calendar.png" 
    #replace with the correct path if you are not in root repo
```

## 4.2. Test the Planner API

The planner endpoint expects:

- `user_id`: must exist in Postgres (`users` table). Create/update one via the
  `core-etl-api` service or insert manually.
- `file` *(optional)*: a PNG/JPG calendar screenshot. If omitted, the service
  generates a generic weekly split labeled Day 1, Day 2, etc., without concrete
  timestamps.
- `save_to_db` *(optional, default `false`)*: set to `true` to persist the generated
  plan into the `ml_generated_plans` table.

If the file is elsewhere, use an absolute path:

```bash
curl -X POST "http://localhost:8004/planner" \
    -F "user_id=1" \
    -F "file=@/Users/cefayefang/Projects/AC215-Project-FitAI/services/calendar-agent/calendar_image/calendar.png"
    #-F "save_to_db=true" optional, default is false
```
[Expected output(with_calendar_input)](sexpected_output/user_1_with_calendar.json)

Or you can use relative path if your working directory is at `calendar-agent`:

```bash
curl -X POST "http://localhost:8004/planner" \
    -F "user_id=1" \
    -F "file=@calendar_image/calendar.png"
```

Or omit the file entirely for a template-style plan:

```bash
curl -X POST "http://localhost:8004/planner" \
    -F "user_id=1"
    # -F "save_to_db=true"
```
[Expected output_no_calendar_input](expected_output/user_1_with_calendar.json)

## 4.3. Response Format

The endpoint returns a dictionary with the following shape:

```json
{
  "user": { /* user record from Sql db  (dict) */ },
  "calendar": { /* parsed calendar dict */ } | null,
  "fitness_plan": { /* generated fitness plan dict */ },
  "plan_record": { /* persisted plan DB record */ } | null
}
```

Fields:
- user: user object fetched from Postgres (id, name, metrics, goals, etc.).  
- calendar: parsed calendar data when a file is provided; null if no calendar was parsed.  
- fitness_plan: the generated plan object (summary, training_days, notes).  
- plan_record: the DB record created when save_to_db=true; null if not saved.

## 5.1 Frontend Integration (No Local Path Required)

When a real frontend uploads a calendar screenshot, it does NOT send a file path.
Browsers do not expose a user’s file system path for security reasons.

Instead, the browser sends the file as a Blob via multipart/form-data.

## Example — React / Next.js (client)

```js
// Call from the browser (e.g., a React component)
function uploadCalendar(file, userId) {
    const formData = new FormData();
    formData.append("user_id", userId);
    formData.append("file", file); // file is a Blob/File from <input type="file">

    return fetch("http://localhost:8004/planner", {
        method: "POST",
        body: formData, // Do not set Content-Type; the browser handles it
    })
        .then((res) => res.json());
}
```

Usage in a component:

```jsx
<input
    type="file"
    onChange={(e) => {
        const file = e.target.files?.[0];
        if (file) uploadCalendar(file, "1").then(data => console.log("Planner result:", data));
    }}
/>
```

---


### Expected Output:
#### With Calendar:
```json
{
  "user": {
    "id": 1,
    "full_name": "Avery Chen",
    "height_cm": 170.2,
    "weight_kg": 68.5,
    "body_type": "mesomorph",
    "gender": "female",
    "age_years": 28,
    "training_goal": "build lean muscle"
  },
  "calendar": {
    "events": [
      {
        "title": "Veterans Day",
        "date": "2025-11-11",
        "start": "00:00",
        "end": "23:59",
        "location": null,
        "notes": null,
        "raw_text": "Veterans Day"
      },
      {
        "title": "Faye & Andy",
        "date": "2025-11-11",
        "start": "10:00",
        "end": "11:00",
        "location": null,
        "notes": null,
        "raw_text": "Faye & Andy"
      },
      {
        "title": "Adv Practical Data Science",
        "date": "2025-11-11",
        "start": "11:15",
        "end": "14:15",
        "location": "SEC 1.321",
        "notes": "Lecture",
        "raw_text": "Adv Practical Data Science\nSEC 1.321 Lecture\n11:15AM (2:15PM)"
      },
      {
        "title": "Interview with Faye",
        "date": "2025-11-12",
        "start": "11:00",
        "end": "12:00",
        "location": null,
        "notes": null,
        "raw_text": "Interview with Faye"
      },
      {
        "title": "Adv Practical Data Science",
        "date": "2025-11-12",
        "start": "09:45",
        "end": "12:45",
        "location": "SEC 1.321",
        "notes": "Lecture",
        "raw_text": "Adv Practical Data Science\nSEC 1.321 Lecture\n9:45AM (12:45PM)"
      },
      {
        "title": "Data Science 1",
        "date": "2025-11-12",
        "start": "14:00",
        "end": "15:00",
        "location": "SEC 2.118",
        "notes": "Class",
        "raw_text": "Data Science 1\nSEC 2.118 Class"
      },
      {
        "title": "Intro to Linear Models",
        "date": "2025-11-13",
        "start": "14:00",
        "end": "15:00",
        "location": null,
        "notes": null,
        "raw_text": "Intro to Linear Models"
      },
      {
        "title": "FitAI",
        "date": "2025-11-14",
        "start": "16:00",
        "end": "17:00",
        "location": "harvard.zoom.us",
        "notes": null,
        "raw_text": "FitAI\nharvard.zoom.us"
      }
    ],
    "metadata": {
      "source_type": "calendar_screenshot",
      "confidence": 0.95,
      "missing_fields_filled": []
    }
  },
  "fitness_plan": {
    "plan_summary": "This plan focuses on building lean muscle with a 3-day split...",
    "training_days": [
      {
        "date": "2025-11-11",
        "day_of_week": "Tuesday",
        "available_time_blocks": ["00:00-10:00", "14:15-23:59"],
        "scheduled_time_block": "14:15-15:15",
        "schedule_reason": "Available after class; shorter session due to class schedule.",
        "workout_focus": "Upper Body Strength",
        "movements": [
          {
            "name": "Barbell Bench Press",
            "sets_reps": "3x8 @ RPE 7",
            "equipment": "Barbell, Bench",
            "coaching_notes": "Focus on controlled descent..."
          },
          {
            "name": "Bent-Over Row",
            "sets_reps": "3x8 @ RPE 7",
            "equipment": "Barbell",
            "coaching_notes": "Maintain a flat back..."
          },
          {
            "name": "Overhead Press",
            "sets_reps": "3x8 @ RPE 7",
            "equipment": "Barbell",
            "coaching_notes": "Engage your core..."
          },
          {
            "name": "Dumbbell Bicep Curl",
            "sets_reps": "3x10 @ RPE 6",
            "equipment": "Dumbbells",
            "coaching_notes": "Control the eccentric phase..."
          }
        ],
        "conditioning_or_cardio": null,
        "recovery": "Foam roll chest, back, and shoulders for 10 minutes."
      },
      {
        "date": "2025-11-13",
        "day_of_week": "Thursday",
        "available_time_blocks": ["00:00-14:00", "15:00-23:59"],
        "scheduled_time_block": "15:00-16:30",
        "schedule_reason": "Fits best after scheduled meetings.",
        "workout_focus": "Lower Body Strength",
        "movements": [
          {
            "name": "Barbell Back Squat",
            "sets_reps": "4x8 @ RPE 8",
            "equipment": "Barbell, Squat Rack",
            "coaching_notes": "Maintain proper form..."
          },
          {
            "name": "Romanian Deadlift",
            "sets_reps": "3x10 @ RPE 7",
            "equipment": "Barbell",
            "coaching_notes": "Keep your back straight..."
          },
          {
            "name": "Leg Press",
            "sets_reps": "3x12 @ RPE 6",
            "equipment": "Leg Press Machine",
            "coaching_notes": "Ensure full range of motion."
          },
          {
            "name": "Standing Calf Raise",
            "sets_reps": "4x15 @ RPE 6",
            "equipment": "Calf Raise Machine or Dumbbells",
            "coaching_notes": "Squeeze at the top."
          }
        ],
        "conditioning_or_cardio": null,
        "recovery": "Stretch quads, hamstrings, and calves for 10 minutes."
      },
      {
        "date": "2025-11-14",
        "day_of_week": "Friday",
        "available_time_blocks": ["00:00-16:00", "17:00-23:59"],
        "scheduled_time_block": "17:00-18:00",
        "schedule_reason": "Scheduled after FitAI meeting.",
        "workout_focus": "Full Body Hypertrophy",
        "movements": [
          {
            "name": "Dumbbell Walking Lunge",
            "sets_reps": "3x10 @ RPE 7",
            "equipment": "Dumbbells",
            "coaching_notes": "Maintain balance..."
          },
          {
            "name": "Push-Ups",
            "sets_reps": "3xFailure @ RPE 8",
            "equipment": "None",
            "coaching_notes": "Maintain a straight line..."
          },
          {
            "name": "Dumbbell Shoulder Press",
            "sets_reps": "3x10 @ RPE 7",
            "equipment": "Dumbbells",
            "coaching_notes": "Control the eccentric phase..."
          },
          {
            "name": "Dumbbell Goblet Squat",
            "sets_reps": "3x10 @ RPE 7",
            "equipment": "Dumbbell",
            "coaching_notes": "Keep the dumbbell close..."
          }
        ],
        "conditioning_or_cardio": null,
        "recovery": "Full body stretching for 15 minutes."
      }
    ],
    "recovery_notes": "Prioritize sleep and hydration...",
    "nutrition_notes": "Ensure adequate protein intake..."
  }
}
```
#### Without Calendar
```json
{
  "user": {
    "id": 1,
    "full_name": "Avery Chen",
    "height_cm": 170.2,
    "weight_kg": 68.5,
    "body_type": "mesomorph",
    "gender": "female",
    "age_years": 28,
    "training_goal": "build lean muscle"
  },
  "calendar": null,
  "fitness_plan": {
    "plan_summary": "This plan is designed to build lean muscle, focusing on compound movements and hypertrophy-specific rep ranges. It incorporates a 3-day split targeting major muscle groups with adequate recovery.",
    "training_days": [
      {
        "day_of_week": "Monday",
        "workout_focus": "Upper Body Strength",
        "movements": [
          {
            "name": "Barbell Bench Press",
            "sets_reps": "4x8 @ RPE 8",
            "equipment": "Barbell, Bench",
            "coaching_notes": "Focus on controlled descent and explosive concentric movement."
          },
          {
            "name": "Bent-Over Row",
            "sets_reps": "3x10 @ RPE 7",
            "equipment": "Barbell",
            "coaching_notes": "Maintain a flat back and pull the bar towards your lower chest."
          },
          {
            "name": "Overhead Press",
            "sets_reps": "3x8 @ RPE 7",
            "equipment": "Barbell",
            "coaching_notes": "Engage core for stability and press the bar overhead in a controlled manner."
          },
          {
            "name": "Pull-ups",
            "sets_reps": "3xAMRAP @ RPE 8",
            "equipment": "Pull-up Bar",
            "coaching_notes": "If unable to perform pull-ups, use an assisted pull-up machine."
          }
        ],
        "conditioning_or_cardio": "20 minutes of incline walking on treadmill",
        "recovery": "Foam roll upper back and shoulders"
      },
      {
        "day_of_week": "Wednesday",
        "workout_focus": "Lower Body Strength",
        "movements": [
          {
            "name": "Barbell Back Squat",
            "sets_reps": "4x6 @ RPE 8",
            "equipment": "Barbell, Squat Rack",
            "coaching_notes": "Maintain a neutral spine and control the depth of the squat."
          },
          {
            "name": "Romanian Deadlift",
            "sets_reps": "3x10 @ RPE 7",
            "equipment": "Barbell",
            "coaching_notes": "Keep legs straight and focus on hamstring stretch."
          },
          {
            "name": "Leg Press",
            "sets_reps": "3x12 @ RPE 7",
            "equipment": "Leg Press Machine",
            "coaching_notes": "Full range of motion, controlled tempo."
          },
          {
            "name": "Calf Raises",
            "sets_reps": "4x15 @ RPE 6",
            "equipment": "Calf Raise Machine or Dumbbells",
            "coaching_notes": "Focus on full contraction and stretch of the calf muscles."
          }
        ],
        "conditioning_or_cardio": "None",
        "recovery": "Static stretching of quads and hamstrings"
      },
      {
        "day_of_week": "Friday",
        "workout_focus": "Full Body Hypertrophy",
        "movements": [
          {
            "name": "Dumbbell Bench Press",
            "sets_reps": "3x10 @ RPE 7",
            "equipment": "Dumbbells, Bench",
            "coaching_notes": "Focus on controlled movement and chest activation."
          },
          {
            "name": "Dumbbell Rows",
            "sets_reps": "3x10 @ RPE 7",
            "equipment": "Dumbbells, Bench",
            "coaching_notes": "Support body with one arm on the bench, pull the dumbbell towards your hip."
          },
          {
            "name": "Dumbbell Shoulder Press",
            "sets_reps": "3x10 @ RPE 7",
            "equipment": "Dumbbells",
            "coaching_notes": "Control the dumbbells, focus on shoulder muscle activation."
          },
          {
            "name": "Goblet Squat",
            "sets_reps": "3x12 @ RPE 7",
            "equipment": "Dumbbell or Kettlebell",
            "coaching_notes": "Hold the weight close to your chest, squat with proper form."
          },
          {
            "name": "Dumbbell Bicep Curls",
            "sets_reps": "3x12 @ RPE 7",
            "equipment": "Dumbbells",
            "coaching_notes": "Control the movement, focus on bicep contraction."
          },
          {
            "name": "Dumbbell Tricep Extensions",
            "sets_reps": "3x12 @ RPE 7",
            "equipment": "Dumbbells",
            "coaching_notes": "Keep elbows stable, focus on tricep contraction."
          }
        ],
        "conditioning_or_cardio": "20 minutes of cycling",
        "recovery": "Light stretching and mobility exercises"
      }
    ],
    "recovery_notes": "Prioritize sleep and hydration. Consider active recovery on off days.",
    "nutrition_notes": "Focus on a balanced diet with adequate protein intake to support muscle growth. Aim for 1.6-2.2 grams of protein per kilogram of body weight."
  }
}
```

---

## Troubleshooting

1) curl: (26) Failed to open/read local data  
- File path is likely wrong. Check:

```bash
ls -al calendar_image
```

Or use the absolute path.

2) curl: (7) Failed to connect  
- Service not running. Verify with:

```bash
docker ps
```

You should see a container mapping like: `0.0.0.0:8004->8004/tcp`. If not, start:

```bash
docker compose up calendar-agent
```

3) View service logs:

```bash
docker compose logs -f calendar-agent
```