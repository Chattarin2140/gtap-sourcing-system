import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin, STATUS_LABELS, LeadStatus } from "@/lib/supabase";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const status = searchParams.get("status");

  let query = supabaseAdmin
    .from("leads")
    .select("*")
    .order("created_at", { ascending: false });

  if (status && status !== "all") {
    query = query.eq("status", status);
  }

  const { data, error } = await query;

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  const headers = [
    "ชื่อ-นามสกุล",
    "เบอร์โทร",
    "อีเมล",
    "LINE ID",
    "รุ่นรถที่สนใจ",
    "งบประมาณ",
    "จังหวัด",
    "ระยะเวลาซื้อ",
    "สถานะ",
    "ที่มา",
    "หมายเหตุ",
    "วันที่ลงทะเบียน",
  ];

  const rows = (data ?? []).map((lead) => [
    lead.full_name,
    lead.phone,
    lead.email ?? "",
    lead.line_id ?? "",
    lead.interested_model_name ?? "",
    lead.budget_range ?? "",
    lead.province ?? "",
    lead.purchase_timeline ?? "",
    STATUS_LABELS[lead.status as LeadStatus] ?? lead.status,
    lead.source,
    (lead.notes ?? "").replace(/\n/g, " "),
    new Date(lead.created_at).toLocaleDateString("th-TH"),
  ]);

  const csvRows = [headers, ...rows].map((row) =>
    row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")
  );

  const bom = "﻿";
  const csv = bom + csvRows.join("\r\n");

  return new NextResponse(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="toyota-gr-leads-${new Date().toISOString().slice(0, 10)}.csv"`,
    },
  });
}
