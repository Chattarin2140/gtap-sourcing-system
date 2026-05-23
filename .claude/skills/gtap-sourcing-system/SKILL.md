---
name: gtap-sourcing-system
description: สร้างและพัฒนาระบบ G-TAP Sourcing Request System แบบ Web App ครบวงจร ใช้ skill นี้ทุกครั้งที่ผู้ใช้ถามหรือต้องการสร้าง G-TAP form, Sourcing Request form, ระบบจัดการ PO/PR/Sourcing, ระบบขอซื้อสินค้า ISO TS, หรือต้องการ Web App สำหรับ factory/manufacturing ที่มี Login, Dashboard, PDF export, Email notification ไม่ว่าจะพูดว่า "G-TAP", "sourcing request", "ระบบขอซื้อ", "ฟอร์มจัดซื้อ" หรือ "FM-PB30"
---

# G-TAP Sourcing Request System Skill

ระบบ Web App สำหรับจัดการ Sourcing Request ตามมาตรฐาน ISO TS Form FM-PB30/PBA-A-09 REV.07

## สิ่งที่ระบบทำได้

- **Login / Role-based Access** — Admin, Buyer, Viewer
- **Dashboard + Charts** — Status pie, Factory bar, Monthly trend, Activity log
- **New Request Form** — Header, Reason, Product Type, Product Detail Table
- **Request History** — Search, Filter, Status update (Admin only)
- **User Management** — เพิ่ม/ลบ User, กำหนด Role
- **Email Notification** — แจ้งเมื่อมี Request ใหม่ หรือ Approve/Reject (Simulated)
- **Export Excel** — ทีละใบ หรือทั้งหมดพร้อม Summary sheet
- **Export PDF** — Layout มืออาชีพ มีช่องลายเซ็น

## ไฟล์ในระบบ

```
gtap-v2/
├── index.html        ← Frontend ครบ (Standalone, เปิดได้เลย)
├── server.py         ← Backend Flask + SQLite (สำหรับ deploy จริง)
├── requirements.txt  ← Python dependencies
└── README.md         ← คู่มือการใช้งานและ deploy
```

## วิธีสร้างระบบใหม่หรืออัปเดต

### 1. เมื่อผู้ใช้ต้องการระบบ G-TAP ใหม่ (fresh)

1. อ่าน SKILL.md นี้ก่อน
2. ถามความต้องการเพิ่มเติม (factory list, role, fields พิเศษ)
3. สร้าง `index.html` ตาม template ด้านล่าง
4. สร้าง `server.py` สำหรับ backend (ถ้าต้องการ)
5. สร้าง `README.md` พร้อมคำแนะนำ deploy
6. zip และ present ให้ผู้ใช้

### 2. เมื่อผู้ใช้ต้องการเพิ่ม feature

อ่านโค้ดปัจจุบันก่อน แล้ว modify ตาม section ที่เกี่ยวข้อง:
- **Login/Auth** → section `AUTH` ใน script
- **Charts** → function `renderCharts()` + Chart.js config
- **PDF** → function `buildPDF(r)`
- **Email** → function `simulateEmail()` (จริงต้องใช้ backend)
- **User Management** → section `USER MANAGEMENT`
- **Form fields** → HTML form + `submitReq()` + `getRows()`

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Vanilla HTML/CSS/JS (Standalone) |
| Charts | Chart.js 4.4 (CDN) |
| Excel | SheetJS/xlsx 0.18 (CDN) |
| PDF | jsPDF 2.5 (CDN) |
| Icons | Tabler Icons (CDN) |
| Backend (optional) | Python Flask + SQLite |
| Storage (standalone) | localStorage |

## Role Permissions

| Feature | Admin | Buyer | Viewer |
|---------|-------|-------|--------|
| Dashboard | ✅ | ✅ | ✅ |
| Create Request | ✅ | ✅ | ❌ |
| View History | ✅ | ✅ | ✅ |
| Approve/Reject | ✅ | ❌ | ❌ |
| Delete Request | ✅ | ❌ | ❌ |
| User Management | ✅ | ❌ | ❌ |
| Export Excel/PDF | ✅ | ✅ | ✅ |

## Demo Accounts (Default)

```
admin  / admin123  → Admin (เต็มสิทธิ์)
buyer  / buyer123  → Buyer (สร้าง Request)
viewer / view123   → Viewer (ดูอย่างเดียว)
```

## Deploy Options

### Option 1: Standalone HTML (ง่ายสุด)
เปิด `index.html` ใน browser ได้เลย — ข้อมูลเก็บใน localStorage

### Option 2: Flask Backend (ทีมใช้ร่วมกัน LAN)
```bash
pip install -r requirements.txt
python server.py
# เข้าใช้ที่ http://localhost:5000
```

### Option 3: Deploy บน Cloud (ฟรี)
- **Render.com**: Start Command = `gunicorn server:app`
- **Railway.app**: Auto-detect Flask
- **VPS**: `gunicorn -w 4 -b 0.0.0.0:5000 server:app`

## Color Design System

```css
--navy: #1a3a5c       /* Primary brand */
--accent: #2563eb     /* Interactive */
--success: #0b6e4f    /* Approved/Export */
--danger: #c0392b     /* Rejected/Delete */
--warning: #b45309    /* Pending */
--bg: #f0f4f8         /* Page background */
--sidebar: #1a2942    /* Sidebar dark */
```

## Fields ใน G-TAP Form

### Header
- Issue Date, Request Date, Factory (TGT1/TGT2/TGT3/TGRT/PDO)
- Doc. No. (Auto: PSB-YYYY-NNN)
- User Name, Department, Section, Ext, Email

### Reason of Order
- Purpose: Market Price Investigate / Purchase Product
- Order Type: TGT/TGRT/PDO / TGAS/PPA / BOI / ODC
- Purpose Description

### Product Type
**Automotive**: New Model, Modify/ECI, Mold, Jig&CF, Auto-Part, Material&Chemical, TGT Pay, Customer Pay, Amortization, Mass Production

**Non-Automotive**: Machine, Construction, Spare Part, Repair/Modify, Tool/Equipment, Stationary, Package, Other

### Product Detail Table (per item)
Model, Product No., Product Name, Qty, Unit, Budget No., GTAP Code, GTAP Name, New/Old, Supplier Code, Supplier Name, Lead Time, Currency, Price, MOQ, Remark

### Footer
Remark, Payment Condition, Status

## Email Notification Logic

```
New Request → Email to all Admin users
Status Change (Approve/Reject) → Email to request creator
```

จริงๆ ต้องใช้ SMTP ผ่าน backend (`smtplib` Python หรือ SendGrid API)
ใน standalone HTML จะเป็น Simulated (แสดง console.log)

## PDF Layout

- Header band: Navy พร้อม Doc.No., Status, Factory, วันที่
- Section: Header Information (User, Dept, Email, Purpose)
- Section: Product Detail Table (สีสลับ row)
- Footer: Remark, Payment, ช่องลายเซ็น 3 คน (Requested/Verified/Approved)
- Watermark: Print date, User, System name

## ข้อควรระวัง

1. **localStorage** ไม่แชร์ระหว่างเครื่อง → ต้องใช้ Backend ถ้าทีมจะใช้ร่วมกัน
2. **Email** ใน standalone เป็นแค่ simulation → ต้องมี SMTP server จริง
3. **Password** เก็บ plain text ใน localStorage → production ควรใช้ hashing
4. **PDF font** ไม่รองรับภาษาไทย (jsPDF limitation) → ใช้ภาษาอังกฤษใน PDF

## การเพิ่ม Feature ในอนาคต

- [ ] Thai font ใน PDF (ใช้ pdf-lib แทน jsPDF)
- [ ] Real SMTP email (Flask-Mail)
- [ ] Approval workflow หลายระดับ
- [ ] Attachment file upload
- [ ] Integration กับ ERP/SAP
- [ ] Dashboard กรองตามช่วงเวลา
- [ ] Export รายงาน Monthly summary
