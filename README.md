# Trip Planner AI 🧳

ผู้ช่วยวางแผนทริปด้วย Gemini API — สร้างแผนเที่ยวรายวันที่อ้างอิงข้อมูลปัจจุบันจริง
(สถานที่ / สภาพอากาศ) ผ่าน Google Search grounding และคำนวณงบประมาณรวมผ่าน function calling

ต่อยอดจาก Lab **GSP1150 · Introduction to Gemini 3** (Gemini API ผ่าน Google Gen AI SDK / `genai`)

---

## ฟีเจอร์ที่ใช้จาก Lab

- ✅ System Instructions — กำหนดบทบาทโมเดลเป็นไกด์ทัวร์มืออาชีพ
- ✅ Structured Output (JSON Schema) — บังคับ output เป็น JSON ตาม schema ที่กำหนด
- ✅ Grounding (Google Search) — ค้นข้อมูลสถานที่/อากาศปัจจุบันจริง
- ✅ Function Calling — ฟังก์ชัน `calculate_total_budget()` คำนวณงบประมาณรวม

---

## วิธีติดตั้งและรัน

### 1. ติดตั้ง dependencies
```bash
pip install -r requirements.txt --break-system-packages
```
(หรือใช้ virtual environment ตามปกติ)

### 2. ตั้งค่า API Key
คัดลอกไฟล์ตัวอย่างแล้วใส่ key จริงของคุณ:
```bash
cp .env.example .env
```
แล้วแก้ไข `.env` ให้เป็น:

GEMINI_API_KEY=your_actual_api_key_here

> ดึง API key ได้จาก Google AI Studio (ตามที่ใช้ใน Lab)

### 3. รันโปรแกรม
```bash
python app.py
```

---

## ตัวอย่างการใช้งาน (Input/Output)

### Input
ปลายทาง: เชียงใหม่
จำนวนวัน: 2
งบประมาณ (บาท): 6000
ความสนใจ (คั่นด้วย comma, Enter เพื่อข้าม): วัด, อาหารท้องถิ่น
เดือนที่เดินทาง (Enter เพื่อใช้เดือนปัจจุบัน): สิงหาคม

### Output (ตัวอย่าง)
==================================================
🧳 แผนเที่ยว: เชียงใหม่ (2 วัน)

📝 สรุป: ทริป 2 วันเน้นวัดสำคัญและร้านอาหารท้องถิ่นในตัวเมืองเชียงใหม่
🌤️ สภาพอากาศ: เดือนสิงหาคมเป็นฤดูฝน อากาศเย็นสบาย ควรพกร่ม

--- วันที่ 1: วันวัดและวัฒนธรรม ---
09:00 | วัดพระธาตุดอยสุเทพ — ชมทิวทัศน์เมืองเชียงใหม่จากมุมสูง (~300 บาท)
13:00 | วัดเจดีย์หลวง — ชมโบราณสถานใจกลางเมืองเก่า (~50 บาท)
18:00 | ถนนคนเดินท่าแพ — ชิมอาหารท้องถิ่นและซื้อของฝาก (~500 บาท)

--- วันที่ 2: วันผ่อนคลายและอาหาร ---
09:00 | ตลาดวโรรส — ชิมอาหารเช้าแบบล้านนา (~200 บาท)
...

💰 งบประมาณรวมโดยประมาณ: 5,450 บาท
📊 สถานะงบ: อยู่ในงบ

🔗 แหล่งข้อมูล: https://...


---

## โครงสร้างโปรเจกต์

trip-planner-ai/
├── README.md
├── SPEC.md
├── app.py
├── requirements.txt
└── .env.example


---

## ส่วนที่ใช้ AI ช่วยพัฒนา (ตามที่โจทย์กำหนดให้ระบุ)

- ใช้ Claude ช่วยร่างโครงสร้าง `SPEC.md` ตาม requirement ที่กำหนดเอง (input/output, schema, ฟีเจอร์ที่เลือกใช้)
- ใช้ Claude ช่วยเขียนโครง `app.py` เบื้องต้น โดยเฉพาะส่วนการประกาศ `response_schema`
  และ `FunctionDeclaration` ตาม syntax ของ `google-genai` SDK
- ผู้พัฒนา (ฉัน) เป็นคนตัดสินใจเรื่อง use case, ฟีเจอร์ที่เลือกใช้ (grounding + function calling),
  ปรับ prompt ใน system instruction ให้เหมาะกับ use case, และทดสอบ/แก้ไข output จริงก่อนส่ง

---

## หมายเหตุ

- โค้ดแยกการเรียก grounding และ structured output เป็นคนละ API call เนื่องจาก SDK บางเวอร์ชัน
  ไม่รองรับการใช้ `tools` (search) พร้อมกับ `response_schema` ในการเรียกเดียว
- `calculate_total_budget` ถูกเรียกแบบ manual หลังได้ผลลัพธ์จากโมเดล เพื่อความแม่นยำของตัวเลข 100%

