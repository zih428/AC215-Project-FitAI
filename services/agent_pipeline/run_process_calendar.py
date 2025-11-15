from fastapi import UploadFile, File, HTTPException
from openai import OpenAI
import io
from PIL import Image
import os

open_ai_key = os.getenv("OPENAI_API_KEY", "OPEN_AI_API_KEY")
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

Rules:
- Do NOT include explanations.
- Do NOT include markdown.
- Times MUST be 24-hour format.
- If date is missing but the screenshot shows a weekly grid, deduce the date.
- If duration is shown instead of start/end, calculate end time.
- If information is ambiguous, leave field null and include a note in "notes".
"""


async def process_calendar(file: UploadFile = File(...)):
    """Upload screenshot → GPT-4o Vision → return structured JSON."""
    
    # Validate upload type
    if file.content_type not in ["image/png", "image/jpeg"]:
        raise HTTPException(status_code=400, detail="Only PNG or JPG allowed.")

    # Read bytes
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (>10MB).")

    # Convert to PIL for processing
    try:
        image = Image.open(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)

    # Vision model call
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": VISION_PROMPT},
            {"role": "user", "content": [
                {"type": "input_image", "image": buf.getvalue()}
            ]},
        ]
    )

    try:
        calendar_json = response.choices[0].message.content
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid response from GPT VisionAgent.")

    return {
        "parsed_calendar": calendar_json
    }