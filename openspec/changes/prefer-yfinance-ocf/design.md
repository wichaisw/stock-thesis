# Design

## Context

ดู proposal.md (Why) `PreferredStatements` ใน `engine/shortlist/sources/preferred.py` ทับค่าของ thaifin ด้วยทุกคอลัมน์ที่ `fetch_statements` คืนมา โดยทับเฉพาะไตรมาสที่ thaifin มีและช่องที่ yfinance มีค่า (`overlay`) ตอนนี้ `to_statements` คืนแค่ `net_profit` และ `equity` จาก `quarterly_income_stmt` และ `quarterly_balance_sheet` และคืนตารางว่างถ้างบไม่ใช่สกุลบาท

ข้อมูลที่ตรวจแล้ว (BEM): OCF รายไตรมาสของ yfinance เป็นค่าของไตรมาสนั้น ไม่ใช่ยอดสะสม เพราะ 1Q25 (จาก snapshot) + 2Q25 + 3Q25 + 4Q25 = FY2025 พอดี และ yfinance มีแค่ราว 5 ไตรมาสล่าสุด บางไตรมาสเป็น NaN (1Q25)

## Goals / Non-Goals

**Goals:**
- เกณฑ์ OCF ของ quality gate อ่าน OCF ที่ตรงกับงบ

**Non-Goals:**
- เปลี่ยนเกณฑ์ OCF หรือรายการ sector ที่ข้ามเกณฑ์นี้

## Decisions

### D1: เพิ่ม `ocf` ใน `STATEMENT_ROWS` จาก `quarterly_cashflow` แถว "Operating Cash Flow"

`overlay` และ `PreferredStatements` ใช้ได้เลยโดยไม่ต้องแก้ เพราะทับทุกคอลัมน์ที่มีร่วมกัน เงื่อนไขสกุลบาทใช้กับ OCF ด้วย

- ทางเลือก: source ใหม่แยกเฉพาะ OCF ไม่เลือก เพราะซ้ำกับ overlay ที่มีอยู่และมี spec รองรับแล้ว
- ทางเลือก: แก้ thaifin ให้คิดไตรมาสจาก YTD ใหม่ ไม่เลือก เพราะไม่รู้ว่า thaifin คิดอย่างไร และยังไม่มีงบ YTD จาก SET ให้ตรวจ

### D2: cash flow ดึงไม่ได้ไม่ทำให้กำไรและส่วนผู้ถือหุ้นหาย

ถ้า `quarterly_cashflow` error หรือว่าง ให้ `ocf` เป็นค่าว่าง แต่ยังคืน `net_profit` และ `equity` ไม่ใช่คืนตารางว่างทั้งตาราง เพราะ `fetch_statements` จับ exception ครอบทั้งหมดอยู่

- ทางเลือก: ให้ error ของ cash flow ตกไปที่ except เดิม ไม่เลือก เพราะ request ที่เพิ่มมาหนึ่งตัวจะทำให้กำไรสุทธิที่เคยได้จาก yfinance หายไปด้วย

### D3: cross-check ก่อนใช้จริง

รัน skill `data-crosscheck` กับชุดหุ้นคงที่ (PTT, CPALL, SCAP, GULF; KBANK ข้ามเกณฑ์ OCF แต่ยังเทียบตัวเลข) และ BEM เทียบ OCF ของ yfinance กับงบบน SET (FY และไตรมาสที่หาได้) tolerance 2% ถ้าเกิน หยุดและรายงานก่อนรัน batch

## Risks / Trade-offs

- [กรณีเลวร้าย: yfinance ให้ OCF สะสม (YTD) ในบางหุ้น ทำให้ OCF ไตรมาส 2–4 ผิดเท่าตัวและเกณฑ์ OCF ตัดสินผิดทั้งตลาด] → D3 ตรวจก่อนใช้ และเทียบจำนวนหุ้นที่ผ่านเกณฑ์ OCF ก่อน/หลังใน batch ถ้าเปลี่ยนเกิน 10% ให้หยุดดูก่อน
- [ไตรมาสเก่าใน window ของเกณฑ์ (4 ไตรมาส) มาจาก thaifin ส่วนไตรมาสใหม่มาจาก yfinance ผสมสองแหล่ง] → เหมือนกำไรสุทธิที่ทำอยู่ และ yfinance มีครบ 4 ไตรมาสล่าสุดในหุ้นส่วนใหญ่
- [batch ช้าลงหนึ่ง request ต่อหุ้น] → ดูเวลาช่วงดึงงบใน log ของ batch เทียบ run ก่อน ถ้าเกินเวลารวมสูงสุดให้หยุดดูก่อน
- [backtest ยังใช้ thaifin ผลของ backtest จึงต่างจาก batch มากขึ้น] → อยู่ใน `LIMITATIONS` อยู่แล้ว

## Migration Plan

ไม่มี ข้อมูลใหม่จะมาเองใน batch ถัดไป ถ้าต้องถอยกลับให้ revert แล้วรัน batch ใหม่
