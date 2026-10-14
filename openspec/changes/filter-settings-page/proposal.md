# Proposal

## Why

ตอนนี้ปรับเกณฑ์ได้ทางเดียวคือแก้ `engine/config.yaml` เอง และไม่มีที่ให้ดูว่าแต่ละค่ากระทบผลอย่างไร ผู้ใช้เห็นว่า liquidity filter (10 ลบ./วัน) สูงเกินไป จึงอยากปรับเกณฑ์จากหน้าเว็บ แล้วดูคำอธิบายภาษาไทยของแต่ละค่าได้ก่อนตัดสินใจ ควรทำก่อนงานที่เหลือของ `value-stock-shortlist` (4.9, 4.10, 8.2) เพราะ end-to-end test (8.2) ต้องใช้เกณฑ์ที่ผู้ใช้ตั้งเองจริง

## What Changes

- **หน้า Settings (`/settings`)** แสดงเกณฑ์ทุกตัวที่ใช้กรองและจัดอันดับหุ้น แบ่งตามหมวด:
  - Liquidity: window, traded value ขั้นต่ำ
  - Quality gate: ไตรมาสขั้นต่ำ, ROE, D/E, OCF, ขาดทุน
  - Fair value: เกณฑ์ที่เปิดใช้, lookback, จำนวนข้อมูลขั้นต่ำ, peer ขั้นต่ำ, PE สูงสุด, threshold ของป้ายเตือนโครงสร้างทุน
  - CDC: ETA ของ `bear-approaching`, จำนวนวันของ `just-crossed`, จำนวนวันราคาขั้นต่ำ, speed window
  - Risk/reward: swing low, stop buffer, RRR ขั้นต่ำ, ระยะถือ
  - Candidates: median MoS ขั้นต่ำ, state ที่รับเข้า
- **Tooltip ภาษาไทยทุกช่อง**: hover หรือ focus ที่ไอคอน ⓘ เพื่อดูว่าค่านี้ใช้ทำอะไร และถ้าเพิ่มหรือลดค่าจะทำให้ผลเปลี่ยนอย่างไร
- **ค่าที่แสดงเป็นหน่วยที่อ่านง่าย**: สัดส่วนแสดงเป็น % และ traded value แสดงเป็นล้านบาท แต่เก็บใน engine ตามหน่วยเดิม
- **บันทึก, validate และ reset**: engine ปฏิเสธค่าที่ผิดและบอกว่าช่องไหนผิด แต่ละช่องแสดงค่า default ไว้เทียบ และ reset กลับเป็น default ทั้งหมดได้
- **ค่าใหม่มีผลกับ batch ครั้งถัดไป** (ทั้งจากปุ่มบนเว็บและจาก CLI/cron) ถ้าแก้ค่าหลังจากรันครั้งล่าสุด หน้า candidates จะแจ้งว่าผลที่เห็นยังใช้ค่าเก่า
- ยกเลิก non-goal "UI สำหรับแก้ config" ของ `value-stock-shortlist`
- `config.yaml` ยังเป็นค่า default และใช้แก้เกณฑ์ที่ไม่อยู่บนหน้า settings ได้เหมือนเดิม

นอกขอบเขต:
- สูตร CDC (`source`, `ap_length`, `fast_length`, `slow_length`) ไม่อยู่บนหน้า settings เพราะต้องตรงกับ TradingView (ดู engine/README) ถ้าจะเปลี่ยนให้แก้ `config.yaml`
- รายชื่อ sector การเงิน, catalyst hints, วัน SET50/100 review และค่าของ batch ยังแก้ใน `config.yaml` เพราะไม่ใช่เกณฑ์กรองหุ้น
- ไม่มี preview ว่าค่าใหม่จะได้ candidates กี่ตัวก่อนรัน batch ถ้าอยากรู้ให้รัน batch (ราว 1 นาที)
- ไม่มีประวัติการแก้ค่าและไม่ผูกค่าที่ใช้กับแต่ละ run

## Capabilities

### New Capabilities
- `filter-settings`: ดูและแก้เกณฑ์กรองหุ้นจากหน้าเว็บ พร้อมคำอธิบายภาษาไทยรายช่อง validation, reset เป็น default และนำค่าไปใช้กับ batch ครั้งถัดไป

### Modified Capabilities
- (ไม่มี) ยังไม่มี spec หลักใน `openspec/specs/` เพราะ `value-stock-shortlist` ยังไม่ archive และ requirement ของ capability เดิมไม่เปลี่ยน ทุกเกณฑ์ยังเป็น "ปรับได้" ตามเดิม แค่มีช่องทางแก้เพิ่ม

## Impact

- **engine**:
  - `shortlist/config.py`: เพิ่มชื่อ, คำอธิบายภาษาไทย, หน่วย และช่วงค่าที่ยอมรับให้แต่ละ field
  - `shortlist/db.py`: เพิ่มตาราง `settings` เก็บค่าที่ผู้ใช้แก้
  - `shortlist/api.py`: เพิ่ม `GET/PUT/DELETE /settings` และให้ batch ใช้ config ที่รวมค่าที่แก้แล้ว
  - `shortlist/cli.py`: ใช้ config ที่รวมค่าที่แก้แล้วเหมือนกัน
- **web**: เพิ่มหน้า `app/settings/`, ลิงก์ใน header, ปุ่ม "ปรับเกณฑ์" ข้างปุ่มรัน batch บนหน้า candidates, component tooltip และป้ายเตือนบนหน้า candidates
- ไม่เพิ่ม dependency ทั้งสองฝั่ง
- **ข้อมูล**: ค่าที่แก้อยู่ใน SQLite ไม่อยู่ใน git ถ้าลบ `shortlist.db` ค่าจะกลับเป็น default
