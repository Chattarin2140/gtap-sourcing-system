# Toyota Gazoo Thailand - Automotive Buyers System

## ขั้นตอนการ Setup

### 1. สร้าง Supabase Project

1. ไปที่ [supabase.com](https://supabase.com) และสร้าง account (ฟรี)
2. กด **New Project** ตั้งชื่อว่า `toyoda-gosei`
3. เลือก Region: **Southeast Asia (Singapore)**
4. รอ project สร้างเสร็จ (~2 นาที)

### 2. สร้าง Database Tables

1. ใน Supabase Dashboard ไปที่ **SQL Editor**
2. คัดลอก code ทั้งหมดจากไฟล์ `supabase-schema.sql`
3. วางใน SQL Editor แล้วกด **Run**

### 3. ตั้งค่า Environment Variables

1. ใน Supabase Dashboard ไปที่ **Settings > API**
2. คัดลอก:
   - **Project URL** (NEXT_PUBLIC_SUPABASE_URL)
   - **anon/public key** (NEXT_PUBLIC_SUPABASE_ANON_KEY)
   - **service_role key** (SUPABASE_SERVICE_ROLE_KEY)
3. แก้ไขไฟล์ `.env.local` ใส่ค่าที่ copy มา

### 4. รัน Development Server

```bash
cd toyoda-gosei
npm run dev
```

เปิดเบราว์เซอร์ที่ http://localhost:3000

### 5. Deploy บน Vercel

```bash
npx vercel
```

หรือ:
1. Push code ขึ้น GitHub
2. ไปที่ [vercel.com](https://vercel.com) และ import project
3. ตั้ง Environment Variables ใน Vercel Dashboard
4. Deploy!

---

## หน้าต่างๆ

| หน้า | URL | คำอธิบาย |
|------|-----|----------|
| ลงทะเบียน | `/` | ฟอร์มสำหรับลูกค้าที่สนใจซื้อรถ |
| Dashboard | `/dashboard` | สำหรับ admin ดู leads และเปลี่ยนสถานะ |

## Features

- ฟอร์มลงทะเบียนผู้สนใจซื้อรถ (ชื่อ, เบอร์, อีเมล, LINE, รุ่นรถ, งบ, จังหวัด)
- Dashboard สรุป Leads พร้อม stats
- Filter leads ตาม status pipeline
- ค้นหา leads
- เปลี่ยน status lead (New > Contacted > Test Drive > Negotiating > Sold/Lost)
- Export CSV (รองรับภาษาไทย)
- รุ่นรถ Toyota GR ทั้งหมด preloaded

## โครงสร้าง Pipeline

| Status | ความหมาย |
|--------|----------|
| New | ลูกค้าใหม่ที่เพิ่งลงทะเบียน |
| Contacted | ทีมงานติดต่อแล้ว |
| Test Drive | นัด Test Drive แล้ว |
| Negotiating | กำลังเจรจาราคา |
| Sold | ปิดดีลสำเร็จ |
| Lost | ลูกค้าไม่ซื้อ |
