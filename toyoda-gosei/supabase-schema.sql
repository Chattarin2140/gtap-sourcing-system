-- Toyota Gazoo Thailand Automotive Buyers System
-- Run this in your Supabase SQL Editor

-- Car models table
CREATE TABLE IF NOT EXISTS car_models (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  category VARCHAR(50) NOT NULL, -- GR Sport, GR, Standard
  price_from NUMERIC(12, 0),
  price_to NUMERIC(12, 0),
  color VARCHAR(30),
  image_url TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Leads (interested buyers) table
CREATE TABLE IF NOT EXISTS leads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  email VARCHAR(100),
  line_id VARCHAR(50),
  interested_model_id UUID REFERENCES car_models(id),
  interested_model_name VARCHAR(100),
  budget_range VARCHAR(50),
  province VARCHAR(50),
  purchase_timeline VARCHAR(50), -- ทันที, 1-3 เดือน, 3-6 เดือน, 6+ เดือน
  notes TEXT,
  status VARCHAR(30) DEFAULT 'new', -- new, contacted, test_drive, negotiating, sold, lost
  assigned_to VARCHAR(100),
  source VARCHAR(50) DEFAULT 'website', -- website, walk-in, referral, social
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Status history table
CREATE TABLE IF NOT EXISTS lead_status_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  old_status VARCHAR(30),
  new_status VARCHAR(30),
  changed_by VARCHAR(100),
  note TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger to update updated_at on leads
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS leads_updated_at ON leads;
CREATE TRIGGER leads_updated_at
  BEFORE UPDATE ON leads
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Seed car models
INSERT INTO car_models (name, category, price_from, price_to) VALUES
  ('GR86', 'GR', 1990000, 2190000),
  ('GR Yaris', 'GR', 1590000, 1990000),
  ('GR Supra', 'GR', 3990000, 4490000),
  ('Corolla Altis GR Sport', 'GR Sport', 1129000, 1269000),
  ('Camry GR Sport', 'GR Sport', 1729000, 1999000),
  ('Fortuner GR Sport', 'GR Sport', 1499000, 1649000),
  ('Hilux Revo GR Sport', 'GR Sport', 949000, 1099000),
  ('Yaris Ativ GR Sport', 'GR Sport', 619000, 719000),
  ('Corolla Cross GR Sport', 'GR Sport', 939000, 989000),
  ('Veloz GR Sport', 'GR Sport', 869000, 919000)
ON CONFLICT DO NOTHING;

-- Enable Row Level Security (for production, configure policies)
ALTER TABLE car_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_status_history ENABLE ROW LEVEL SECURITY;

-- Drop existing policies before recreating
DROP POLICY IF EXISTS "car_models_public_read" ON car_models;
DROP POLICY IF EXISTS "leads_public_insert" ON leads;
DROP POLICY IF EXISTS "leads_service_role_all" ON leads;
DROP POLICY IF EXISTS "lead_history_service_role_all" ON lead_status_history;
DROP POLICY IF EXISTS "car_models_service_role_all" ON car_models;

-- Allow public read for car_models (for registration form)
CREATE POLICY "car_models_public_read" ON car_models FOR SELECT USING (is_active = true);

-- Allow public insert for leads (registration form)
CREATE POLICY "leads_public_insert" ON leads FOR INSERT WITH CHECK (true);

-- Allow all for service role (dashboard/admin)
CREATE POLICY "leads_service_role_all" ON leads FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "lead_history_service_role_all" ON lead_status_history FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "car_models_service_role_all" ON car_models FOR ALL USING (auth.role() = 'service_role');
