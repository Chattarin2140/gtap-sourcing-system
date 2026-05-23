"use client";

import { useState, useEffect } from "react";
import { supabase, CarModel, TIMELINES, BUDGET_RANGES, PROVINCES } from "@/lib/supabase";

type FormState = {
  full_name: string;
  phone: string;
  email: string;
  line_id: string;
  interested_model_id: string;
  budget_range: string;
  province: string;
  purchase_timeline: string;
  notes: string;
  source: string;
};

const INITIAL: FormState = {
  full_name: "",
  phone: "",
  email: "",
  line_id: "",
  interested_model_id: "",
  budget_range: "",
  province: "",
  purchase_timeline: "",
  notes: "",
  source: "website",
};

export default function BuyerRegistrationForm() {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [models, setModels] = useState<CarModel[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    supabase
      .from("car_models")
      .select("*")
      .eq("is_active", true)
      .order("category")
      .order("name")
      .then(({ data }) => {
        if (data) setModels(data);
      });
  }, []);

  const set = (key: keyof FormState) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const selectedModel = models.find((m) => m.id === form.interested_model_id);

    const { error: err } = await supabase.from("leads").insert({
      ...form,
      interested_model_name: selectedModel?.name ?? null,
    });

    setSubmitting(false);
    if (err) {
      setError("เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง: " + err.message);
    } else {
      setSubmitted(true);
    }
  };

  if (submitted) {
    return (
      <div className="p-10 text-center">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">ลงทะเบียนสำเร็จ</h2>
        <p className="text-gray-600 mb-6">
          ขอบคุณที่สนใจรถยนต์ Toyota GR ทีมงานของเราจะติดต่อกลับภายใน 24 ชั่วโมง
        </p>
        <button
          onClick={() => { setSubmitted(false); setForm(INITIAL); }}
          className="bg-[#eb0a1e] text-white px-6 py-3 rounded-full font-medium hover:bg-red-700 transition-colors"
        >
          ลงทะเบียนอีกครั้ง
        </button>
      </div>
    );
  }

  const grModels = models.filter((m) => m.category === "GR");
  const grSportModels = models.filter((m) => m.category === "GR Sport");

  const inputClass =
    "w-full border border-gray-200 rounded-lg px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent bg-white";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <div className="p-8">
      <h2 className="text-xl font-bold text-gray-900 mb-6 pb-4 border-b border-gray-100">
        ข้อมูลติดต่อ
      </h2>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className={labelClass}>
              ชื่อ-นามสกุล <span className="text-red-500">*</span>
            </label>
            <input
              required
              value={form.full_name}
              onChange={set("full_name")}
              className={inputClass}
              placeholder="กรอกชื่อ-นามสกุล"
            />
          </div>
          <div>
            <label className={labelClass}>
              เบอร์โทรศัพท์ <span className="text-red-500">*</span>
            </label>
            <input
              required
              type="tel"
              value={form.phone}
              onChange={set("phone")}
              className={inputClass}
              placeholder="0XX-XXX-XXXX"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className={labelClass}>อีเมล</label>
            <input
              type="email"
              value={form.email}
              onChange={set("email")}
              className={inputClass}
              placeholder="example@email.com"
            />
          </div>
          <div>
            <label className={labelClass}>LINE ID</label>
            <input
              value={form.line_id}
              onChange={set("line_id")}
              className={inputClass}
              placeholder="@lineid"
            />
          </div>
        </div>

        <div>
          <label className={labelClass}>
            รุ่นรถที่สนใจ <span className="text-red-500">*</span>
          </label>
          <select required value={form.interested_model_id} onChange={set("interested_model_id")} className={inputClass}>
            <option value="">-- เลือกรุ่นรถ --</option>
            {grModels.length > 0 && (
              <optgroup label="GR Performance">
                {grModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                    {m.price_from
                      ? ` (ราคาเริ่ม ${m.price_from.toLocaleString()} บาท)`
                      : ""}
                  </option>
                ))}
              </optgroup>
            )}
            {grSportModels.length > 0 && (
              <optgroup label="GR Sport">
                {grSportModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                    {m.price_from
                      ? ` (ราคาเริ่ม ${m.price_from.toLocaleString()} บาท)`
                      : ""}
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className={labelClass}>งบประมาณ</label>
            <select value={form.budget_range} onChange={set("budget_range")} className={inputClass}>
              <option value="">-- เลือกงบประมาณ --</option>
              {BUDGET_RANGES.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>ระยะเวลาที่ต้องการซื้อ</label>
            <select value={form.purchase_timeline} onChange={set("purchase_timeline")} className={inputClass}>
              <option value="">-- เลือกระยะเวลา --</option>
              {TIMELINES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className={labelClass}>จังหวัด</label>
          <select value={form.province} onChange={set("province")} className={inputClass}>
            <option value="">-- เลือกจังหวัด --</option>
            {PROVINCES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelClass}>หมายเหตุ / ข้อมูลเพิ่มเติม</label>
          <textarea
            value={form.notes}
            onChange={set("notes")}
            rows={3}
            className={inputClass}
            placeholder="เช่น ต้องการสีเฉพาะ, มีคำถามเพิ่มเติม..."
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-[#eb0a1e] text-white py-4 rounded-full font-semibold text-lg hover:bg-red-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {submitting ? "กำลังส่งข้อมูล..." : "ลงทะเบียนความสนใจ"}
        </button>

        <p className="text-center text-xs text-gray-400">
          ข้อมูลของคุณจะถูกเก็บไว้อย่างปลอดภัยและใช้เพื่อติดต่อกลับเท่านั้น
        </p>
      </form>
    </div>
  );
}
