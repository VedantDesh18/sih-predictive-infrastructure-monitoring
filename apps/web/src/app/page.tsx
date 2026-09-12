"use client";

import type { EChartsOption } from "echarts";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  DashboardShell,
  formatCrore,
  RiskBadge,
} from "@/components/dashboard-shell";
import { EChart } from "@/components/echart";
import type { Portfolio, Project, Statistics } from "@/lib/types";

const riskPalette: Record<string, string> = {
  LOW: "#34d399",
  MEDIUM: "#fbbf24",
  HIGH: "#fb923c",
  CRITICAL: "#fb7185",
};

async function api<T>(path: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load monitoring data");
  return response.json();
}

function StatCard({
  label,
  value,
  detail,
  tone = "cyan",
}: {
  label: string;
  value: string | number;
  detail: string;
  tone?: "cyan" | "rose" | "amber" | "emerald";
}) {
  const toneClass = {
    cyan: "text-cyan-300",
    rose: "text-rose-300",
    amber: "text-amber-200",
    emerald: "text-emerald-300",
  }[tone];
  return (
    <article className="panel-card relative overflow-hidden p-5">
      <div
        className={`absolute left-0 top-0 h-1 w-full ${tone === "rose" ? "bg-rose-400" : tone === "amber" ? "bg-amber-400" : tone === "emerald" ? "bg-emerald-400" : "bg-cyan-400"}`}
      />
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">
        {label}
      </p>
      <p className={`mt-3 text-2xl font-semibold tracking-tight ${toneClass}`}>
        {value}
      </p>
      <p className="mt-2 text-xs text-slate-500">{detail}</p>
    </article>
  );
}

export default function Home() {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState(false);
  const [ministry, setMinistry] = useState("ALL");
  const [sector, setSector] = useState("ALL");
  const [level, setLevel] = useState("ALL");
  const [trend, setTrend] = useState("ALL");

  useEffect(() => {
    Promise.all([
      api<Statistics>("/statistics"),
      api<Portfolio>("/risk/portfolio"),
      api<{ projects: Project[] }>("/projects"),
    ])
      .then(([stats, portfolioData, projectData]) => {
        setStatistics(stats);
        setPortfolio(portfolioData);
        setProjects(projectData.projects);
      })
      .catch(() => setError(true));
  }, []);

  const ministries = useMemo(
    () => [...new Set(projects.map((project) => project.ministry))],
    [projects]
  );
  const sectors = useMemo(
    () => [...new Set(projects.map((project) => project.sector))],
    [projects]
  );
  const filteredProjects = useMemo(
    () =>
      projects.filter(
        (project) =>
          (ministry === "ALL" || project.ministry === ministry) &&
          (sector === "ALL" || project.sector === sector) &&
          (level === "ALL" || project.risk.scores.risk_level === level) &&
          (trend === "ALL" || project.risk.trajectory.trend === trend)
      ),
    [projects, ministry, sector, level, trend]
  );

  const distributionOption: EChartsOption = useMemo(
    () => ({
      tooltip: {
        trigger: "item",
        backgroundColor: "#12243a",
        textStyle: { color: "#e2e8f0" },
      },
      legend: {
        bottom: 0,
        textStyle: { color: "#94a3b8", fontSize: 10 },
        itemWidth: 9,
        itemHeight: 9,
      },
      series: [
        {
          type: "pie",
          radius: ["56%", "78%"],
          center: ["50%", "43%"],
          label: { show: false },
          itemStyle: {
            borderColor: "#0b1828",
            borderWidth: 4,
            borderRadius: 4,
          },
          data: (portfolio?.risk_distribution ?? []).map((item) => ({
            name: item.level,
            value: item.count,
            itemStyle: { color: riskPalette[item.level] },
          })),
        },
      ],
    }),
    [portfolio]
  );
  const trendOption: EChartsOption = useMemo(
    () => ({
      grid: { left: 38, right: 14, top: 22, bottom: 28 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#12243a",
        textStyle: { color: "#e2e8f0" },
      },
      xAxis: {
        type: "category",
        data: portfolio?.portfolio_trend.map((point) => point.month) ?? [],
        axisLine: { lineStyle: { color: "#25415e" } },
        axisLabel: { color: "#94a3b8" },
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: "#1a3049" } },
        axisLabel: { color: "#94a3b8" },
      },
      series: [
        {
          type: "line",
          smooth: true,
          data: portfolio?.portfolio_trend.map((point) => point.risk) ?? [],
          symbolSize: 7,
          lineStyle: { color: "#22d3ee", width: 3 },
          itemStyle: { color: "#67e8f9" },
          areaStyle: { color: "rgba(34,211,238,.11)" },
        },
      ],
    }),
    [portfolio]
  );
  const ministryOption: EChartsOption = useMemo(
    () => ({
      grid: { left: 130, right: 18, top: 10, bottom: 15 },
      xAxis: {
        type: "value",
        max: 100,
        splitLine: { lineStyle: { color: "#1a3049" } },
        axisLabel: { color: "#94a3b8" },
      },
      yAxis: {
        type: "category",
        data:
          portfolio?.ministry_comparison.map((item) =>
            item.name.replace("Ministry of ", "")
          ) ?? [],
        axisLabel: {
          color: "#cbd5e1",
          fontSize: 10,
          width: 118,
          overflow: "truncate",
        },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [
        {
          type: "bar",
          data:
            portfolio?.ministry_comparison.map((item) => ({
              value: item.risk,
              itemStyle: {
                color:
                  item.risk >= 80
                    ? "#fb7185"
                    : item.risk >= 65
                      ? "#fb923c"
                      : "#22d3ee",
                borderRadius: [0, 4, 4, 0],
              },
            })) ?? [],
          barWidth: 13,
          label: {
            show: true,
            position: "right",
            color: "#94a3b8",
            fontSize: 10,
          },
        },
      ],
    }),
    [portfolio]
  );
  const sectorOption: EChartsOption = useMemo(
    () => ({
      grid: { left: 28, right: 8, top: 18, bottom: 52 },
      xAxis: {
        type: "category",
        data: portfolio?.sector_comparison.map((item) => item.name) ?? [],
        axisLabel: { color: "#94a3b8", fontSize: 9, rotate: 28 },
        axisLine: { lineStyle: { color: "#25415e" } },
      },
      yAxis: {
        type: "value",
        max: 100,
        splitLine: { lineStyle: { color: "#1a3049" } },
        axisLabel: { color: "#94a3b8" },
      },
      series: [
        {
          type: "bar",
          data: portfolio?.sector_comparison.map((item) => item.risk) ?? [],
          barWidth: "48%",
          itemStyle: { color: "#818cf8", borderRadius: [4, 4, 0, 0] },
        },
      ],
    }),
    [portfolio]
  );

  if (error)
    return (
      <DashboardShell>
        <div className="m-8 panel-card p-8 text-rose-300">
          The monitoring API could not be reached. Start the FastAPI service and
          refresh this dashboard.
        </div>
      </DashboardShell>
    );
  if (!statistics || !portfolio)
    return (
      <DashboardShell>
        <div className="grid min-h-screen place-items-center text-sm tracking-wide text-cyan-300">
          INITIALISING PORTFOLIO INTELLIGENCE…
        </div>
      </DashboardShell>
    );

  return (
    <DashboardShell>
      <header className="flex flex-col gap-4 border-b border-slate-700/50 bg-[#091827]/80 px-5 py-5 backdrop-blur md:flex-row md:items-center md:justify-between md:px-8">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-300">
            Infrastructure Command Center
          </p>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-white">
            Portfolio Risk Intelligence
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full border border-amber-300/25 bg-amber-300/10 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-amber-200">
            Synthetic Demonstration Data
          </span>
          <span className="hidden text-xs text-slate-500 sm:inline">
            Updated Jul 2026 · Prototype
          </span>
        </div>
      </header>
      <section className="px-5 py-6 md:px-8">
        <div className="mb-6 flex flex-col justify-between gap-3 xl:flex-row xl:items-end">
          <div>
            <h2 className="text-2xl font-semibold text-white">
              Early warning, before project failure
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">
              A transparent predictive-risk prototype that identifies worsening
              project trajectories and exposes the operational drivers behind
              each warning.
            </p>
          </div>
          <Link href="/projects/SYN-DEMO-001" className="action-button">
            Open primary demo project <span>→</span>
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          <StatCard
            label="Total projects"
            value={statistics.total_projects}
            detail="Synthetic portfolio"
          />
          <StatCard
            label="High risk"
            value={statistics.high_risk_projects}
            detail="Requires attention"
            tone="amber"
          />
          <StatCard
            label="Critical"
            value={statistics.critical_projects}
            detail="Immediate review"
            tone="rose"
          />
          <StatCard
            label="Rising risk"
            value={statistics.rising_risk_projects}
            detail="Worsening trajectory"
            tone="rose"
          />
          <StatCard
            label="Approved cost"
            value={formatCrore(statistics.total_approved_cost)}
            detail="Portfolio baseline"
            tone="emerald"
          />
          <StatCard
            label="Potential exposure"
            value={formatCrore(statistics.potential_cost_exposure)}
            detail="Calculated overrun exposure"
            tone="amber"
          />
        </div>
      </section>
      <section
        id="risk-lens"
        className="grid gap-5 px-5 pb-6 md:px-8 xl:grid-cols-12"
      >
        <article className="panel-card p-5 xl:col-span-3">
          <div className="mb-1 flex items-center justify-between">
            <h3 className="section-title">Risk distribution</h3>
            <span className="text-xs text-slate-500">Projects</span>
          </div>
          <EChart option={distributionOption} className="h-[245px] w-full" />
        </article>
        <article className="panel-card p-5 xl:col-span-5">
          <div className="mb-1 flex items-center justify-between">
            <div>
              <h3 className="section-title">Portfolio risk trajectory</h3>
              <p className="mt-1 text-xs text-slate-500">
                Average calculated risk across reporting periods
              </p>
            </div>
            <span className="pulse-dot">LIVE MODEL INPUT</span>
          </div>
          <EChart option={trendOption} className="h-[245px] w-full" />
        </article>
        <article className="panel-card p-5 xl:col-span-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="section-title">Top intervention queue</h3>
            <span className="text-xs text-slate-500">Top 10</span>
          </div>
          <div className="space-y-1">
            {portfolio.top_risky_projects.slice(0, 5).map((project, index) => (
              <Link
                href={`/projects/${project.project_id}`}
                key={project.project_id}
                className="group flex items-center gap-3 rounded-lg px-2 py-2.5 transition hover:bg-white/[.035]"
              >
                <span className="w-4 text-xs text-slate-600">0{index + 1}</span>
                <span className="min-w-0 flex-1 truncate text-xs font-medium text-slate-200 group-hover:text-cyan-200">
                  {project.project_name}
                </span>
                <span className="text-sm font-semibold text-rose-300">
                  {project.overall_risk}
                </span>
                <span className="text-slate-600">›</span>
              </Link>
            ))}
          </div>
          <Link
            href="#portfolio-table"
            className="mt-3 block border-t border-slate-700/50 pt-3 text-center text-xs font-semibold text-cyan-300"
          >
            View risk register →
          </Link>
        </article>
        <article className="panel-card p-5 xl:col-span-7">
          <h3 className="section-title">Ministry risk comparison</h3>
          <EChart option={ministryOption} className="mt-1 h-[275px] w-full" />
        </article>
        <article className="panel-card p-5 xl:col-span-5">
          <h3 className="section-title">Sector risk comparison</h3>
          <EChart option={sectorOption} className="mt-1 h-[275px] w-full" />
        </article>
      </section>
      <section id="portfolio-table" className="px-5 pb-10 md:px-8">
        <div className="panel-card overflow-hidden">
          <div className="border-b border-slate-700/50 px-5 py-5">
            <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
              <div>
                <h3 className="section-title">Project risk register</h3>
                <p className="mt-1 text-xs text-slate-500">
                  Sorted by calculated overall risk · {filteredProjects.length}{" "}
                  projects shown
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:flex">
                <Filter
                  value={ministry}
                  onChange={setMinistry}
                  label="Ministry"
                  options={ministries}
                />
                <Filter
                  value={sector}
                  onChange={setSector}
                  label="Sector"
                  options={sectors}
                />
                <Filter
                  value={level}
                  onChange={setLevel}
                  label="Risk"
                  options={["LOW", "MEDIUM", "HIGH", "CRITICAL"]}
                />
                <Filter
                  value={trend}
                  onChange={setTrend}
                  label="Trend"
                  options={[
                    "STABLE",
                    "IMPROVING",
                    "WORSENING",
                    "RAPIDLY WORSENING",
                  ]}
                />
              </div>
            </div>
          </div>
          <div className="max-h-[760px] overflow-auto">
            <table className="w-full min-w-[1080px] text-left">
              <thead className="sticky top-0 z-10 bg-[#0d1d2f]">
                <tr>
                  {[
                    "Project",
                    "Ministry",
                    "Sector",
                    "Cost",
                    "Schedule",
                    "Execution",
                    "Overall",
                    "Trend",
                    "Alert",
                  ].map((item) => (
                    <th
                      key={item}
                      className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500"
                    >
                      {item}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredProjects.map((project) => (
                  <tr
                    key={project.project_id}
                    className="border-t border-slate-800/80 transition hover:bg-cyan-300/[.025]"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/projects/${project.project_id}`}
                        className="block max-w-[245px] text-sm font-semibold text-slate-100 hover:text-cyan-300"
                      >
                        {project.project_name}
                      </Link>
                      <span className="text-[10px] text-slate-500">
                        {project.project_id}
                      </span>
                    </td>
                    <td className="max-w-[200px] truncate px-4 text-xs text-slate-400">
                      {project.ministry.replace("Ministry of ", "")}
                    </td>
                    <td className="px-4 text-xs text-slate-400">
                      {project.sector}
                    </td>
                    <ScoreCell value={project.risk.scores.cost_risk} />
                    <ScoreCell value={project.risk.scores.schedule_risk} />
                    <ScoreCell value={project.risk.scores.execution_risk} />
                    <ScoreCell
                      value={project.risk.scores.overall_risk}
                      strong
                    />
                    <td className="px-4">
                      <RiskBadge
                        value={project.risk.trajectory.trend}
                        compact
                      />
                    </td>
                    <td className="px-4">
                      {project.risk.alerts.length ? (
                        <span className="text-xs text-rose-300">
                          {project.risk.alerts[0].type.replace(" WARNING", "")}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </DashboardShell>
  );
}

function Filter({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="filter-control"
    >
      <option value="ALL">All {label}</option>
      {options.map((option) => (
        <option key={option} value={option}>
          {option.replace("Ministry of ", "")}
        </option>
      ))}
    </select>
  );
}
function ScoreCell({
  value,
  strong = false,
}: {
  value: number;
  strong?: boolean;
}) {
  return (
    <td
      className={`px-4 text-sm font-semibold ${strong ? (value >= 80 ? "text-rose-300" : value >= 65 ? "text-orange-300" : "text-cyan-200") : "text-slate-300"}`}
    >
      {value}
    </td>
  );
}
