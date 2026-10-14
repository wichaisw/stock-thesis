# Tasks

## 1. ตรวจ field ของ yfinance ก่อนเขียน code

- [x] 1.1 ใช้ skill `data-crosscheck` เทียบ `Net Income Common Stockholders` และ `Stockholders Equity` ของ yfinance (`quarterly_income_stmt`, `quarterly_balance_sheet`) กับงบรวมบน SET และกับ `net_profit`, `equity` ของ thaifin ของชุดหุ้นที่ใช้ตรวจ (PTT, CPALL, KBANK, SCAP, GULF) ทุกไตรมาสที่ yfinance มี และบันทึก `financialCurrency` ของแต่ละตัวพร้อม PTTEP (รายงานเป็น USD) บันทึกผลใน `engine/README.md` ตรวจด้วยตารางผลใน README ถ้าต่างจาก SET เกิน 2% หรือต่างจาก thaifin อย่างเป็นระบบ หยุดและรายงานก่อนทำกลุ่ม 2

## 2. Engine

- [x] 2.1 เพิ่มการดึงงบรายไตรมาสใน `sources/yahoo.py` ที่คืน `net_profit` และ `equity` index เป็น label ไตรมาส และคืนว่างเมื่อ `financialCurrency` ไม่ใช่ THB หรือดึงไม่ได้ (D3, D4, D5) พร้อม test ด้วยข้อมูลปลอม (แปลงวันที่เป็นไตรมาส, USD → ว่าง, ไม่มี currency → ว่าง, error → ว่าง) ตรวจด้วย `uv run pytest tests/test_sources.py`
- [x] 2.2 เพิ่ม adapter ใน `sources/` ที่ห่อ thaifin แล้วทับ `net_profit` และ `equity` เฉพาะไตรมาสที่ thaifin มีและช่องที่ yfinance มีค่า (D1, D2) พร้อม test ตาม scenario ของ requirement "กำไรสุทธิและส่วนผู้ถือหุ้นจากแหล่งราคาก่อน" (5 ไตรมาสล่าสุดจาก yfinance ที่เหลือจาก thaifin, ช่องว่างใช้ thaifin, ไตรมาสที่ thaifin ยังไม่มีไม่ถูกเพิ่ม) ตรวจด้วย `uv run pytest tests/test_sources.py`
- [x] 2.3 ให้ `batch.py` ใช้ adapter ที่รวมแล้ว และ log จำนวนหุ้นที่ใช้งบจาก yfinance ได้ เพิ่ม test ใน `test_batch.py` ว่าเมื่อแหล่งงบเสริม raise หุ้นยังถูกประเมินและไม่อยู่ใน failures ตรวจด้วย `uv run pytest`

## 3. Integration

- [ ] 3.1 บันทึก candidate list, median MoS และเวลา batch ของ run ล่าสุดไว้เทียบ แล้วรัน batch ใหม่ ตรวจว่า run สำเร็จ เวลาไม่เกินเพดาน และ log บอกจำนวนหุ้นที่ใช้งบจาก yfinance ตรวจด้วย skill `stock-sanity-check`
- [ ] 3.2 spot-check อย่างน้อย 3 หุ้น (รวมหุ้นธนาคาร 1 ตัว และหุ้นที่รายงานงบเป็น USD 1 ตัวถ้าผ่าน liquidity) คำนวณ ROE TTM และ Justified PBV ด้วยมือจากงบบน SET ให้ตรงกับหน้ารายละเอียดภายใน 1% เปิดหน้ารายละเอียดใน browser ด้วย skill `orca-browser-check` และอธิบายหุ้นที่เข้าหรือหลุดจาก candidate list เทียบกับ 3.1 บันทึกใน `engine/README.md`
