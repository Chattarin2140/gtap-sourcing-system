import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export async function GET() {
  const { data, error } = await supabaseAdmin
    .from("car_models")
    .select("*")
    .order("category")
    .order("name");

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ models: data });
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { name, category, price_from, price_to } = body;

  if (!name || !category) {
    return NextResponse.json({ error: "name and category required" }, { status: 400 });
  }

  const { data, error } = await supabaseAdmin
    .from("car_models")
    .insert({ name, category, price_from: price_from || null, price_to: price_to || null })
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ model: data }, { status: 201 });
}

export async function PATCH(req: NextRequest) {
  const body = await req.json();
  const { id, ...updates } = body;

  if (!id) {
    return NextResponse.json({ error: "id required" }, { status: 400 });
  }

  const { data, error } = await supabaseAdmin
    .from("car_models")
    .update(updates)
    .eq("id", id)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ model: data });
}
