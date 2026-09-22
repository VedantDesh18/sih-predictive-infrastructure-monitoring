import Link from "next/link";
import { ReactNode } from "react";

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f5f7f9] text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex min-h-[76px] max-w-[1540px] items-center justify-between gap-5 px-5 py-3 md:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center border-2 border-[#008fc4] bg-white text-lg font-black text-[#173b5d]">
              P
            </div>
            <div>
              <p className="text-base font-bold tracking-[0.16em] text-[#173b5d]">
                PAIMANA
              </p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">
                Infrastructure Risk Intelligence
              </p>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            <div className="hidden border-r border-slate-200 pr-4 text-right sm:block">
              <p className="text-[10px] font-bold uppercase tracking-[0.09em] text-slate-500">
                Public infrastructure monitoring
              </p>
              <p className="mt-0.5 text-xs font-semibold text-[#173b5d]">
                Decision-support dashboard
              </p>
            </div>
            <a
              href="#portfolio-table"
              className="secondary-button hidden sm:inline-flex"
            >
              Project register
            </a>
          </div>
        </div>
      </header>
      <nav className="sticky top-0 z-20 border-b border-[#0078aa] bg-[#008fc4] shadow-sm">
        <div className="mx-auto flex max-w-[1540px] overflow-x-auto px-3 md:px-5">
          <Link href="/" className="nav-link nav-link-active">
            <span>▦</span>Portfolio overview
          </Link>
          <a href="#portfolio-table" className="nav-link">
            <span>▤</span>Project risk register
          </a>
          <a href="#risk-lens" className="nav-link">
            <span>◌</span>Risk trajectory
          </a>
          <a href="#portfolio-table" className="nav-link">
            <span>▲</span>Early warnings
          </a>
        </div>
      </nav>
      <main className="mx-auto max-w-[1540px]">{children}</main>
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
    LOW: "border-emerald-200 bg-emerald-50 text-emerald-700",
    MEDIUM: "border-amber-200 bg-amber-50 text-amber-800",
    HIGH: "border-orange-200 bg-orange-50 text-orange-800",
    CRITICAL: "border-rose-200 bg-rose-50 text-rose-800",
    STABLE: "border-slate-200 bg-slate-50 text-slate-700",
    IMPROVING: "border-emerald-200 bg-emerald-50 text-emerald-700",
    WORSENING: "border-orange-200 bg-orange-50 text-orange-800",
    "RAPIDLY WORSENING": "border-rose-200 bg-rose-50 text-rose-800",
  };
  return (
    <span
      className={`inline-flex items-center rounded border font-bold tracking-wide ${compact ? "px-2 py-1 text-[10px]" : "px-2.5 py-1 text-[11px]"} ${colors[value] ?? colors.STABLE}`}
    >
      {value}
    </span>
  );
}

export function formatCrore(value: number) {
  return `₹${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value)} Cr`;
}
