"use client";

import { useState, useEffect, useCallback } from "react";
import { Lead, LeadStatus, STATUS_LABELS, STATUS_COLORS } from "@/lib/supabase";
import LeadDetailPanel from "@/components/LeadDetailPanel";

const STATUSES: { value: string; label: string }[] = [
  { value: "all", label: "ทั้งหมด" },
  { value: "new", label: "ลูกค้าใหม่" },
  { value: "contacted", label: "ติดต่อแล้ว" },
  { value: "test_drive", label: "Test Drive" },
  { value: "negotiating", label: "เจรจา" },
  { value: "sold", label: "ปิดดีล" },
  { value: "lost", label: "เสียลูกค้า" },
];

type Stats = {
  total: number;
  by_status: Record<string, number>;
  by_model: { name: string; count: number }[];
};

export default function DashboardPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<Stats | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams({ page: String(page) });
    if (statusFilter !== "all") params.set("status", statusFilter);
    if (search) params.set("search", search);
    const res = await fetch(`/api/leads?${params}`);
    const json = await res.json();
    setLeads(json.leads ?? []);
    setTotal(json.total ?? 0);
    setLoading(false);
  }, [page, statusFilter, search]);

  const fetchStats = useCallback(async () => {
    const res = await fetch("/api/leads?page=1");
    const json = await res.json();
    const all: Lead[] = json.leads ?? [];
    const by_status: Record<string, number> = {};
    const by_model: Record<string, number> = {};
    all.forEach((l) => {
      by_status[l.status] = (by_status[l.status] ?? 0) + 1;
      const name = l.interested_model_name ?? "ไม่ระบุ";
      by_model[name] = (by_model[name] ?? 0) + 1;
    });
    setStats({
      total: json.total ?? 0,
      by_status,
      by_model: Object.entries(by_model)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5),
    });
  }, []);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);
  useEffect(() => { fetchStats(); }, [fetchStats]);

  const handleLeadUpdated = (updated: Lead) => {
    setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    fetchStats();
    setSelectedLead(updated);
  };

  const exportCSV = () => {
    const params = new URLSearchParams();
    if (statusFilter !== "all") params.set("status", statusFilter);
    window.location.href = `/api/leads/export?${params}`;
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Leads Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">ติดตามและจัดการผู้ที่สนใจซื้อรถ Toyota GR</p>
      </div>

      {stats && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatCard label="Leads ทั้งหมด" value={stats.total} color="bg-gray-900" />
            <StatCard label="ปิดดีล" value={stats.by_status["sold"] ?? 0} color="bg-emerald-600" />
            <StatCard label="กำลังเจรจา" value={stats.by_status["negotiating"] ?? 0} color="bg-orange-500" />
            <StatCard label="ลูกค้าใหม่" value={stats.by_status["new"] ?? 0} color="bg-blue-600" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <PipelineBar stats={stats} />
            {stats.by_model.length > 0 && <TopModels models={stats.by_model} />}
          </div>
        </>
      )}

      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex flex-wrap gap-3 items-center">
          <div className="flex gap-1.5 flex-wrap">
            {STATUSES.map((s) => (
              <button
                key={s.value}
                onClick={() => { setStatusFilter(s.value); setPage(1); }}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  statusFilter === s.value
                    ? "bg-[#eb0a1e] text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {s.label}
                {s.value !== "all" && stats?.by_status[s.value]
                  ? ` (${stats.by_status[s.value]})`
                  : ""}
              </button>
            ))}
          </div>
          <div className="ml-auto flex gap-2">
            <input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="ค้นหาชื่อ / เบอร์"
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-44 focus:outline-none focus:ring-2 focus:ring-red-400"
            />
            <button
              onClick={exportCSV}
              className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors whitespace-nowrap"
            >
              Export CSV
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-16 text-center text-gray-400">กำลังโหลด...</div>
        ) : leads.length === 0 ? (
          <div className="p-16 text-center text-gray-400">ไม่พบข้อมูล</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  {["ชื่อ-เบอร์", "รุ่นที่สนใจ", "งบ", "จังหวัด", "สถานะ", "วันที่"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-gray-500 font-medium text-xs uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr
                    key={lead.id}
                    onClick={() => setSelectedLead(lead)}
                    className={`border-b border-gray-50 hover:bg-red-50 cursor-pointer transition-colors ${
                      selectedLead?.id === lead.id ? "bg-red-50" : ""
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{lead.full_name}</div>
                      <div className="text-gray-400 text-xs">{lead.phone}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{lead.interested_model_name ?? "-"}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{lead.budget_range?.replace(" บาท", "")?.replace(",000,000", "M") ?? "-"}</td>
                    <td className="px-4 py-3 text-gray-600">{lead.province ?? "-"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[lead.status as LeadStatus]}`}>
                        {STATUS_LABELS[lead.status as LeadStatus]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                      {new Date(lead.created_at).toLocaleDateString("th-TH", { day: "numeric", month: "short" })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="p-4 border-t border-gray-100 flex items-center justify-between">
            <span className="text-sm text-gray-500">{total} รายการ / หน้า {page}/{totalPages}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50"
              >
                ก่อนหน้า
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50"
              >
                ถัดไป
              </button>
            </div>
          </div>
        )}
      </div>

      {selectedLead && (
        <LeadDetailPanel
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
          onUpdated={handleLeadUpdated}
        />
      )}
    </>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`${color} text-white rounded-xl p-5`}>
      <div className="text-4xl font-bold tabular-nums">{value.toLocaleString()}</div>
      <div className="text-sm opacity-75 mt-1">{label}</div>
    </div>
  );
}

function PipelineBar({ stats }: { stats: Stats }) {
  const order: LeadStatus[] = ["new", "contacted", "test_drive", "negotiating", "sold", "lost"];
  const colorMap: Record<LeadStatus, string> = {
    new: "bg-blue-500",
    contacted: "bg-yellow-400",
    test_drive: "bg-purple-500",
    negotiating: "bg-orange-500",
    sold: "bg-emerald-500",
    lost: "bg-red-400",
  };
  const maxVal = Math.max(...order.map((s) => stats.by_status[s] ?? 0), 1);

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5">
      <h3 className="font-semibold text-gray-700 text-sm mb-4">Pipeline ภาพรวม</h3>
      <div className="space-y-2.5">
        {order.map((s) => {
          const val = stats.by_status[s] ?? 0;
          const pct = Math.round((val / maxVal) * 100);
          return (
            <div key={s} className="flex items-center gap-3">
              <span className="text-xs text-gray-500 w-24 shrink-0">{STATUS_LABELS[s]}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full rounded-full ${colorMap[s]} transition-all`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs font-medium text-gray-700 w-4 text-right">{val}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TopModels({ models }: { models: { name: string; count: number }[] }) {
  const max = Math.max(...models.map((m) => m.count), 1);
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5">
      <h3 className="font-semibold text-gray-700 text-sm mb-4">รุ่นที่สนใจมากสุด</h3>
      <div className="space-y-2.5">
        {models.map((m, i) => (
          <div key={m.name} className="flex items-center gap-3">
            <span className="text-xs text-gray-400 w-4 shrink-0">#{i + 1}</span>
            <span className="text-xs text-gray-700 w-36 shrink-0 truncate">{m.name}</span>
            <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="h-full rounded-full bg-[#eb0a1e] transition-all"
                style={{ width: `${Math.round((m.count / max) * 100)}%` }}
              />
            </div>
            <span className="text-xs font-medium text-gray-700 w-4 text-right">{m.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
