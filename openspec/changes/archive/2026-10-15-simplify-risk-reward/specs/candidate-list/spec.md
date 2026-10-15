# Spec Delta

## MODIFIED Requirements

### Requirement: ข้อมูลที่แสดงใน candidate list
ระบบ SHALL แสดงหุ้นแต่ละตัวใน candidate list พร้อม symbol, sector, ราคาล่าสุด, CDC state และ ETA, สรุป fair value panel, RRR, ป้าย inflection, ป้ายเตือน RRR ต่ำ, ป้ายเตือน upside สูงผิดปกติ และวันที่ของข้อมูล

#### Scenario: เปิดดู candidate list
- **WHEN** ผู้ใช้เปิดหน้า candidate list หลัง batch รันสำเร็จ
- **THEN** ระบบแสดงหุ้นตามลำดับพร้อมข้อมูลครบทุกคอลัมน์ และระบุวันที่ของข้อมูลราคาล่าสุด
