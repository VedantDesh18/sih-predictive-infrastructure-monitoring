import Link from "next/link";
import { ReactNode } from "react";

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#07111f] text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-[255px] border-r border-slate-700/50 bg-[#091827] px-5 py-6 lg:flex lg:flex-col">
        <Link href="/" className="mb-12 flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-400 text-lg font-black text-[#07111f] shadow-[0_0_25px_rgba(34,211,238,.25)]">
            P
          </div>
          <div>
            <p className="text-sm font-bold tracking-[0.22em] text-cyan-300">
              PAIMANA
            </p>
            <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
              Risk Intelligence
            </p>
          </div>
        </Link>
        <nav className="space-y-2 text-sm">
          <Link href="/" className="nav-link nav-link-active">
            <span>▦</span>Portfolio Command
          </Link>
          <a href="#portfolio-table" className="nav-link">
            <span>▤</span>Project Risk Register
          </a>
          <a href="#risk-lens" className="nav-link">
            <span>◌</span>Risk Trajectory
          </a>
          <a href="#portfolio-table" className="nav-link">
            <span>▲</span>Early Warnings
          </a>
        </nav>
        <div className="mt-auto rounded-xl border border-cyan-400/15 bg-cyan-400/5 p-4">
          <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.14em] text-cyan-300">
            Decision-support prototype
          </p>
          <p className="text-xs leading-5 text-slate-400">
            Transparent calculated risk indicators. Ready for a future model
            replacement.
          </p>
        </div>
      </aside>
      <main className="lg:pl-[255px]">{children}</main>
    </div>
  );
}

export function RiskBadge({
  value,
  compact = false,
}: {
  value: string;
  compact?: boolean;
}) {
  const colors: Record<string, string> = {
    LOW: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
    MEDIUM: "border-amber-400/25 bg-amber-400/10 text-amber-200",
    HIGH: "border-orange-400/30 bg-orange-400/10 text-orange-300",
    CRITICAL: "border-rose-400/30 bg-rose-400/10 text-rose-300",
    STABLE: "border-slate-400/25 bg-slate-400/10 text-slate-300",
    IMPROVING: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
    WORSENING: "border-orange-400/30 bg-orange-400/10 text-orange-300",
    "RAPIDLY WORSENING": "border-rose-400/30 bg-rose-400/10 text-rose-300",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md border font-bold tracking-wide ${compact ? "px-2 py-1 text-[10px]" : "px-2.5 py-1 text-[11px]"} ${colors[value] ?? colors.STABLE}`}
    >
      {value}
    </span>
  );
}

export function formatCrore(value: number) {
  return `₹${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value)} Cr`;
}
