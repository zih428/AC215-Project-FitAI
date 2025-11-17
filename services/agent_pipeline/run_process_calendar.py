# run_process_calendar.py
from fastapi import UploadFile, File, HTTPException
from openai import OpenAI
import io
from PIL import Image
import os
import base64


open_ai_key = os.getenv("OPENAI_API_KEY")

if not open_ai_key:
    # 在本地开发时你会立刻看到错误，而不会默默用一个假 key
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

Rules:
- Do NOT include explanations.
- Do NOT include markdown.
- Times MUST be in 24-hour format.
- If date is missing but screenshot shows a weekly grid, deduce the date.
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

    # Convert to PIL (validates image)
    try:
        image = Image.open(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    # Convert to PNG bytes
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    png_bytes = buf.getvalue()

    # Encode to base64 for OpenAI Vision
    base64_image = base64.b64encode(png_bytes).decode("utf-8")

    # Call GPT Vision
    response = client.chat.completions.create(
        model="gpt-4o",  # or gpt-4o-mini for speed
        messages=[
            {"role": "system", "content": VISION_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text", 
                        "text": "Extract structured calendar JSON."
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{base64_image}"
                    }
                ]
            }
        ],
        max_tokens=1500
    )

    # Get LLM output
    try:
        calendar_json = response.choices[0].message["content"]
    except:
        raise HTTPException(status_code=500, detail="Invalid response from GPT VisionAgent.")

    return {"parsed_calendar": calendar_json}