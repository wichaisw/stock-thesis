# Tasks

## 1. Formatter

- [x] 1.1 เขียน `web/lib/llm-export.test.ts` ด้วย `StockDetail` จำลองสามแบบ (candidate ครบทุกส่วน, ไม่ผ่าน gate ROE พร้อม dividend yield band เป็น N/A และป้ายโครงสร้างทุนเปลี่ยน, หุ้น fail ที่ไม่มีผลประเมิน) ครอบทุก scenario ใน spec `stock-summary-export` ยกเว้นเรื่อง clipboard: prompt นำมีคำขอให้ตอบเป็นภาษาไทยอยู่ก่อนข้อมูล, หัวข้อครบทุกส่วน, แถว N/A พร้อมเหตุผล, ราคา `32.75 THB`, วันที่ `2026-10-14`, MoS `+12.3%`, คำอธิบาย dividend yield band ตรวจด้วย `bun test lib` ว่า fail ก่อนเขียน formatter
- [x] 1.2 เขียน `web/lib/llm-export.ts` (`toLlmMarkdown`, formatter ตัวเลขและวันที่ที่ไม่ขึ้นกับ locale, escape `|` ในเซลล์, `METHOD_NOTES_EN` ตาม design D3–D4) และใส่ comment ที่ `FAIR_VALUE_HELP` ให้แก้คู่กับ `METHOD_NOTES_EN` ตรวจด้วย `bun test lib` ผ่านทั้งหมด และ `bun run lint`

## 2. ปุ่มบนหน้ารายละเอียดหุ้น

- [x] 2.1 เพิ่ม `web/app/stocks/[symbol]/copy-button.tsx` (client component ตาม design D2) และวางที่หัวหน้าข้างชื่อหุ้นใน `page.tsx` โดยส่ง `toLlmMarkdown(data)` ตรวจด้วย `bun run lint` และในเบราว์เซอร์ (skill `orca-browser-check`) กับ KLINIQ (candidate หรือเกือบ), หุ้นที่ไม่ผ่าน gate และหุ้นที่ fail ใน batch ล่าสุด: กดแล้วปุ่มแสดง "คัดลอกแล้ว" อ่าน clipboard แล้วเทียบราคา MoS และเหตุผลทุกส่วนกับที่หน้าแสดง ว่าตรงกันทุกค่า
- [x] ~~2.2 วางข้อความที่คัดลอกของ KLINIQ ในแชท LLM ตัวอื่นหนึ่งครั้ง ตรวจว่า LLM ตอบเป็นภาษาไทยและอ้างถึงตัวเลขในข้อความได้ถูก (ไม่อ่านวันที่หรือหน่วยผิด) บันทึกผลสั้นๆ ไว้ในรายงานตอน apply~~ ข้ามตามที่ผู้ใช้เลือก (14 ต.ค. 2026) ใช้ผลตรวจในเบราว์เซอร์ของ 2.1 และ `bun test lib` แทน
