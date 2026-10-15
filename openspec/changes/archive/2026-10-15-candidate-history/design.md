# Design

## Context

`db.save_run` เขียน evaluations ของ run ใหม่แล้ว `DELETE FROM evaluations WHERE run_id < ?` ใน transaction เดียว candidate คือแถวที่ `candidate_rank IS NOT NULL` (14 ตัวใน run 33) evaluation JSON ของ candidate ยาวราว 2.6 KB ตาราง candidate บนหน้าแรก (`CandidateTable` ใน `web/app/page.tsx`) อ่าน field จาก evaluation โดยตรง และนับ Gates ด้วย `gateRows`/`gateTally` ใน `web/lib/gates.ts` วันนี้รัน batch ได้หลายรอบต่อวันที่ราคา (เช่น run 32 และ 33 ของ 15 ต.ค.)

## Goals / Non-Goals

**Goals:** ดู candidate list ของวันก่อน ๆ ได้ด้วยคอลัมน์เดิม โดยไม่เปลี่ยน batch หรือวิธีประเมิน

**Non-Goals:** หน้ารายละเอียดย้อนหลัง, settings ย้อนหลัง, ผลตอบแทนหลังวันนั้น

## Decisions

### D1: ตาราง `candidate_history (price_date, symbol, run_id, candidate_rank, result)` PK `(price_date, symbol)`
`result` คือ evaluation JSON เดียวกับใน evaluations (ผู้ใช้เลือก)
- ทางเลือกแถวย่อเฉพาะค่าที่แสดง (~0.5 KB): แถวเก่าไม่พังเมื่อรูป evaluation เปลี่ยน แต่ต้องนับ Gates และกฎของป้ายซ้ำใน Python ให้ตรงกับ `web/lib/gates.ts` ตลอด ผู้ใช้เลือกเก็บ JSON เต็ม
- ทางเลือกเลิกลบ evaluations ของ run เก่า: เก็บหุ้นทุกตัว ~1.8 MB ต่อ run และ query candidate ต้องรู้ run ของแต่ละวัน เกินความต้องการที่ขอแค่ candidate

### D2: เขียนใน transaction ของ `save_run`
`DELETE FROM candidate_history WHERE price_date=?` แล้ว insert candidate ของ run ใน transaction เดียวกับ evaluations run ที่ failed ไม่ผ่าน `save_run` จึงไม่เขียนเอง วันที่ไม่มี candidate ไม่มีแถวใน `candidate_history` จึงเพิ่มตาราง `candidate_history_days (price_date PK, run_id)` ที่ `save_run` เขียนทุก run ที่สำเร็จ (แทนแถวเดิมของวันที่ราคาเดียวกัน) รายการวันที่และจำนวนมาจากตารางนี้ left join จำนวนแถวในประวัติ
- ทางเลือกเขียนจาก batch.py หลัง `save_run`: run อาจสำเร็จแต่ประวัติไม่ถูกเขียนถ้า process ตายระหว่างสองขั้น
- ทางเลือกที่ไม่เลือก (แผนแรก): เอารายการวันที่จาก `runs` ที่ succeeded ตัดที่ `MIN(run_id)` ของ `candidate_history` พบตอน apply ว่าถ้า run หลังเริ่มใช้ยังไม่มี candidate เลย ไม่มีเส้นตัด วันที่ 0 ตัวจึงไม่โผล่ ขัดกับ scenario "run ไม่มี candidate"

### D3: seed ตอนสร้างตาราง
ใน `connect` ถ้าตารางยังไม่มี ให้สร้างแล้ว `INSERT ... SELECT` candidate ของ run ล่าสุดที่สำเร็จจาก evaluations และวันที่ของ run นั้นลง `candidate_history_days` เพื่อไม่ให้ list ของวันที่ apply หาย

### D4: API
`GET /candidates/history` คืน `[{price_date, count}]` เรียงใหม่ไปเก่า `GET /candidates/history/{price_date}` คืน `{price_date, run_id, candidates}` เรียงตาม rank (404 ถ้าไม่มีวันที่นั้น)

### D5: web ใช้ตารางเดียวกัน
ย้าย `CandidateTable` ออกจาก `page.tsx` เป็น `web/app/candidate-table.tsx` รับ prop `linkSymbols` (หน้าแรก true, หน้าประวัติ false) ทุกช่องที่อ่าน field ซ้อนใช้ optional chaining และแสดง "-" เมื่อไม่มีค่า หน้า `web/app/history/page.tsx` อ่านวันที่จาก search param `?date=` ไม่มีให้ใช้วันที่ล่าสุด รายการวันที่เป็นลิงก์ (ไม่ใช่ `<select>`) เพื่อให้ server component ไม่ต้องมี client JS
- ทางเลือกตารางแยกสำหรับประวัติ: คอลัมน์จะค่อย ๆ ไม่ตรงกับหน้าแรก

## Risks / Trade-offs

- **กรณีแย่สุด: รูป evaluation เปลี่ยนจนแถวเก่าทำให้หน้าประวัติ crash** (เช่น `fair_value.summary` เปลี่ยนชื่อ) หน้าทั้งหน้าใช้ไม่ได้จนกว่าจะแก้ component → optional chaining ทุกช่อง และ test render แถวที่ไม่มี field ของ change หลัง ๆ
- **ความหมายของคอลัมน์เปลี่ยนตามเวลา**: ค่าวันเก่าคิดด้วย code และเกณฑ์ของวันนั้น (เช่นก่อนและหลัง `gate-on-proven-methods`) เทียบข้ามช่วงต้องระวัง ไม่มี settings snapshot (นอกขอบเขต)
- **run ระหว่างวัน**: ถ้ารันก่อนตลาดปิด `price_date` คือเมื่อวาน run นั้นจะแทนประวัติของเมื่อวานด้วยราคาเดิมแต่เกณฑ์ปัจจุบัน ซึ่งเป็นพฤติกรรมที่ตั้งใจ (run หลังสุดของวันที่ราคาชนะ)
- **ขนาด DB** ราว 20–35 MB ต่อปี ไม่มีการลบ ถ้าโตเกินค่อยเพิ่ม retention
