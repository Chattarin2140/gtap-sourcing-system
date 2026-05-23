"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Leads" },
  { href: "/admin/models", label: "รุ่นรถ" },
];

export default function AdminNav() {
  const pathname = usePathname();

  return (
    <header className="bg-[#1a1a1a] text-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-6">
        <Link href="/dashboard" className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 bg-[#eb0a1e] rounded-full flex items-center justify-center">
            <span className="text-white font-black text-xs">GR</span>
          </div>
          <span className="font-bold text-sm hidden sm:block">Toyota Gazoo Thailand</span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  active
                    ? "bg-[#eb0a1e] text-white"
                    : "text-gray-300 hover:text-white hover:bg-white/10"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto">
          <Link
            href="/"
            className="text-gray-400 hover:text-white text-sm transition-colors"
          >
            ดูหน้าลงทะเบียน
          </Link>
        </div>
      </div>
    </header>
  );
}
