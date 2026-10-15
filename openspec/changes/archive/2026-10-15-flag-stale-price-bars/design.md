# Design

## Context

ดู proposal.md (Why) ตอนนี้ `batch.collect` ตั้ง `price_date` ของ run เป็น `max` ของ `price_date` ของทุก evaluation และแต่ละ evaluation มี `price_date` ของตัวเองอยู่แล้ว (วันที่แท่งล่าสุดหลัง `clean_prices` ตัดแท่งที่ไม่มี close) evaluation ทั้งหมดเก็บเป็น JSON ใน `evaluations.result` และ `save_run` ลบ evaluation ของ run ก่อนหน้า จึงเหลือแค่ของ run ล่าสุด หน้า candidate list อ่าน run จาก `/runs/latest` (`latest_successful_run`)

## Goals / Non-Goals

**Goals:**
- เห็นทันทีที่หน้า candidate list ว่าราคาของ run ไม่ครบ โดยไม่ต้องเทียบ TradingView เอง
- ป้ายตามแบบเดียวกับ `low_rrr`/`high_upside` (flag ในผล + Tag ใน UI)

**Non-Goals:**
- เปลี่ยน schema ของฐานข้อมูล

## Decisions

**D1 วันที่อ้างอิงคือ `price_date` ของ run (max ของทุกหุ้น)**
ทางเลือกที่ไม่เลือก: วันที่วันนี้หรือวันทำการก่อนหน้า (ไม่มีปฏิทินวันหยุดของ SET เช่น 13 ต.ค. เป็นวันหยุด และรันหลังเที่ยงคืนวันที่ก็เปลี่ยนแล้ว จะเตือนผิดทุกครั้ง), วันที่ที่พบบ่อยที่สุด (mode) (กรณี 15 ต.ค. mode คือ 12 ต.ค. จะเตือนหุ้น 25 ตัวที่ราคาถูกแทนที่จะเตือน 897 ตัวที่ผิด) ข้อแลก: ถ้าหุ้นทุกตัวขาดแท่งเดียวกันจะไม่มีป้าย

**D2 ติด `stale_price` ใน evaluation ที่ `batch.collect` หลังคำนวณ `price_date` ของ run**
ป้ายต้องรู้ผลของทุกหุ้นก่อน จึงทำใน `evaluate_stock` (ทีละตัว) ไม่ได้ ทางเลือกที่ไม่เลือก: คำนวณตอนอ่านที่ API (ต้องคิดซ้ำทุก endpoint ที่คืน evaluation และ LLM export ฝั่ง web ต้องรู้วันที่ของ run)

**D3 จำนวนระดับ run คำนวณตอนอ่านใน `latest_successful_run`**
เพิ่ม `stale_count` และ `stale_date` (วันที่ที่พบบ่อยที่สุดในกลุ่มที่ราคาไม่อัปเดต) ด้วย query บน `evaluations` ของ run นั้น ทางเลือกที่ไม่เลือก: เพิ่มคอลัมน์ใน `runs` (ต้อง `ALTER TABLE` กับ DB เดิมเพราะ `CREATE TABLE IF NOT EXISTS` ไม่เพิ่มคอลัมน์) run ที่สำเร็จล่าสุดยังมี evaluation อยู่เสมอ จึง query ได้ run เก่าที่ไม่มี `stale_price` ใน JSON ได้ `stale_count` 0

**D4 Web อ่านแบบ optional (`stale_price?: boolean`, `stale_count?: number`, `stale_date?: string | null`)**
run เก่าไม่มี field จึงต้องไม่พัง ตามแบบ `high_upside?` บรรทัดเตือนระดับ run แสดงเมื่อ `stale_count > 0` และใช้จำนวนหุ้นที่ประเมินได้ (`succeeded`) เป็นตัวหาร

**D5 batch log บอกจำนวนหุ้นที่ราคาไม่อัปเดต**
ต่อท้ายบรรทัด log candidates เดิม เพื่อให้รันจาก cron/CLI แล้วเห็นได้โดยไม่ต้องเปิดเว็บ

## Risks / Trade-offs

- [หุ้นที่หยุดซื้อขาย (SP) หรือไม่มีการซื้อขายในวันนั้นติดป้ายด้วย] → เป็นแค่ป้าย และเป็นข้อมูลที่ควรรู้อยู่แล้วว่าราคาเก่า
- [Worst case: yfinance ขาดแท่งล่าสุดของทุกหุ้นพร้อมกัน ไม่มีป้ายเลย และ run บอกวันที่เก่าโดยไม่เตือน] → วันที่ราคาของ run ยังแสดงอยู่ ผู้ใช้เห็นได้ว่าเป็นวันไหน ถ้าเกิดซ้ำให้ทำ change ใหม่ที่เทียบกับปฏิทิน SET
- [Worst case อีกแบบ: ผู้ใช้ไม่สังเกตบรรทัดเตือนแล้วใช้ entry ที่ผิด] → แสดงเป็นสีเตือนใต้วันที่ราคา และติดป้ายที่ candidate ทุกตัวที่ได้รับผล

## Migration Plan

Deploy ตามปกติแล้วรัน batch ใหม่ ไม่มี migration ของ DB rollback คือ revert commit
