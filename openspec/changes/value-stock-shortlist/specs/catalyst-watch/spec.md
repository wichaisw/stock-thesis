# Spec Delta

## Purpose

ช่วยผู้ใช้คิดเรื่อง catalyst โดยแนะนำ catalyst และ lead indicator ที่ควรจับตาตาม sector และแสดงวันที่ที่ตลาดจะได้เห็นข้อมูลใหม่ภายใน 6 เดือน โดยไม่ใช้เป็นตัวคัดหุ้น

## ADDED Requirements

### Requirement: Catalyst hints ตาม sector
ระบบ SHALL แสดงรายการ catalyst และ lead indicator ที่น่าจับตาตาม sector ของหุ้น โดยอ่านจาก mapping ใน config ถ้า sector ไม่มีใน mapping SHALL แสดงรายการ hint ทั่วไปแทน

#### Scenario: หุ้นโรงแรม
- **WHEN** ผู้ใช้เปิดหน้ารายละเอียดของหุ้นใน sector โรงแรม และ mapping มี sector นี้
- **THEN** หน้ารายละเอียดแสดง hint เช่น ยอด booking และจำนวนนักท่องเที่ยว

#### Scenario: sector ไม่มีใน mapping
- **WHEN** ผู้ใช้เปิดหน้ารายละเอียดของหุ้นที่ sector ไม่มีใน mapping
- **THEN** หน้ารายละเอียดแสดง hint ทั่วไป

### Requirement: Event calendar อัตโนมัติ
ระบบ SHALL แสดงวันที่ในอีก 6 เดือนข้างหน้าของ (1) กำหนดส่งงบที่ประมาณจากวันจบไตรมาส: 45 วันสำหรับไตรมาส 1–3 และ 60 วันสำหรับงบปี และ (2) วัน SET50/100 review จากรายการใน config ทุกวันที่ที่ประมาณขึ้น SHALL ถูกระบุว่าเป็นค่าประมาณ

#### Scenario: กำหนดส่งงบไตรมาส 3
- **WHEN** วันนี้คือ 14 ตุลาคม 2026
- **THEN** event calendar แสดงกำหนดส่งงบไตรมาส 3/2026 ประมาณวันที่ 14 พฤศจิกายน 2026 และกำหนดส่งงบปี 2026 ประมาณวันที่ 1 มีนาคม 2027 พร้อมป้ายว่าเป็นค่าประมาณ

### Requirement: Event แบบ manual
ระบบ SHALL ให้ผู้ใช้เพิ่มและลบ event ของหุ้นแต่ละตัวได้เอง (เช่น วัน XD, ผลประมูล) โดยมีวันที่และข้อความ และ SHALL แสดง event ที่อยู่ในอีก 6 เดือนข้างหน้ารวมกับ event อัตโนมัติ

#### Scenario: เพิ่มวัน XD
- **WHEN** ผู้ใช้เพิ่ม event "XD 0.50 บาท" ของหุ้นตัวหนึ่ง วันที่อยู่ในอีก 2 เดือน
- **THEN** event นั้นแสดงใน event calendar ของหุ้นตัวนั้น และยังอยู่หลัง batch รันรอบถัดไป

#### Scenario: event เลยวันไปแล้ว
- **WHEN** วันที่ของ event manual ผ่านไปแล้ว
- **THEN** event นั้นไม่แสดงใน event calendar

### Requirement: Catalyst ไม่ใช่ตัวคัดหุ้น
ระบบ SHALL ไม่ใช้ catalyst hints หรือ event calendar ในการตัดหุ้นออกจาก candidate list

#### Scenario: หุ้นไม่มี event manual
- **WHEN** หุ้นผ่านทุก gate แต่ไม่มี event manual
- **THEN** หุ้นยังอยู่ใน candidate list
