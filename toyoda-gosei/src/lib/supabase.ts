import { createClient, SupabaseClient } from '@supabase/supabase-js'

const getSupabaseUrl = () => process.env.NEXT_PUBLIC_SUPABASE_URL ?? ''
const getAnonKey = () => process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? ''
const getServiceKey = () => process.env.SUPABASE_SERVICE_ROLE_KEY ?? ''

let _supabase: SupabaseClient | null = null
let _supabaseAdmin: SupabaseClient | null = null

export const getSupabase = () => {
  if (!_supabase) _supabase = createClient(getSupabaseUrl(), getAnonKey())
  return _supabase
}

export const getSupabaseAdmin = () => {
  if (!_supabaseAdmin) _supabaseAdmin = createClient(getSupabaseUrl(), getServiceKey())
  return _supabaseAdmin
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const supabase = new Proxy({} as SupabaseClient, {
  get: (_, prop) => {
    const client = getSupabase()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const val = (client as any)[prop]
    return typeof val === 'function' ? val.bind(client) : val
  },
})

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const supabaseAdmin = new Proxy({} as SupabaseClient, {
  get: (_, prop) => {
    const client = getSupabaseAdmin()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const val = (client as any)[prop]
    return typeof val === 'function' ? val.bind(client) : val
  },
})

export type CarModel = {
  id: string
  name: string
  category: string
  price_from: number | null
  price_to: number | null
  is_active: boolean
  created_at: string
}

export type Lead = {
  id: string
  full_name: string
  phone: string
  email: string | null
  line_id: string | null
  interested_model_id: string | null
  interested_model_name: string | null
  budget_range: string | null
  province: string | null
  purchase_timeline: string | null
  notes: string | null
  status: LeadStatus
  assigned_to: string | null
  source: string
  created_at: string
  updated_at: string
}

export type LeadStatus = 'new' | 'contacted' | 'test_drive' | 'negotiating' | 'sold' | 'lost'

export const STATUS_LABELS: Record<LeadStatus, string> = {
  new: 'ลูกค้าใหม่',
  contacted: 'ติดต่อแล้ว',
  test_drive: 'นัด Test Drive',
  negotiating: 'กำลังเจรจา',
  sold: 'ปิดดีล',
  lost: 'เสียลูกค้า',
}

export const STATUS_COLORS: Record<LeadStatus, string> = {
  new: 'bg-blue-100 text-blue-800',
  contacted: 'bg-yellow-100 text-yellow-800',
  test_drive: 'bg-purple-100 text-purple-800',
  negotiating: 'bg-orange-100 text-orange-800',
  sold: 'bg-green-100 text-green-800',
  lost: 'bg-red-100 text-red-800',
}

export const TIMELINES = [
  'ทันที (ภายใน 1 เดือน)',
  '1-3 เดือน',
  '3-6 เดือน',
  '6 เดือนขึ้นไป',
  'กำลังหาข้อมูล',
]

export const BUDGET_RANGES = [
  'ต่ำกว่า 700,000 บาท',
  '700,000 - 1,000,000 บาท',
  '1,000,000 - 1,500,000 บาท',
  '1,500,000 - 2,000,000 บาท',
  '2,000,000 - 3,000,000 บาท',
  '3,000,000 บาทขึ้นไป',
]

export const PROVINCES = [
  'กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร',
  'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท',
  'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง',
  'ตราด', 'ตาก', 'นครนายก', 'นครปฐม', 'นครพนม',
  'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส',
  'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์',
  'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พะเยา', 'พังงา',
  'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์',
  'แพร่', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน',
  'ยโสธร', 'ยะลา', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง',
  'ราชบุรี', 'ลพบุรี', 'ลำปาง', 'ลำพูน', 'เลย',
  'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ',
  'สมุทรสงคราม', 'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี',
  'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย',
  'หนองบัวลำภู', 'อ่างทอง', 'อำนาจเจริญ', 'อุดรธานี', 'อุตรดิตถ์',
  'อุทัยธานี', 'อุบลราชธานี',
]
