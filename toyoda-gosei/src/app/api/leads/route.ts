import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const status = searchParams.get("status");
  const search = searchParams.get("search");
  const page = parseInt(searchParams.get("page") ?? "1");
  const pageSize = 20;

  let query = supabaseAdmin
    .from("leads")
    .select("*", { count: "exact" })
    .order("created_at", { ascending: false })
    .range((page - 1) * pageSize, page * pageSize - 1);

  if (status && status !== "all") {
    query = query.eq("status", status);
  }

  if (search) {
    query = query.or(
      `full_name.ilike.%${search}%,phone.ilike.%${search}%,email.ilike.%${search}%`
    );
  }

  const { data, error, count } = await query;

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ leads: data, total: count, page, pageSize });
}

export async function PATCH(req: NextRequest) {
  const body = await req.json();
  const { id, status, assigned_to, notes } = body;

  if (!id) {
    return NextResponse.json({ error: "id required" }, { status: 400 });
  }

  const { data: existing } = await supabaseAdmin
    .from("leads")
    .select("status")
    .eq("id", id)
    .single();

  const { data, error } = await supabaseAdmin
    .from("leads")
    .update({ status, assigned_to, notes })
    .eq("id", id)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  if (existing?.status !== status) {
    await supabaseAdmin.from("lead_status_history").insert({
      lead_id: id,
      old_status: existing?.status,
      new_status: status,
    });
  }

  return NextResponse.json({ lead: data });
}
