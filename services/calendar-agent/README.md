# Calendar Agent — Local Test Guide

This README explains how to test the hard-coded Planner API running inside the `calendar-agent` Docker service.

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
calendar-agent/calendar_image/calendar.png
```

Or use any path — adjust the curl command accordingly.

Verify the file exists:

```bash
ls -al calendar_image
```

---

## 4. Test the Hard-Coded Planner API


If the file is elsewhere, use an absolute path:

```bash
curl -X POST "http://localhost:8004/planner" \
    -F "user_id=12345" \
    -F "file=@/Users/cefayefang/Projects/AC215-Project-FitAI/services/calendar-agent/calendar_image/calendar.png"
```

Or you can use relative path if your working directory is at `calendar-agent`:

```bash
curl -X POST "http://localhost:8004/planner" \
    -F "user_id=12345" \
    -F "file=@calendar_image/calendar.png"
```


## 4.1 Frontend Integration (No Local Path Required)

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
        if (file) uploadCalendar(file, "12345").then(data => console.log("Planner result:", data));
    }}
/>
```

----
## 5. Expected Response (Hard-Coded JSON)

```json
{
    "user_id": "12345",
    "events": [
        {
            "title": "Workout Session",
            "date": "2025-11-14",
            "start": "08:00",
            "end": "09:00",
            "location": "Gym",
            "notes": "Leg day"
        },
        {
            "title": "Team Meeting",
            "date": "2025-11-14",
            "start": "14:00",
            "end": "15:00",
            "location": "Office",
            "notes": null
        }
    ]
}
```

This confirms:
- upload endpoint works
- FastAPI file handling works
- planner API path is correct
- Docker networking is correct

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

---
