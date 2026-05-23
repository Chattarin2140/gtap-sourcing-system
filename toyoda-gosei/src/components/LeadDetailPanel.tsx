"use client";

import { useState } from "react";
import { Lead, LeadStatus, STATUS_LABELS, STATUS_COLORS } from "@/lib/supabase";

const PIPELINE: LeadStatus[] = ["new", "contacted", "test_drive", "negotiating", "sold", "lost"];

type Props = {
  lead: Lead;
  onClose: () => void;
  onUpdated: (updated: Lead) => void;
};

export default function LeadDetailPanel({ lead, onClose, onUpdated }: Props) {
  const [saving, setSaving] = useState(false);
  const [notes, setNotes] = useState(lead.notes ?? "");
  const [assignedTo, setAssignedTo] = useState(lead.assigned_to ?? "");

  const updateStatus = async (newStatus: LeadStatus) => {
    setSaving(true);
    const res = await fetch("/api/leads", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: lead.id, status: newStatus, assigned_to: assignedTo, notes }),
    });
    const json = await res.json();
    setSaving(false);
    if (json.lead) onUpdated(json.lead);
  };

  const saveDetails = async () => {
    setSaving(true);
    const res = await fetch("/api/leads", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: lead.id, status: lead.status, assigned_to: assignedTo, notes }),
    });
    const json = await res.json();
    setSaving(false);
    if (json.lead) onUpdated(json.lead);
  };

  return (
    <>
      <div
        className="fixed inset-0 bg-black/30 z-40"
        onClick={onClose}
      />
      <aside className="fixed right-0 top-0 h-full w-full max-w-md bg-white z-50 shadow-2xl flex flex-col overflow-hidden">
        <div className="bg-[#1a1a1a] text-white p-5 flex items-start justify-between shrink-0">
          <div>
            <h2 className="font-bold text-lg">{lead.full_name}</h2>
            <p className="text-gray-400 text-sm mt-0.5">{lead.interested_model_name ?? "ไม่ระบุรุ่น"}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors text-2xl leading-none mt-0.5"
          >
            &times;
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">ข้อมูลติดต่อ</h3>
            <div className="space-y-2">
              <InfoRow label="เบอร์โทร" value={lead.phone} copyable />
              {lead.email && <InfoRow label="อีเมล" value={lead.email} copyable />}
              {lead.line_id && <InfoRow label="LINE ID" value={lead.line_id} copyable />}
              {lead.province && <InfoRow label="จังหวัด" value={lead.province} />}
            </div>
          </section>

          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">ความสนใจ</h3>
            <div className="space-y-2">
              {lead.interested_model_name && (
                <InfoRow label="รุ่นรถ" value={lead.interested_model_name} />
              )}
              {lead.budget_range && <InfoRow label="งบประมาณ" value={lead.budget_range} />}
              {lead.purchase_timeline && <InfoRow label="ระยะเวลา" value={lead.purchase_timeline} />}
              <InfoRow label="ที่มา" value={lead.source} />
            </div>
          </section>

          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Pipeline</h3>
            <div className="flex flex-wrap gap-2">
              {PIPELINE.map((s) => (
                <button
                  key={s}
                  onClick={() => updateStatus(s)}
                  disabled={saving}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border-2 transition-all disabled:opacity-50 ${
                    lead.status === s
                      ? "border-[#eb0a1e] " + STATUS_COLORS[s]
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  {STATUS_LABELS[s]}
                </button>
              ))}
            </div>
            <div className="mt-2">
              <span className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold ${STATUS_COLORS[lead.status as LeadStatus]}`}>
                สถานะปัจจุบัน: {STATUS_LABELS[lead.status as LeadStatus]}
              </span>
            </div>
          </section>

          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">จัดการ</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">มอบหมายให้</label>
                <input
                  value={assignedTo}
                  onChange={(e) => setAssignedTo(e.target.value)}
                  placeholder="ชื่อพนักงาน"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">หมายเหตุ</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={4}
                  placeholder="บันทึกการติดต่อ, รายละเอียดเพิ่มเติม..."
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 resize-none"
                />
              </div>
              <button
                onClick={saveDetails}
                disabled={saving}
                className="w-full bg-[#eb0a1e] text-white py-2.5 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {saving ? "กำลังบันทึก..." : "บันทึก"}
              </button>
            </div>
          </section>

          <div className="text-xs text-gray-300 pb-2">
            <div>ลงทะเบียน: {new Date(lead.created_at).toLocaleString("th-TH")}</div>
            <div>อัปเดตล่าสุด: {new Date(lead.updated_at).toLocaleString("th-TH")}</div>
          </div>
        </div>
      </aside>
    </>
  );
}

function InfoRow({ label, value, copyable }: { label: string; value: string; copyable?: boolean }) {
  const copy = () => navigator.clipboard.writeText(value);
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-gray-50">
      <span className="text-xs text-gray-500 w-20 shrink-0">{label}</span>
      <span className="text-sm text-gray-800 flex-1 text-right">{value}</span>
      {copyable && (
        <button
          onClick={copy}
          className="ml-2 text-gray-300 hover:text-gray-500 transition-colors shrink-0"
          title="คัดลอก"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </button>
      )}
    </div>
  );
}
