# Spec Delta

## ADDED Requirements

### Requirement: ป้ายเตือน upside สูงผิดปกติ
ระบบ SHALL ติดป้ายเตือนเมื่อ upside = (target − entry) / entry สูงกว่าเกณฑ์ (default 100%, ปรับได้ในหน้า settings) เพื่อบอกว่า target อาจถูก band ในอดีตดึงสูงเกินจริง ระบบ SHALL ไม่ตัดหุ้นออกและไม่ใช้ป้ายนี้ในการเรียงลำดับ

#### Scenario: upside เกินเกณฑ์
- **WHEN** entry 2.70 และ target 15.73 (upside 483%)
- **THEN** หุ้นถูกติดป้ายเตือน upside สูงผิดปกติ และยังอยู่ใน candidate list ถ้าผ่าน gate อื่น

#### Scenario: upside ไม่เกินเกณฑ์
- **WHEN** entry 12.40 และ target 14.20 (upside 14.5%)
- **THEN** ไม่มีป้ายเตือน upside สูงผิดปกติ

#### Scenario: ไม่มี upside
- **WHEN** target ต่ำกว่าหรือเท่ากับ entry หรือ fair value panel ไม่มีเกณฑ์ที่คำนวณได้
- **THEN** ไม่มีป้ายเตือน upside สูงผิดปกติ

## REMOVED Requirements

### Requirement: Reward ต่อเดือน
**Reason**: ระยะถือถูก clamp ที่ 1 เดือนแทบทุกครั้ง reward ต่อเดือนจึงเท่ากับ upside แต่ดูเหมือนตัวเลขต่อเดือนที่แม่นยำ และสมมติว่าราคาถึง fair value ภายในรอบงบเดียว ผู้ใช้ไม่ต้องการให้ระยะเวลาถือกำหนดสูตร
**Migration**: ดู upside ซึ่งแสดงอยู่แล้ว ระยะถือที่คาดและเกณฑ์ระยะถือขั้นต่ำ/สูงสุดถูกลบออกด้วย
