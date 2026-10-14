# Design

## Context

`batch.py` เรียก `fin_src.fetch_quarterly(sym)` (thaifin) แล้ว `prices_src.fetch_market_caps(sym)` (yfinance) ต่อหุ้นที่ผ่าน liquidity core รับ DataFrame ตาม `QUARTERLY_COLUMNS` index เป็น label ไตรมาส ("2026Q2") และถือว่าไตรมาสล่าสุดคือแถวสุดท้ายที่มี EPS จำนวนหุ้นมาจาก `get_shares_full` ของ yfinance อยู่แล้ว ตรวจ yfinance เบื้องต้น (15 ต.ค. 2026) พบว่า `quarterly_income_stmt` และ `quarterly_balance_sheet` ของ PTT.BK และ KBANK.BK มี 5–6 ไตรมาส (1Q25 หรือ 2Q25 ถึง 2Q26) และมี `Net Income Common Stockholders` และ `Stockholders Equity` ทั้งคู่

## Goals / Non-Goals

**Goals:**
- กำไรสุทธิและส่วนผู้ถือหุ้นของไตรมาสล่าสุดมาจาก yfinance เมื่อมีค่า โดย core ไม่ต้องแก้
- ดึงงบจาก yfinance ไม่ได้ต้องไม่ทำให้หุ้น fail หรือ batch ช้าลงมาก

**Non-Goals:**
- ไม่เปลี่ยน EPS, กำไร YoY, D/E, OCF, NPM, BVPS
- ไม่เก็บว่าค่าแต่ละช่องมาจากแหล่งไหน

## Decisions

### D1 รวมสองแหล่งใน adapter ที่ห่อ `FinancialSource` เดิม
- adapter ใหม่ใน `sources/` รับ thaifin source และฟังก์ชันดึงงบจาก yfinance แล้วคืน DataFrame รูปแบบกลางเดิม `batch.py` เปลี่ยนแค่ตอนสร้าง source
- ทางเลือก: รวมใน `batch.py` → ปฏิเสธ เพราะ batch จะรู้ชื่อ field ของแต่ละแหล่ง ขัดกับ requirement "เปลี่ยนแหล่งข้อมูลได้"
- ทางเลือก: รวมใน core → ปฏิเสธ core ต้องไม่รู้ว่าข้อมูลมาจากแหล่งไหน

### D2 ทับเฉพาะไตรมาสที่แหล่งงบมีอยู่แล้ว
- ใช้ label ไตรมาสจากวันสิ้นงวดของ yfinance (`2026-06-30` → `2026Q2`) แล้วทับ `net_profit` และ `equity` เฉพาะแถวที่ thaifin มี และเฉพาะช่องที่ yfinance มีค่า
- ทางเลือก: เพิ่มไตรมาสที่ yfinance มีแต่ thaifin ยังไม่มี → ปฏิเสธ แถวนั้นไม่มี EPS ตาม requirement "Clean ข้อมูลที่ยังไม่สมบูรณ์" จึงไม่ถูกนับเป็นงบล่าสุดอยู่ดี และจะเป็นแถวที่ข้อมูลไม่ครบ

### D3 ใช้ `Stockholders Equity` และ `Net Income`
- ทั้งคู่ไม่รวมส่วนได้เสียที่ไม่มีอำนาจควบคุม ตรงกับ `equity` และ `net_profit` ของ thaifin (task 1.1 ของ `add-fair-value-methods` พบว่า equity ของ thaifin เป็นของบริษัทใหญ่)
- ทางเลือก: `Total Equity Gross Minority Interest` / `Net Income Including Noncontrolling Interests` → ปฏิเสธ รวมส่วนของผู้ถือหุ้นส่วนน้อย ทำให้ ROE และ PBV เพี้ยนสำหรับบริษัทที่มีบริษัทย่อยใหญ่ (เช่น PTT, CPALL)
- ทางเลือก: `Net Income Common Stockholders` → ปฏิเสธหลัง task 1.1: หักดอกเบี้ยหุ้นกู้ด้อยสิทธิไม่มีกำหนดไถ่ถอนออก (CPALL −1.2% ถึง −1.75% ทุกไตรมาส) ไม่ตรงกับ SET และ thaifin ทำให้ PE band มีรอยต่อ ส่วน `Stockholders Equity` ยังรวมหุ้นกู้นั้นอยู่ ตัวตั้งกับตัวหารจึงไม่สอดคล้องกัน `Net Income` ตรงกับ SET ทุกตัว

### D4 ใช้งบจาก yfinance เฉพาะเมื่อ `financialCurrency` เป็น THB
- ทางเลือก: แปลงสกุลเงินด้วยอัตราแลกเปลี่ยน → ปฏิเสธ ต้องมีแหล่งอัตราแลกเปลี่ยนรายไตรมาสที่ยังไม่ได้ตรวจ และ thaifin รายงานเป็นบาทอยู่แล้ว
- ไม่มีค่า `financialCurrency` ถือว่าไม่ใช่ THB (ไม่เดา)

### D5 ดึงงบจาก yfinance ไม่ได้ ใช้ thaifin ทั้งหมดโดยไม่ fail และไม่นับเป็น network error
- การตรวจเน็ตล่มยังมาจาก `fetch_market_caps` ที่เรียกต่อทันทีสำหรับหุ้นเดียวกัน จึงไม่ต้องนับซ้ำ
- ทางเลือก: ให้หุ้น fail → ปฏิเสธ thaifin ยังมีข้อมูลที่ใช้ได้ และการ fail จะทำให้ candidate หายเพราะแหล่งเสริม

## Risks / Trade-offs

- [worst case: `Stockholders Equity` หรือ `Net Income Common Stockholders` ของ yfinance ผิดเงียบๆ (หน่วย, งบเฉพาะกิจการแทนงบรวม, ไตรมาสเลื่อน) ทำให้ ROE TTM และ fair value ของทุกหุ้นเพี้ยน candidate list ผิดทั้งชุด] → task 1 cross-check กับงบบน SET ก่อนเขียน code และ spot-check หลังรัน batch
- [ไตรมาสล่าสุดมาจาก yfinance แต่ไตรมาสเก่ามาจาก thaifin ถ้าสองแหล่งนิยามต่างกันเล็กน้อย PE band จะมีรอยต่อ] → cross-check ไตรมาสที่ซ้อนกันของสองแหล่ง ถ้าต่างเกิน 2% อย่างเป็นระบบ หยุดก่อน
- [EPS TTM ที่แสดงยังมาจาก thaifin แต่ PE ใช้กำไรจาก yfinance ตัวเลขในหน้ารายละเอียดอาจไม่ตรงกันเล็กน้อย] → ยอมรับ EPS ใช้แสดงผลเท่านั้น
- [request เพิ่ม 2 ครั้งต่อหุ้น batch ช้าลงหรือโดน rate limit ของ Yahoo] → วัดเวลาใน task integration เทียบกับ run ก่อน ยังมีเพดาน 20 นาทีอยู่
- [yfinance เปลี่ยนชื่อ row โดยไม่บอก ทำให้ทุกหุ้นกลับไปใช้ thaifin เงียบๆ] → log จำนวนหุ้นที่ใช้ค่าจาก yfinance ได้ในแต่ละ run

## Migration Plan

- ไม่มี schema เปลี่ยน ค่าใหม่มีผลตั้งแต่ batch ถัดไป
- rollback: revert commit แล้วรัน batch ใหม่
