# Design

## Context

หน้า `web/app/stocks/[symbol]/page.tsx` เป็น server component ที่ดึง `StockDetail` จาก engine ครั้งเดียว (`/stocks/<symbol>`) แล้ว render แต่ละส่วนจาก object นั้น คำอธิบายวิธีคิดของ fair value และ MoS อยู่ใน `FAIR_VALUE_HELP` และ `MOS_HELP` ในไฟล์เดียวกันเป็นภาษาไทย ฟังก์ชันจัดรูปแบบอยู่ใน `web/lib/format.ts` (`baht`, `pct`, `thaiDate`) ซึ่งจัดตาม locale ไทย

web ยังไม่มี test runner (`package.json` มีแค่ `lint`) ส่วน runtime คือ bun 1.0.23 ซึ่งมี `bun test` ในตัว

## Goals / Non-Goals

**Goals:**
- กดปุ่มเดียวได้ Markdown ที่วางในแชท LLM ได้ทันที ตัวเลขตรงกับหน้า
- ไม่แก้ engine และไม่เพิ่ม dependency

**Non-Goals:**
- ข้อมูลรายไตรมาสย้อนหลัง (ดู proposal นอกขอบเขต)
- แสดงตัวอย่างข้อความก่อนคัดลอก หรือแก้ prompt จากหน้าเว็บ

## Decisions

### D1. สร้าง Markdown จาก `StockDetail` ด้วย pure function ใน `web/lib/llm-export.ts`

`toLlmMarkdown(detail: StockDetail): string` ไม่มี side effect เรียกจาก server component แล้วส่งผลเป็น string ให้ปุ่ม ข้อความจึงมาจาก object เดียวกับที่หน้า render ตัวเลขตรงกันโดยไม่ต้องดึงซ้ำ และ test ได้โดยไม่ต้องมีเบราว์เซอร์

- ทางเลือกอื่น: อ่านข้อความจาก DOM (`innerText`) ปฏิเสธเพราะได้ข้อความไม่มีโครงสร้าง ตกหล่น tooltip และพังเมื่อเปลี่ยน layout
- ทางเลือกอื่น: endpoint ใหม่ใน engine ที่คืน Markdown ปฏิเสธเพราะต้องแก้สองฝั่ง และ engine ไม่ควรรู้เรื่องการแสดงผล
- ทางเลือกอื่น: ส่ง `StockDetail` ทั้ง object ให้ client component แล้วสร้างข้อความตอนกด ปฏิเสธเพราะ serialize ข้อมูลทั้งก้อนเข้า client bundle ของหน้า ทั้งที่ต้องการแค่ string

### D2. ปุ่มเป็น client component `copy-button.tsx` ข้าง `event-form.tsx`

รับ `text: string` ใช้ `navigator.clipboard.writeText` แสดง "คัดลอกแล้ว" ราว 2 วินาที ถ้า promise reject แสดง "คัดลอกไม่สำเร็จ" ข้อความบนปุ่มเป็นภาษาไทยตาม UI ส่วนอื่น วางปุ่มที่หัวหน้าข้างชื่อหุ้น ใช้ได้ทั้งตอนมีและไม่มีผลประเมิน

- ทางเลือกอื่น: `document.execCommand("copy")` เป็น fallback ปฏิเสธเพราะ deprecated และแอปรันบน localhost ซึ่งเป็น secure context ที่ Clipboard API ใช้ได้

### D3. รูปแบบข้อความ: Markdown ป้ายกำกับภาษาอังกฤษ ตัวเลขไม่ขึ้นกับ locale

- โครง: prompt นำ → `# <SYMBOL> — <name>` → หัวข้อ `##` ต่อส่วนตามลำดับเดียวกับหน้า (Overview, Candidate status, Gates, Fair value, CDC, Risk/reward, Catalyst hints, Events, Method notes)
- Gates และ fair value เป็นตาราง Markdown ส่วนอื่นเป็นรายการ `- Label: value`
- ตัวเลขใช้ formatter ของตัวเองใน `llm-export.ts`: ราคาเป็นทศนิยม 2 ตำแหน่งไม่มีตัวคั่นหลักพัน ต่อท้าย THB, สัดส่วนเป็น % พร้อมเครื่องหมาย (ใช้ `pct` เดิมได้เพราะไม่ขึ้นกับ locale), วันที่ YYYY-MM-DD ตรงจาก engine, ค่าที่ไม่มีเป็น `N/A`
- ข้อความที่ engine ให้มา (reason, threshold, hints, label ของ event) ใส่ตามเดิมเพราะเป็นภาษาไทยจาก engine และ escape `|` ในเซลล์ตาราง
- ไม่ใส่แถวของเกณฑ์ที่ปิดใน config เพราะหน้าไม่แสดง (engine ไม่ส่งมา)

- ทางเลือกอื่น: ใช้ `baht()` และ `thaiDate()` เดิม ปฏิเสธเพราะได้ "14 ต.ค. 2569" (ปี พ.ศ.) และตัวคั่นหลักพัน LLM อ่านวันที่ผิดเป็น ค.ศ. ได้
- ทางเลือกอื่น: JSON ปฏิเสธตามที่ผู้ใช้เลือก (อ่านยากสำหรับคน และเปลือง token กับ key)

### D4. คำอธิบายวิธีคิดภาษาอังกฤษแยกจาก tooltip ภาษาไทย

เพิ่ม `METHOD_NOTES_EN` ใน `llm-export.ts` หนึ่งบรรทัดต่อ method (`pe_median`, `pe_minus_1sd`, `pbv_median`, `dividend_yield_median`, `peer_pe`) และ MoS เนื้อหาเดียวกับ `FAIR_VALUE_HELP` และ `MOS_HELP` ใส่ใน Method notes เฉพาะ method ที่อยู่ในข้อความ method ที่ไม่มีคำอธิบายจะไม่มีบรรทัดนั้น

- ทางเลือกอื่น: ใช้ tooltip ภาษาไทยเดิม ปฏิเสธเพราะผู้ใช้เลือกป้ายภาษาอังกฤษ ข้อความผสมสองภาษาในส่วนเดียวกันอ่านยาก
- ทางเลือกอื่น: ย้าย tooltip ทั้งสองภาษามาไว้ที่เดียว ปฏิเสธเพราะเป็น refactor นอกคำขอ แค่วางสองชุดไว้ใกล้กันพอ

### D5. ตรวจด้วย `bun test` หนึ่งไฟล์

`web/lib/llm-export.test.ts` ใช้ `StockDetail` จำลองสามแบบ: candidate ครบทุกส่วน, ไม่ผ่าน gate พร้อมเกณฑ์ N/A และป้ายเตือน, หุ้น fail ที่ไม่มีผลประเมิน ไม่เพิ่ม dependency และไม่เพิ่ม script ใน `package.json` (รัน `bun test lib` ตรงๆ)

- ทางเลือกอื่น: ตรวจในเบราว์เซอร์อย่างเดียว ปฏิเสธเพราะ formatter มี branch หลายทาง (N/A, ไม่มี quality, ไม่มี risk/reward, fail) ที่เช็คด้วยตาไม่ครบ
- ทางเลือกอื่น: เพิ่ม vitest ปฏิเสธเพราะเพิ่ม dependency ทั้งที่ bun มีอยู่แล้ว

## Risks / Trade-offs

- [หน้าเพิ่มส่วนใหม่ในอนาคตแต่ไม่ได้เพิ่มใน formatter] → ข้อความขาดส่วนนั้นโดยไม่มีใครรู้ กรณีแย่สุดคือ LLM ให้ความเห็นโดยไม่เห็นข้อมูลที่ขัดกับข้อสรุป บรรเทาด้วยการเขียนไว้ใน proposal ว่าส่วนใหม่ต้องเพิ่มที่นี่ด้วย และ test เช็คหัวข้อครบทุกส่วน
- [คำอธิบายภาษาอังกฤษไม่ตรงกับ tooltip เมื่อแก้สูตร] → LLM เข้าใจวิธีคิดผิด วางทั้งสองชุดไว้ใกล้กันและระบุใน comment ให้แก้คู่กัน
- [ข้อมูลจากแหล่งไม่เป็นทางการผิดจริง] → LLM อาจเชื่อตัวเลขผิดแล้วยืนยันข้อสรุป prompt นำจึงบอกว่าข้อมูลไม่เป็นทางการและขอให้ตรวจความสอดคล้อง ความเห็นที่สองไม่แทนการตรวจกับ SET
- [ข้อความยาว] หุ้นที่มี event และ hint มากอาจยาวราว 1–2k token ยังพอสำหรับแชททั่วไป
- [เปิดแอปผ่าน IP ในวง LAN แทน localhost] → ไม่ใช่ secure context Clipboard API ใช้ไม่ได้ ปุ่มแสดง "คัดลอกไม่สำเร็จ" ตาม spec ไม่เงียบ
