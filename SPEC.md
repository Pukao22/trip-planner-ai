# SPEC.md — Trip Planner AI (ผู้ช่วยวางแผนทริป)

## 1. ภาพรวม (Overview)

แอปนี้ช่วยผู้ใช้วางแผนทริปท่องเที่ยวแบบรายวัน โดยรับข้อมูลปลายทาง วันที่เดินทาง งบประมาณ
และความสนใจของผู้ใช้ แล้วให้ Gemini สร้างแผนเที่ยวที่ **อ้างอิงข้อมูลปัจจุบันจริง**
(สถานที่เที่ยว / สภาพอากาศ) ผ่าน Google Search grounding และ **คำนวณงบประมาณรวม**
ผ่าน function calling แล้วส่งคืนผลลัพธ์เป็น JSON ที่มีโครงสร้างแน่นอน พร้อมนำไปใช้ต่อ
(เช่น render เป็นตารางหรือ export)

ต่อยอดจาก Lab วันนี้ (GSP1150 · Introduction to Gemini 3) โดยไม่ใช้ use case ตัวอย่างในแล็บซ้ำ

---

## 2. Input

ผู้ใช้กรอกข้อมูลผ่าน CLI (input()) หรือ argument ดังนี้:

| ฟิลด์ | ชนิดข้อมูล | ตัวอย่าง | บังคับ |
|---|---|---|---|
| `destination` | string | "เชียงใหม่" | ใช่ |
| `num_days` | int | 3 | ใช่ |
| `budget_thb` | int | 9000 | ใช่ |
| `interests` | string (comma-separated) | "ธรรมชาติ, อาหารท้องถิ่น, วัด" | ไม่ (default: "ทั่วไป") |
| `travel_month` | string | "สิงหาคม" | ไม่ (default: เดือนปัจจุบัน) |

---

## 3. Output (Structured Output / JSON Schema)

โมเดลต้องตอบกลับเป็น JSON ที่ตรงตาม schema นี้เท่านั้น (ใช้ `response_schema` ของ genai SDK
บังคับ ไม่ใช่แค่สั่งใน prompt):

```json
{
  "destination": "string",
  "num_days": "integer",
  "trip_summary": "string (สรุปทริปสั้นๆ 1-2 ประโยค)",
  "weather_note": "string (ข้อมูลสภาพอากาศช่วงเดินทาง จาก grounding)",
  "days": [
    {
      "day": "integer",
      "theme": "string (ธีมของวันนั้น เช่น 'วันวัดและวัฒนธรรม')",
      "activities": [
        {
          "time": "string (เช่น '09:00')",
          "place": "string",
          "description": "string",
          "est_cost_thb": "integer"
        }
      ]
    }
  ],
  "total_budget_estimate_thb": "integer (มาจาก function calling)",
  "budget_status": "string ('อยู่ในงบ' หรือ 'เกินงบ X บาท')",
  "sources": ["string (URL หรือชื่อแหล่งข้อมูลจาก grounding)"]
}
```

### กติกาการ validate output
- `activities` ต้องมีอย่างน้อย 2 รายการต่อวัน
- `total_budget_estimate_thb` ต้องมาจากผลลัพธ์ function `calculate_total_budget()` จริง
  ไม่ใช่ให้โมเดลกะเอาเอง
- ถ้า parse JSON ไม่ผ่าน ให้ retry เรียก API ซ้ำ 1 ครั้งก่อน raise error

---

## 4. System Instruction (แนวทาง)
คุณคือไกด์ทัวร์มืออาชีพที่เชี่ยวชาญการวางแผนทริปในประเทศไทยและต่างประเทศ
หน้าที่ของคุณคือวางแผนทริปให้สมจริง ใช้ข้อมูลสถานที่และสภาพอากาศล่าสุด
จากการค้นหาเว็บเสมอ ห้ามใช้ข้อมูลเก่าหรือเดาเอง

กฎ:

-แผนต้องเหมาะกับความสนใจของผู้ใช้ที่ระบุมา
-กระจายกิจกรรมให้สมเหตุสมผลตามเวลาในแต่ละวัน (เช้า-บ่าย-เย็น)
-ประมาณค่าใช้จ่ายแต่ละกิจกรรมอย่างสมเหตุสมผล
-เมื่อคำนวณงบรวม ให้เรียกใช้ฟังก์ชัน calculate_total_budget เสมอ
ห้ามคำนวณเลขเอง
-ตอบกลับเป็น JSON ตาม schema ที่กำหนดเท่านั้น ห้ามมีข้อความอื่นนอก JSON

---

## 5. ฟีเจอร์ที่ใช้ (≥ 1 ตามโจทย์ / ที่นี่ใช้ 2 อย่าง)

### 5.1 Grounding (Google Search)
- ใช้ค้นหาสถานที่ท่องเที่ยวยอดนิยม ณ ปัจจุบัน และสภาพอากาศของปลายทางในช่วงเดือนที่เดินทาง
- ผลลัพธ์ที่ได้จะถูกอ้างอิงใส่ใน `weather_note` และ `sources`

### 5.2 Function Calling
- ฟังก์ชัน `calculate_total_budget(activities: list[dict]) -> int`
  รับ list ของกิจกรรมทั้งหมด (รวมทุกวัน) แล้วคืนผลรวม `est_cost_thb`
- โมเดลต้องเรียกฟังก์ชันนี้แทนการคำนวณเลขเอง เพื่อความแม่นยำ

---

## 6. Temperature

ตั้งค่า `temperature = 0.7`
เหตุผล: งานนี้ต้องการความ "สร้างสรรค์พอประมาณ" ในการจัดกิจกรรม/คำอธิบายให้น่าสนใจ
ไม่ซ้ำซาก แต่ยังต้องคง factual accuracy ของสถานที่และตัวเลขงบประมาณ (ซึ่งคุมด้วย
grounding + function calling อยู่แล้ว ไม่ได้พึ่ง temperature ต่ำเพื่อความแม่นยำส่วนนั้น)
จึงไม่ตั้งต่ำสุด (0) และไม่ตั้งสูงมาก (>1) เพื่อลดโอกาส hallucinate ชื่อสถานที่

---

## 7. โจทย์เสริม (Determination) ที่วางแผนจะทำ

- [ ] Multi-turn chat: ผู้ใช้สามารถพิมพ์ตามหลังผลลัพธ์แรก เช่น "ขอปรับวันที่ 2 ให้เน้นอาหารมากขึ้น"
      แล้วโมเดลแก้แผนเดิมโดยจำ context เดิมไว้
- [ ] thinking_level: ตั้งระดับการคิดของโมเดลให้เหมาะกับความซับซ้อนของทริป (ทริปยาว/หลายเงื่อนไข
      ใช้ thinking level สูงขึ้น)

---

## 8. โครงสร้างไฟล์ในโปรเจกต์

trip-planner-ai/
├── README.md
├── SPEC.md
├── app.py
├── requirements.txt
└── .env.example


---

## 9. ส่วนที่ใช้ AI ช่วย (จะระบุใน README.md เมื่อเขียนเสร็จ)

- ใช้ AI ช่วยร่าง SPEC.md ฉบับนี้ตาม requirement ที่กำหนดเอง
- ใช้ AI ช่วย debug โค้ดส่วน function calling / JSON schema (จะระบุรายละเอียดเพิ่มใน README
  ตอนพัฒนาโค้ดจริง)
