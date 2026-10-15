# Design

## Context

ดู proposal.md (Why) สำหรับผล backtest และ spike ที่มาของ rule

สภาพปัจจุบันของ code:
- `core/candidates.py` อ่าน `fair_value.summary.median_mos` ทั้งใน `inclusion` (gate) และ `sort_key` (ลำดับที่ 3)
- `core/risk_reward.py` ใช้ `summary.median_fair_value` เป็น target และ `summary.max_fair_value` เป็น target แบบ optimistic
- `core/fair_value.summarize` สร้าง summary ของ panel จาก items (แต่ละ item มี `method`, `fair_value`, `mos`, เหตุผลเมื่อคำนวณไม่ได้)
- `batch.evaluate_stock` และ `backtest.evaluate_date` เรียก `fair_value.evaluate` แยกกัน และ backtest ตัดสิน candidate เองที่บรรทัดเดียว (`summary.median_mos ≥ min_median_mos`)
- config: `Candidates.min_median_mos` แก้บนเว็บได้ (`editable`) loader ข้าม override ที่ไม่รู้จักพร้อม log เตือนอยู่แล้ว (`load_config`) API แปลง `ValidationError` เป็น error ต่อช่องด้วย `loc[:2]`
- web: `app/page.tsx` คอลัมน์ "MoS ต่ำ / median / สูง" เน้น median, `app/stocks/[symbol]/page.tsx` ป้าย "Target (median fair value)", `lib/llm-export.ts` ป้ายเดียวกัน
- DB เก็บ evaluation ของ run ล่าสุดเท่านั้น

## Goals / Non-Goals

**Goals:**
- rule ของ gate ด้าน fair value อยู่ที่เดียวใน engine และ batch, backtest, web และข้อความ LLM อ่านผลชุดเดียวกัน
- backtest เทียบ rule ใหม่กับ rule เดิมได้ในไฟล์ผลเดียว

**Non-Goals:**
- ไม่เปลี่ยน `summary` ของ panel (median, min, max, label) และไม่เปลี่ยนสูตรของ method ใด
- ไม่ทำ UI สำหรับแก้ `gate_methods`

## Decisions

### D1: คำนวณ gate ครั้งเดียวใน engine และเก็บใน `fair_value.gate`
เพิ่ม pure function ใน `core/fair_value.py` ที่รับ items ของ panel กับรายชื่อ gate methods แล้วคืน `{"methods": [...], "items": [{method, mos, fair_value, reason}], "mos": <MoS ต่ำสุด>, "fair_value": <fair value ต่ำสุด>, "method": <method ที่ให้ค่านั้น>}` (ค่าเป็น None เมื่อไม่มีตัวที่คำนวณได้) batch และ backtest เรียกต่อจาก `fair_value.evaluate` แล้วเก็บไว้ที่ `ev["fair_value"]["gate"]` ส่วน `candidates`, `risk_reward`, web และ LLM export อ่านจากตรงนี้
- ทางเลือกที่ไม่เลือก: (ก) ให้ `candidates.inclusion` และ `risk_reward` คำนวณเองจาก items ซึ่งจะมี logic เดียวกันสองที่และอาจ drift ได้ (ข) ให้ web คำนวณจาก items ซึ่งจะมี rule ซ้ำใน TypeScript และ backtest ใช้ไม่ได้ (ค) ใส่ใน `summary` ซึ่งปน gate กับมุมมองของ panel ที่ spec บอกให้คงเดิม
- `fair_value.evaluate` ไม่รับ `Candidates` config จึงไม่เรียก gate ข้างใน เพื่อไม่ให้ fair value ผูกกับ config ของ candidates

### D2: MoS gate = MoS ต่ำสุดของ gate methods ที่คำนวณได้
"ทุกตัวที่คำนวณได้ ≥ เกณฑ์" เท่ากับ "ตัวต่ำสุด ≥ เกณฑ์" และเพราะทุก method ใช้ราคาเดียวกัน fair value ต่ำสุดจึงเป็นตัวเดียวกับ MoS ต่ำสุด ค่าตัวเดียวนี้จึงใช้ได้ทั้งเป็น gate, ตัวเรียง และ target (ผ่าน fair value ของมัน) ข้อดีคือแสดงในคอลัมน์เดียวได้
- ทางเลือกที่ไม่เลือก: ใช้ค่าเฉลี่ยของ gate methods เป็น target แต่ spike ทดสอบแค่ rule แบบ "ทุกตัว" และค่าเฉลี่ยทำให้ candidate บางตัวมี target ต่ำกว่าราคา ซึ่งเป็นปัญหาเดียวกับ median ที่ proposal ต้องการแก้
- `pe_minus_1sd` ที่รวมกับ `pe_median` เป็น view เดียว ไม่เกี่ยวกับ gate เพราะ gate methods ทั้งสองตัวเป็น method เดี่ยว

### D3: config
- `Candidates.gate_methods: list[FairValueMethod]` เป็น `Field(min_length=1)` ธรรมดา ไม่ใช่ `editable` จึงไม่ขึ้นบนหน้า settings และ override จากเว็บถูก API ปฏิเสธ (ช่องที่แก้บนเว็บไม่ได้)
- เปลี่ยนชื่อ `min_median_mos` เป็น `min_gate_mos` (ยัง `editable`) ค่าเก่าที่บันทึกบนเว็บถูก `load_config` ข้ามพร้อม log เตือนตามกลไกเดิม ไม่ต้องเขียน migration
- ทางเลือกที่ไม่เลือก: คงชื่อ `min_median_mos` ไว้ ซึ่งจะทำให้ชื่อโกหกความหมาย และย้ายค่าเก่ามาเป็นค่าใหม่อัตโนมัติ ซึ่งไม่ถูก เพราะความหมายต่างกัน (15% ของ median ไม่เท่ากับ 15% ของ gate)

### D4: ห้ามปิด gate method ทุกตัว ตรวจใน `Config`
เพิ่ม validator ระดับ `Config` ที่ตรวจว่า `fair_value.enabled ∩ candidates.gate_methods` ไม่ว่าง จึงใช้ทั้งกับ config.yaml และค่าที่บันทึกจากเว็บ (API validate ทั้งชุดก่อนบันทึกอยู่แล้ว) error ต้องแสดงที่ช่อง "เกณฑ์ fair value ที่ใช้" ถ้า `loc` ของ error ระดับ model ไม่ตรงกับ `fair_value.enabled` ให้ API map error นี้ไปที่ช่องนั้น ส่วน tooltip ของช่องนั้นต้องบอกว่า peer PE และ Justified PBV เป็น gate และการปิดตัวหนึ่งทำให้ rule ต่างจากที่ backtest ทดสอบ
- ทางเลือกที่ไม่เลือก: บังคับให้เปิด gate methods ทั้งสองตัว (ผู้ใช้เลือกให้ปิดได้ทีละตัว) หรือปล่อยให้บันทึกได้แล้ว list ว่าง (เงียบเกินไป)

### D5: backtest เพิ่มแถวเทียม `gate` และกลุ่ม `candidate (median)`
`evaluate_date` เพิ่มแถว method `gate` (fair value และ MoS จาก D1) ข้างแถว `median` และเก็บ flag สองตัว: `candidate` (rule ใหม่) และ `candidate_median` (rule เดิมด้วยเกณฑ์ `min_gate_mos`) `groups()` สร้างกลุ่ม `candidate` จากแถว `gate` และกลุ่ม `candidate (median)` จากแถว `median` ผลคือ hit rate ของ candidate วัดกับ target จริง, ตารางแบบไม่นับค่าผิดปกติใช้ flag `abnormal` ของแถวที่กลุ่มนั้นใช้ และ bucket table มีแถว `gate` เพิ่มโดยอัตโนมัติ
- ทางเลือกที่ไม่เลือก: ใช้แถว `median` สำหรับทั้งสองกลุ่ม (hit rate ของ candidate จะวัดกับ median ซึ่งไม่ใช่ target แล้ว) หรือสร้างตารางแยกสำหรับ rule เดิม (ทำซ้ำ code ของตาราง)
- regression: ด้วย cache และ config เดิม แถว `candidate (median)` ต้องได้ตัวเลขเท่ากับแถว `candidate` ของไฟล์ผล 2026-10-15

### D6: target ไม่มี fallback ไปที่ median
หุ้นที่ไม่มี gate method ที่คำนวณได้มี target และ RRR เป็น N/A พร้อมเหตุผล แม้ method อื่นคำนวณได้ หุ้นพวกนี้ไม่มีทางเป็น candidate อยู่แล้ว RRR ของหุ้นพวกนี้จึงเป็นแค่ข้อมูลประกอบ
- ทางเลือกที่ไม่เลือก: fallback ไปที่ median เพื่อให้หน้ารายละเอียดมี RRR มากขึ้น แต่จะทำให้ target มีสองความหมายในหน้าเดียวกัน และป้าย upside สูงผิดปกติอ่านค่าที่นิยามต่างกัน

### D7: web แสดงจาก `fair_value.gate` และไม่พังกับ run เก่า
type `FairValue` ใน `web/lib/engine.ts` มี `gate` เป็น optional, candidate list เพิ่มคอลัมน์ "MoS gate" (ค่า + ชื่อ method) และเลิกเน้น median, หน้ารายละเอียดแสดง gate methods แต่ละตัวในส่วน gate และเปลี่ยนป้าย target, LLM export เพิ่มบรรทัดอธิบาย gate และเปลี่ยนป้าย target เมื่อไม่มี `gate` (run ก่อน change นี้) แสดง N/A
- ทางเลือกที่ไม่เลือก: เติม `gate` ให้ run เก่าใน DB เพราะ DB เก็บแค่ run ล่าสุดและ batch ถัดไปจะเขียนทับอยู่แล้ว

## Risks / Trade-offs

- [กรณีแย่ที่สุด: edge เป็นผลบังเอิญจากการเลือก method ใน 22 วันที่เดียวกัน (in-sample) และ rule ใหม่ให้ผลแย่กว่า rule เดิมในไตรมาสถัดไปโดยที่ไม่มีใครเห็น] → แถว `candidate (median)` อยู่ในไฟล์ผลทุกครั้ง และรัน skill `fair-value-backtest` ทุกไตรมาส ถ้าช่วงความเชื่อมั่นของ candidate คร่อม 0 หรือแถว `candidate (median)` ดีกว่า ให้เปิด change ทบทวน rule ไม่ต้องแก้ code เพื่อดูผล
- [backtest ใช้งบ thaifin อย่างเดียว แต่ batch ใช้งบ yfinance ก่อน (`prefer-yfinance-statements`) Justified PBV ใช้ ROE TTM และ peer PE ใช้กำไร TTM ผลจริงจึงต่างจาก backtest ได้ในไตรมาสล่าสุด] → spot-check หุ้นจริงหลัง batch และดูเหตุผลที่ไม่ผ่านของหุ้นที่หลุด list
- [peer PE ต้องมี peer ใน sector ≥ `min_peers` และ Justified PBV มีเงื่อนไข ROE หุ้นจำนวนมากจึงไม่มี gate method ที่คำนวณได้ เหลือ candidate น้อย หรือ list ว่างบางวัน] → เทียบจำนวน candidate ก่อนและหลังใน task batch spike พบสัดส่วน 8–26% ของหุ้นที่ประเมินได้ ซึ่งน่าจะไม่ทำให้ list ว่าง ถ้า list ว่างจริง เหตุผลต่อหุ้นจะบอกว่าตกที่ gate ไหน
- [หุ้นที่ gate method คำนวณได้ตัวเดียวผ่านด้วยมุมมองเดียว ตัวที่ไม่มี peer PE เพราะ sector เล็กจะพึ่ง Justified PBV ตัวเดียว] → ยอมรับตาม rule D ที่ spike ทดสอบ (rule B ที่ต้องมีทั้งสองตัวไม่ผ่านช่วง 2021–2023)
- [target ต่ำลง (ตัวต่ำกว่าของสองตัว แทน median) RRR จึงต่ำลง ป้าย RRR ต่ำขึ้นบ่อยขึ้น และป้าย upside สูงผิดปกติขึ้นน้อยลง] → ตั้งใจให้เป็นแบบนี้ เป็นมุมมองระมัดระวัง ทั้งสองป้ายไม่ตัดหุ้นออก
- [ผู้ใช้เคยตั้ง median MoS ขั้นต่ำบนเว็บไว้ ค่านั้นหายไปเงียบๆ] → log เตือนจาก loader และหน้า settings แสดงช่องใหม่ที่ค่า default
- [archive ผิดลำดับ: archive change นี้ก่อน `strengthen-fair-value-backtest` ทำให้ archive ล้มเพราะหา header ไม่เจอ] → task สุดท้ายบังคับลำดับ

## Migration Plan

1. ลง code (engine, config, web) แล้วรัน batch ปกติ ไม่ต้อง migrate DB
2. ค่า `candidates.min_median_mos` ที่บันทึกบนเว็บถูกข้าม ไม่ต้องลบจาก DB เอง
3. Rollback: revert commit แล้วรัน batch ใหม่ ค่า `min_gate_mos` ที่บันทึกบนเว็บจะถูกข้ามด้วยกลไกเดียวกัน
