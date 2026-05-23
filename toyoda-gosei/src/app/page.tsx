import BuyerRegistrationForm from "@/components/BuyerRegistrationForm";

const GR_HIGHLIGHTS = [
  { model: "GR86", power: "234 PS", tag: "Rear-Wheel Drive" },
  { model: "GR Yaris", power: "272 PS", tag: "GR-Four AWD" },
  { model: "GR Supra", power: "387 PS", tag: "6-Cylinder Inline" },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white">
      <header className="border-b border-white/10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <div className="w-9 h-9 bg-[#eb0a1e] rounded-full flex items-center justify-center shrink-0">
            <span className="text-white font-black text-xs">GR</span>
          </div>
          <div>
            <div className="font-bold text-base leading-tight tracking-wide">toyoda-gosei Racing</div>
            <div className="text-[10px] text-red-400 tracking-widest uppercase">Thailand</div>
          </div>
        </div>
      </header>

      <section className="relative overflow-hidden py-20 px-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(235,10,30,0.15),_transparent_60%)]" />
        <div className="max-w-6xl mx-auto relative">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 bg-[#eb0a1e]/10 border border-[#eb0a1e]/30 rounded-full px-4 py-1.5 text-xs text-red-400 font-medium mb-6">
              <span className="w-1.5 h-1.5 bg-[#eb0a1e] rounded-full animate-pulse"></span>
              toyoda-gosei Racing Lineup 2025
            </div>
            <h1 className="text-5xl font-black leading-tight mb-4 tracking-tight">
              ขับเคลื่อน<br />
              <span className="text-[#eb0a1e]">ความตื่นเต้น</span>
            </h1>
            <p className="text-gray-400 text-lg leading-relaxed mb-8">
              ลงทะเบียนความสนใจ รับข้อมูลและข้อเสนอพิเศษ
              จากทีมผู้เชี่ยวชาญรถยนต์ Toyota GR โดยตรง
            </p>
            <div className="flex flex-wrap gap-4">
              {GR_HIGHLIGHTS.map((g) => (
                <div key={g.model} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3">
                  <div className="font-bold">{g.model}</div>
                  <div className="text-[#eb0a1e] text-sm font-semibold">{g.power}</div>
                  <div className="text-gray-500 text-xs">{g.tag}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 pb-20">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold">ลงทะเบียนความสนใจ</h2>
            <p className="text-gray-500 text-sm mt-2">
              กรอกข้อมูล ทีมงานจะติดต่อกลับภายใน 24 ชั่วโมง
            </p>
          </div>
          <div className="bg-white rounded-2xl shadow-2xl">
            <BuyerRegistrationForm />
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 py-8 px-6 text-center text-gray-600 text-sm">
        <p>Toyoda-gosei Racing Thailand &copy; {new Date().getFullYear()}</p>
        <div className="mt-2 flex justify-center gap-4">
          <a href="/dashboard" className="hover:text-gray-400 transition-colors">
            Admin
          </a>
        </div>
      </footer>
    </div>
  );
}
