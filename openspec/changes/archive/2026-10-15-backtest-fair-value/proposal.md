# Proposal

## Why

fair value panel (PE band, PBV band, dividend yield band, peer PE, Justified PBV) เป็นตัวตัดสินว่าหุ้นตัวไหนเป็น candidate แต่ยังไม่เคยมีใครวัดว่าประเมินแม่นแค่ไหน backtest ที่มีอยู่ (`scripts/backtest_cdc.py`) วัดแค่ CDC และได้ข้อสรุปว่า "กำไรต้องมาจากเกณฑ์พื้นฐานและ margin of safety" ซึ่งยังไม่มีหลักฐานรองรับ ตอนนี้กำลังเพิ่มและแก้ method (`add-fair-value-methods`, `prefer-yfinance-statements`) จึงต้องมีตัววัดที่รันซ้ำได้ ใช้เทียบก่อนและหลังแก้ code

## What Changes

- skill ใหม่ `fair-value-backtest` (`.agents/skills/fair-value-backtest/` มี symlink ใน `.claude/skills/`) มี SKILL.md บอกขั้นตอนและวิธีอ่านผล พร้อม script ที่ทำงานตามนี้
  - ย้อนไปทุกสิ้นไตรมาสตั้งแต่ 2021Q1 ถึง 2026Q2 ประเมินหุ้นด้วย code จริงของ engine (`fair_value.evaluate`, `quality.evaluate`, `quality.liquidity`) โดยใช้แค่ข้อมูลที่มีอยู่ ณ วันนั้น (งบที่พ้นกำหนดส่งแล้ว: 45 วัน ส่วน Q4 60 วัน และราคา market cap จำนวนหุ้นที่ไม่เกินวันนั้น)
  - วัดผลที่ 63 วันทำการ (1 ไตรมาส ตาม thesis) แยกตาม method, median MoS และกลุ่ม candidate rule (ผ่าน quality และ median MoS ≥ เกณฑ์)
    - hit rate: % ที่ราคาขึ้นไปแตะ fair value ภายใน 63 วัน
    - excess return: ผลตอบแทนของกลุ่ม MoS ≥ เกณฑ์ ลบ equal-weight ของหุ้นทุกตัวที่ประเมินได้ในวันเดียวกัน
    - ผลตอบแทนแยกตาม bucket ของ MoS (MoS สูงกว่าได้ผลตอบแทนสูงกว่าจริงไหม)
  - ตัดหุ้นที่ข้อมูลเพี้ยนออกทั้งตัว: เคย split หรือจ่ายปันผลเป็นหุ้นในช่วงราคา 8 ปี หรือส่วนผู้ถือหุ้นเปลี่ยนเกิน 50% ในไตรมาสเดียว (merger, เพิ่มทุก) และข้ามวันที่ทดสอบที่ market cap ย้อนหลังขาด รายงานจำนวนและรายชื่อที่ตัด
  - ไม่ตัดค่าประเมินที่ผิดปกติ (MoS < −100%, fair value > 5× ราคา) เพราะเป็นความผิดพลาดจริงของ engine แต่แสดงแยกอีกตาราง
  - กัน look-ahead 3 ชั้น: ทุกรอบสุ่มประเมินซ้ำบางวันโดยแทนข้อมูลหลังวันทดสอบด้วยค่าขยะ ถ้าผลเปลี่ยนให้หยุดทันที, รายงานผลของ MoS ที่สลับมั่วระหว่างหุ้น (ควรได้ excess ราว 0) และ spot-check ด้วยมือเทียบ SET
  - เขียนผลเต็มเป็น markdown file `docs/backtests/fair-value-<วันที่รัน>.md` และพิมพ์ตารางเดียวกันออกจอ
- สรุปผลรอบแรกและลิงก์ไปยังไฟล์ผลใน `engine/README.md` ส่วน `## ผลตรวจข้อมูล`
- `stock-sanity-check` SKILL.md เพิ่มหนึ่งบรรทัด: หลังแก้ `core/fair_value` ให้รัน `fair-value-backtest` เทียบกับผลรอบก่อน

นอกขอบเขต:
- CDC (มี backtest แยกแล้ว) และ risk/reward (stop, RRR) จึงไม่จำลองการเทรดจริง ไม่มีค่าธรรมเนียมและ slippage
- เปลี่ยนสูตร fair value หรือเกณฑ์ใด ๆ จากผล backtest (ถ้าผลชี้ว่าควรแก้ เป็น change แยก)
- งบจาก yfinance (มีแค่ 5–6 ไตรมาส ย้อนหลังไม่พอ) backtest ใช้งบ thaifin อย่างเดียว
- แก้ survivorship bias (yfinance ไม่มีหุ้นที่ถูกถอน) และงบที่ถูก restate ย้อนหลัง บันทึกเป็นข้อจำกัด
- แปลงราคาของหุ้นที่ split หรือ merge ให้เทียบกันได้ (ตัดทิ้งแทน)
- ตัดหุ้นที่ split หรือ merge ออกจาก batch หรือ candidate list การตัดมีผลกับ backtest เท่านั้น แอปยังประเมินหุ้นเหล่านี้ตามเดิม
- หน้าเว็บหรือ API สำหรับผล backtest

ความสัมพันธ์กับ change อื่น:
- ไม่บล็อกและไม่ถูกบล็อกโดย change ไหน (ไม่แก้ code ของ engine ที่ change อื่นแตะ)
- ผลขึ้นกับ code ของ fair value ณ ตอนที่รัน ถ้ารันก่อน `add-fair-value-methods` 5.x หรือ `relax-quality-gate` 3.x เสร็จ ให้ระบุ commit ในไฟล์ผล (script ใส่ให้เอง) แล้วค่อยรันใหม่หลัง change เหล่านั้นจบเพื่อเทียบ

## Capabilities

### New Capabilities
- `fair-value-backtest`: วัดความแม่นของ fair value panel และ candidate rule ย้อนหลังแบบไม่มี look-ahead และบันทึกผลเป็น markdown

### Modified Capabilities
- (ไม่มี)

## Impact

- **engine**: module ใหม่ `shortlist/backtest.py` (ตัดข้อมูล ณ วันที่ทดสอบ และคำนวณตัววัด เป็น pure function) พร้อม `tests/test_backtest.py` ไม่แก้ module เดิม
- **skill**: `.agents/skills/fair-value-backtest/` (SKILL.md + `backtest.py` ที่ดึงข้อมูลและเขียนผล), symlink ใน `.claude/skills/`, หนึ่งบรรทัดใน `stock-sanity-check/SKILL.md`
- **ไฟล์ผล**: `docs/backtests/*.md` (commit ไว้เทียบรอบต่อรอบ) และ cache ข้อมูลดิบใน `engine/.cache/` (gitignore)
- **network**: ดึงราคา 8 ปีทั้งตลาดจาก yfinance และงบ thaifin + market cap ของหุ้นที่เคยผ่าน liquidity ราว 400 ตัว รอบแรกใช้เวลาหลายนาที รอบถัดไปใช้ cache
- ไม่เพิ่ม dependency
