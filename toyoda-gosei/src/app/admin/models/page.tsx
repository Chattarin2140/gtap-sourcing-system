"use client";

import { useState, useEffect, useCallback } from "react";
import { CarModel } from "@/lib/supabase";

const CATEGORIES = ["GR", "GR Sport", "Standard"];

export default function ModelsPage() {
  const [models, setModels] = useState<CarModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    category: "GR Sport",
    price_from: "",
    price_to: "",
  });

  const fetchModels = useCallback(async () => {
    setLoading(true);
    const res = await fetch("/api/models");
    const json = await res.json();
    setModels(json.models ?? []);
    setLoading(false);
  }, []);

  useEffect(() => { fetchModels(); }, [fetchModels]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    await fetch("/api/models", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: form.name,
        category: form.category,
        price_from: form.price_from ? parseInt(form.price_from.replace(/,/g, "")) : null,
        price_to: form.price_to ? parseInt(form.price_to.replace(/,/g, "")) : null,
      }),
    });
    setSaving(false);
    setForm({ name: "", category: "GR Sport", price_from: "", price_to: "" });
    setShowForm(false);
    fetchModels();
  };

  const toggleActive = async (model: CarModel) => {
    await fetch("/api/models", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: model.id, is_active: !model.is_active }),
    });
    fetchModels();
  };

  const grModels = models.filter((m) => m.category === "GR");
  const grSportModels = models.filter((m) => m.category === "GR Sport");
  const otherModels = models.filter((m) => m.category !== "GR" && m.category !== "GR Sport");

  return (
    <>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">จัดการรุ่นรถ</h1>
          <p className="text-gray-500 text-sm mt-1">รุ่นรถที่จะปรากฎในฟอร์มลงทะเบียน</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="bg-[#eb0a1e] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
        >
          + เพิ่มรุ่นรถ
        </button>
      </div>

      {loading ? (
        <div className="text-center py-16 text-gray-400">กำลังโหลด...</div>
      ) : (
        <div className="space-y-6">
          {[
            { label: "GR Performance", items: grModels },
            { label: "GR Sport", items: grSportModels },
            { label: "Standard", items: otherModels },
          ]
            .filter((g) => g.items.length > 0)
            .map((group) => (
              <div key={group.label} className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 bg-gray-50">
                  <h3 className="font-semibold text-gray-700 text-sm">{group.label}</h3>
                </div>
                <div className="divide-y divide-gray-50">
                  {group.items.map((model) => (
                    <div key={model.id} className={`flex items-center px-5 py-4 gap-4 ${!model.is_active ? "opacity-50" : ""}`}>
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">{model.name}</div>
                        {model.price_from && (
                          <div className="text-sm text-gray-500 mt-0.5">
                            ราคา {model.price_from.toLocaleString()}
                            {model.price_to ? ` - ${model.price_to.toLocaleString()}` : "+"} บาท
                          </div>
                        )}
                      </div>
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                        model.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                      }`}>
                        {model.is_active ? "แสดงอยู่" : "ซ่อน"}
                      </span>
                      <button
                        onClick={() => toggleActive(model)}
                        className="text-sm text-gray-400 hover:text-gray-700 transition-colors"
                      >
                        {model.is_active ? "ซ่อน" : "แสดง"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
            <h3 className="font-bold text-lg mb-5">เพิ่มรุ่นรถใหม่</h3>
            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ชื่อรุ่น <span className="text-red-500">*</span>
                </label>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="เช่น Corolla GR Sport"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">หมวดหมู่</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">ราคาเริ่มต้น (บาท)</label>
                  <input
                    type="number"
                    value={form.price_from}
                    onChange={(e) => setForm((f) => ({ ...f, price_from: e.target.value }))}
                    placeholder="1,500,000"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">ราคาสูงสุด (บาท)</label>
                  <input
                    type="number"
                    value={form.price_to}
                    onChange={(e) => setForm((f) => ({ ...f, price_to: e.target.value }))}
                    placeholder="2,000,000"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                  />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 bg-[#eb0a1e] text-white py-2.5 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {saving ? "กำลังบันทึก..." : "เพิ่มรุ่นรถ"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
