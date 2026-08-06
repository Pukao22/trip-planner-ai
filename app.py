"""
Trip Planner AI — ผู้ช่วยวางแผนทริป
ต่อยอดจาก Lab GSP1150 · Introduction to Gemini 3

Features:
- System Instructions
- Structured Output (JSON Schema)
- Grounding (Google Search)
- Function Calling (คำนวณงบประมาณรวม)
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("ไม่พบ GEMINI_API_KEY กรุณาตั้งค่าในไฟล์ .env")

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-3-pro-preview"  # ปรับตามโมเดลที่ Lab ใช้จริง


# ---------------------------------------------------------------------------
# 1) Function Calling: ฟังก์ชันคำนวณงบประมาณรวม
# ---------------------------------------------------------------------------
def calculate_total_budget(activities: list[dict]) -> int:
    """
    รับ list ของกิจกรรมทั้งหมด (รวมทุกวัน) แล้วคืนผลรวม est_cost_thb
    โมเดลจะเรียกฟังก์ชันนี้แทนการคำนวณเลขเอง เพื่อความแม่นยำ
    """
    total = sum(item.get("est_cost_thb", 0) for item in activities)
    print(f"   [Function Called] calculate_total_budget -> {total} บาท")
    return total


# ประกาศ schema ของฟังก์ชันให้โมเดลรู้จัก (function declaration)
calculate_budget_function = types.FunctionDeclaration(
    name="calculate_total_budget",
    description="คำนวณงบประมาณรวมของทริปจากรายการกิจกรรมทั้งหมด",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "activities": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "est_cost_thb": types.Schema(type=types.Type.INTEGER),
                    },
                ),
            )
        },
        required=["activities"],
    ),
)


# ---------------------------------------------------------------------------
# 2) Structured Output: JSON Schema ตาม SPEC.md
# ---------------------------------------------------------------------------
TRIP_PLAN_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "destination": types.Schema(type=types.Type.STRING),
        "num_days": types.Schema(type=types.Type.INTEGER),
        "trip_summary": types.Schema(type=types.Type.STRING),
        "weather_note": types.Schema(type=types.Type.STRING),
        "days": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "day": types.Schema(type=types.Type.INTEGER),
                    "theme": types.Schema(type=types.Type.STRING),
                    "activities": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "time": types.Schema(type=types.Type.STRING),
                                "place": types.Schema(type=types.Type.STRING),
                                "description": types.Schema(type=types.Type.STRING),
                                "est_cost_thb": types.Schema(type=types.Type.INTEGER),
                            },
                            required=["time", "place", "description", "est_cost_thb"],
                        ),
                    ),
                },
                required=["day", "theme", "activities"],
            ),
        ),
        "total_budget_estimate_thb": types.Schema(type=types.Type.INTEGER),
        "budget_status": types.Schema(type=types.Type.STRING),
        "sources": types.Schema(
            type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)
        ),
    },
    required=[
        "destination",
        "num_days",
        "trip_summary",
        "weather_note",
        "days",
        "total_budget_estimate_thb",
        "budget_status",
    ],
)


# ---------------------------------------------------------------------------
# 3) System Instruction
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """
คุณคือไกด์ทัวร์มืออาชีพที่เชี่ยวชาญการวางแผนทริปในประเทศไทยและต่างประเทศ
หน้าที่ของคุณคือวางแผนทริปให้สมจริง ใช้ข้อมูลสถานที่และสภาพอากาศล่าสุด
จากการค้นหาเว็บเสมอ ห้ามใช้ข้อมูลเก่าหรือเดาเอง

กฎ:
1. แผนต้องเหมาะกับความสนใจของผู้ใช้ที่ระบุมา
2. กระจายกิจกรรมให้สมเหตุสมผลตามเวลาในแต่ละวัน (เช้า-บ่าย-เย็น)
3. ประมาณค่าใช้จ่ายแต่ละกิจกรรมอย่างสมเหตุสมผล
4. เมื่อคำนวณงบรวม ให้เรียกใช้ฟังก์ชัน calculate_total_budget เสมอ ห้ามคำนวณเลขเอง
5. ตอบกลับเป็น JSON ตาม schema ที่กำหนดเท่านั้น ห้ามมีข้อความอื่นนอก JSON
"""


# ---------------------------------------------------------------------------
# 4) เรียก Gemini API
# ---------------------------------------------------------------------------
def generate_trip_plan(destination: str, num_days: int, budget_thb: int,
                        interests: str, travel_month: str) -> dict:

    user_prompt = f"""
    วางแผนทริปเที่ยว {destination} จำนวน {num_days} วัน
    งบประมาณรวมประมาณ {budget_thb} บาท
    ความสนใจ: {interests}
    ช่วงเวลาเดินทาง: {travel_month}
    """

    # หมายเหตุ: Google Search grounding และ response_schema (structured output)
    # ไม่สามารถใช้ร่วมกันในการเรียกครั้งเดียวได้ในหลายเวอร์ชันของ SDK
    # จึงแบ่งเป็น 2 ขั้นตอน: (1) ค้นหาข้อมูล grounding ก่อน (2) ใช้ผลลัพธ์มาสร้าง JSON

    # --- Step 1: ค้นหาข้อมูลสถานที่/อากาศปัจจุบันด้วย Grounding ---
    grounding_response = client.models.generate_content(
        model=MODEL_NAME,
        contents=f"ค้นหาสถานที่ท่องเที่ยวแนะนำและสภาพอากาศของ {destination} "
                 f"ในช่วง {travel_month} ที่เกี่ยวข้องกับความสนใจ: {interests}",
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.7,
        ),
    )
    grounding_info = grounding_response.text
    sources = []
    if grounding_response.candidates[0].grounding_metadata:
        chunks = grounding_response.candidates[0].grounding_metadata.grounding_chunks or []
        sources = [c.web.uri for c in chunks if c.web]

    # --- Step 2: ใช้ function calling คำนวณงบ (ตัวอย่าง manual-call แบบง่าย) ---
    # ในแอปจริงจะปล่อยให้โมเดลเรียกฟังก์ชันเองผ่าน tools=[calculate_budget_function]
    # ตัวอย่างนี้สาธิต flow: โมเดลสร้างกิจกรรมก่อน -> เราคำนวณ -> ส่งกลับให้โมเดลสรุป

    # --- Step 3: สร้างแผนทริปแบบ JSON โดยอิง grounding_info ---
    final_prompt = f"""
    ข้อมูลอ้างอิงล่าสุดที่ค้นเจอ:
    {grounding_info}

    จากข้อมูลข้างต้น จงวางแผนทริป {destination} จำนวน {num_days} วัน
    งบประมาณรวมประมาณ {budget_thb} บาท ความสนใจ: {interests}
    ช่วงเวลาเดินทาง: {travel_month}
    ใส่ sources ต่อไปนี้ใน field sources: {sources}
    """

    final_response = client.models.generate_content(
        model=MODEL_NAME,
        contents=final_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=TRIP_PLAN_SCHEMA,
            temperature=0.7,
        ),
    )

    try:
        trip_plan = json.loads(final_response.text)
    except json.JSONDecodeError:
        # retry ครั้งเดียวตาม SPEC.md
        final_response = client.models.generate_content(
            model=MODEL_NAME,
            contents=final_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=TRIP_PLAN_SCHEMA,
                temperature=0.7,
            ),
        )
        trip_plan = json.loads(final_response.text)

    # --- Step 4: คำนวณงบจริงด้วยฟังก์ชันของเรา (แทนค่าที่โมเดลกะเอง) ---
    all_activities = [
        act for day in trip_plan.get("days", []) for act in day.get("activities", [])
    ]
    real_total = calculate_total_budget(all_activities)
    trip_plan["total_budget_estimate_thb"] = real_total
    trip_plan["budget_status"] = (
        "อยู่ในงบ" if real_total <= budget_thb
        else f"เกินงบ {real_total - budget_thb} บาท"
    )

    return trip_plan


# ---------------------------------------------------------------------------
# 5) แสดงผลลัพธ์
# ---------------------------------------------------------------------------
def print_trip_plan(plan: dict):
    print("\n" + "=" * 50)
    print(f"🧳 แผนเที่ยว: {plan['destination']} ({plan['num_days']} วัน)")
    print("=" * 50)
    print(f"\n📝 สรุป: {plan['trip_summary']}")
    print(f"🌤️  สภาพอากาศ: {plan['weather_note']}\n")

    for day in plan["days"]:
        print(f"--- วันที่ {day['day']}: {day['theme']} ---")
        for act in day["activities"]:
            print(f"  {act['time']} | {act['place']} — {act['description']} "
                  f"(~{act['est_cost_thb']} บาท)")
        print()

    print(f"💰 งบประมาณรวมโดยประมาณ: {plan['total_budget_estimate_thb']} บาท")
    print(f"📊 สถานะงบ: {plan['budget_status']}")
    if plan.get("sources"):
        print(f"\n🔗 แหล่งข้อมูล: {', '.join(plan['sources'])}")


# ---------------------------------------------------------------------------
# 6) Main — รับ input จากผู้ใช้
# ---------------------------------------------------------------------------
def main():
    print("=== 🧳 Trip Planner AI ===\n")
    destination = input("ปลายทาง: ").strip()
    num_days = int(input("จำนวนวัน: ").strip())
    budget_thb = int(input("งบประมาณ (บาท): ").strip())
    interests = input("ความสนใจ (คั่นด้วย comma, Enter เพื่อข้าม): ").strip() or "ทั่วไป"
    travel_month = input("เดือนที่เดินทาง (Enter เพื่อใช้เดือนปัจจุบัน): ").strip()
    if not travel_month:
        travel_month = datetime.now().strftime("%B")

    print("\n⏳ กำลังวางแผนทริป กรุณารอสักครู่...\n")

    try:
        plan = generate_trip_plan(destination, num_days, budget_thb, interests, travel_month)
        print_trip_plan(plan)
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")


if __name__ == "__main__":
    main()