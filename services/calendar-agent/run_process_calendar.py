# run_process_calendar.py
import json
from fastapi import UploadFile, File, HTTPException
from openai import OpenAI
import io
from PIL import Image
import os
import base64
from json_repair import repair_json

open_ai_key = os.getenv("OPENAI_API_KEY")

if not open_ai_key:
    raise RuntimeError("OPENAI_API_KEY not set. Make sure it's defined in secrets/agent.env")

client = OpenAI(api_key=open_ai_key)


VISION_PROMPT = """
You are VisionReaderAgent, an expert calendar OCR and structure extractor.

Your job:
1. Read the provided calendar screenshot.
2. Extract all recognizable events.
3. Normalize ambiguous or partial information.
4. Infer date if screenshot contains a weekly or monthly layout.

Return ONLY a JSON object with this exact structure:

{
  "events": [
    {
      "title": "string",
      "date": "YYYY-MM-DD",
      "start": "HH:MM",
      "end": "HH:MM",
      "location": "string or null",
      "notes": "string or null",
      "raw_text": "original text you extracted"
    }
  ],
  "metadata": {
    "source_type": "calendar_screenshot",
    "confidence": "0-1 float estimation",
    "missing_fields_filled": ["date", "start", "end"]
  }
}
"""


async def process_calendar(file: UploadFile = File(...)):
    """Upload screenshot → GPT-4o Vision → return structured JSON."""

    if file.content_type not in ["image/png", "image/jpeg"]:
        raise HTTPException(status_code=400, detail="Only PNG or JPG allowed.")

    content = await file.read()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (>10MB).")

    # Validate image
    try:
        image = Image.open(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    # Convert to PNG bytes
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    png_bytes = buf.getvalue()

    # Encode to base64
    base64_image = base64.b64encode(png_bytes).decode("utf-8")

    # GPT-4o Vision call (correct format)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": VISION_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract structured JSON from this calendar image."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=2000
    )

    raw_output = response.choices[0].message.content

    try:
        fixed_output = repair_json(raw_output)
        calendar_json = json.loads(fixed_output)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON output from GPT (json-repair failed). Raw output: {raw_output}"
        )

    return {"parsed_calendar": calendar_json}