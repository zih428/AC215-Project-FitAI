import os
import json
import io
from typing import List, Dict, Any
import time

from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
from google import genai
from google.genai import types

# 1. Setup Environment & Client
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("API_KEY not found in environment variables.")

client = genai.Client(api_key=api_key)

app = FastAPI()

# ==========================================
# 🕵️Step 1: Structure Analysis
# ==========================================
def step1_get_grid_structure(image: Image.Image) -> Dict:
    prompt_structure = """
    Analyze the layout of this calendar image.
    
    Task: Identify the column headers visible in the top row.
    1. Ignore the time sidebar on the left.
    2. Read the text of the date headers from Left to Right.
    3. Return them as a strictly ordered list.
    
    Output JSON:
    {
      "view_type": "string (e.g. 5-Day Work Week, 7-Day Week)",
      "column_headers": ["string", "string", ...] 
    }
    """
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt_structure, image],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0
        )
    )
    return json.loads(response.text)

# ==========================================
# Step 2: Event Extraction
# ==========================================
def step2_extract_events(image: Image.Image, structure_data: Dict) -> List[Dict]:
    headers = structure_data.get("column_headers", [])
    
    prompt = f"""
    You are a Calendar Event Extractor.
    
    **KNOWN GRID STRUCTURE:**
    Visible Headers: {json.dumps(headers)}
    
    **INSTRUCTION:**
    1. **Locate Events:** Find every colored event block.
    2. **Map Column:** Map event to exactly one header from the list above (Vertical Alignment).
    
    3. **TIME EXTRACTION & NORMALIZATION (CRITICAL):**
       - Look at the Left Sidebar. It might be **24-hour** (13:00) or **12-hour AM/PM** (1 PM).
       - **RULE:** You MUST convert all times to **24-Hour Format (HH:MM)**.
       - *Example:* If you see "1 PM", output "13:00".
       - *Example:* If you see "9", and it's in the morning slot, output "09:00".
       - *Example:* If you see "2" after "12", it means "14:00".
       - **Visual Estimation:** If an event starts halfway between "1 PM" and "2 PM", output "13:30".
       
    **OUTPUT JSON:**
    [
      {{
        "event_title": "string",
        "aligned_header": "string",
        "start_time": "HH:MM (Always 24h format, e.g. 14:00)",
        "end_time": "HH:MM (Always 24h format)"
      }}
    ]
    """
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt, image],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0
        )
    )
    return json.loads(response.text)

# ==========================================
# Step 3: Visual Date Resolution
# ==========================================
def step3_resolve_dates(image: Image.Image, raw_headers: List[str]) -> Dict:
    prompt = f"""
    You are a Calendar Logic Engine.
    
    **INPUTS:**
    1. **IMAGE:** Look at the top-left/header area for the **Month Name**.
    2. **HEADERS:** {json.dumps(raw_headers)}
    3. **DEFAULT YEAR:** 2025 (If not visible).
    
    **REASONING TASK:**
    1. **Identify Anchor:** What month is written on the screen? (e.g., "December").
    2. **Analyze Sequence:** Look at the numbers in the headers.
       - If the numbers increase normally (e.g., 1, 2, 3), they belong to the Anchor Month.
       - **Transition Logic:** If the sequence resets (e.g., 30, 31, 1, 2), implies a month boundary.
       - Use the Anchor Month to decide if the "30" is the Previous Month or if the "1" is the Next Month.
    3. **Compute:** Calculate the ISO Date (YYYY-MM-DD) for each header based on 2025 calendar logic.
    
    **OUTPUT JSON:**
    Return a simple map:
    {{
      "original_header_text": "YYYY-MM-DD",
      ...
    }}
    """
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt, image],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0
        )
    )
    return json.loads(response.text)

async def process_calendar(file: UploadFile = File(...)):
    """Upload screenshot → Gemini 3-Step Pipeline → JSON with timing."""

    start_total = time.perf_counter()  # 🔥 total timer start

    # 1. Validation
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, or WEBP allowed.")

    try:
        # 2. Read bytes → PIL
        t0 = time.perf_counter()
        content = await file.read()
        image = Image.open(io.BytesIO(content))
        t_read = time.perf_counter() - t0

        # === Step 1 ===
        t1 = time.perf_counter()
        structure = step1_get_grid_structure(image)
        t_step1 = time.perf_counter() - t1

        raw_headers = structure.get("column_headers", [])
        if not raw_headers:
            return {"error": "No headers found", "raw_data": []}

        # === Step 2 ===
        t2 = time.perf_counter()
        events = step2_extract_events(image, structure)
        t_step2 = time.perf_counter() - t2

        # === Step 3 ===
        t3 = time.perf_counter()
        date_map = step3_resolve_dates(image, raw_headers)
        t_step3 = time.perf_counter() - t3

        # === Merge step ===
        t4 = time.perf_counter()
        final_events = []
        for item in events:
            header_key = item.get('aligned_header')
            iso_date = date_map.get(header_key, "Unknown-Date")

            final_events.append({
                "title": item.get('event_title'),
                "start": f"{iso_date}T{item.get('start_time')}:00",
                "end": f"{iso_date}T{item.get('end_time')}:00",
                "location": None 
            })

        final_events.sort(key=lambda x: x['start'])
        t_merge = time.perf_counter() - t4

        # === Total elapsed time ===
        total_elapsed = time.perf_counter() - start_total

        calendar_json= {
            "events": final_events,
            "timing": {
                "read_image": round(t_read, 3),
                "step1_structure": round(t_step1, 3),
                "step2_extract_events": round(t_step2, 3),
                "step3_resolve_dates": round(t_step3, 3),
                "merge_sort": round(t_merge, 3),
                "total_seconds": round(total_elapsed, 3)
            }
        }
        return {"parsed_calendar": calendar_json}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")