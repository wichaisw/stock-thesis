# Spec Delta

## MODIFIED Requirements

### Requirement: คำอธิบายวิธีคิด
ข้อความที่คัดลอก SHALL มีคำอธิบายภาษาอังกฤษหนึ่งบรรทัดของแต่ละเกณฑ์ fair value ที่อยู่ในข้อความ ของสูตร MoS และของ gate ด้าน fair value (ทุก gate method ที่คำนวณได้ต้องมี MoS ≥ เกณฑ์ และ target คือ fair value ที่ต่ำกว่าของ gate methods ไม่ใช่ median ของ panel) พร้อมชื่อ gate methods และ MoS gate ของหุ้นตัวนั้น เพื่อให้ LLM ตัดสินได้ว่าเกณฑ์ไหนเหมาะกับหุ้นตัวนั้น

#### Scenario: อธิบาย dividend yield band
- **WHEN** ข้อความมีเกณฑ์ dividend yield band
- **THEN** ข้อความอธิบายว่าเกณฑ์นี้คือปันผลเงินสด 12 เดือนล่าสุด ÷ median yield 12 เดือนใน 5 ปี ไม่นับปันผลเป็นหุ้นและไตรมาสที่ yield ต่ำกว่าเกณฑ์ขั้นต่ำ

#### Scenario: อธิบาย gate และ target
- **WHEN** ผู้ใช้คัดลอกหุ้นที่มี MoS gate 12% จาก Justified PBV และ target 14.20 บาท
- **THEN** ข้อความระบุว่า gate methods คือ peer PE และ Justified PBV, MoS gate +12.0% (Justified PBV) และป้ายของ target บอกว่าเป็น fair value ที่ต่ำกว่าของ gate methods ไม่ใช่ median fair value
