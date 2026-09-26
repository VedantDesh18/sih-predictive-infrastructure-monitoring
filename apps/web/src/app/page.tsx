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
    cyan: "text-[#006b9a]",
    rose: "text-[#b74643]",
    amber: "text-[#a66b00]",
    emerald: "text-[#16734b]",
  }[tone];
  return (
    <article className={`panel-card stat-card stat-card-${tone} p-5 pl-6`}>
      <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-slate-600">
        {label}
      </p>
      <p className={`mt-3 text-2xl font-semibold tracking-tight ${toneClass}`}>
        {value}
      </p>
      <p className="mt-2 text-xs text-slate-600">{detail}</p>
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
  const [mlLevel, setMlLevel] = useState("ALL");
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
          (mlLevel === "ALL" || project.ml_risk?.risk_level === mlLevel) &&
          (trend === "ALL" || project.risk.trajectory.trend === trend)
      ),
    [projects, ministry, sector, level, mlLevel, trend]
  );

  const distributionOption: EChartsOption = useMemo(
    () => ({
      tooltip: {
        trigger: "item",
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        borderWidth: 1,
        textStyle: { color: "#1e293b" },
      },
      legend: {
        bottom: 0,
        textStyle: { color: "#475569", fontSize: 10 },
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
            borderColor: "#ffffff",
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
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        borderWidth: 1,
        textStyle: { color: "#1e293b" },
      },
      xAxis: {
        type: "category",
        data: portfolio?.portfolio_trend.map((point) => point.month) ?? [],
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        axisLabel: { color: "#475569" },
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: "#e2e8f0" } },
        axisLabel: { color: "#475569" },
      },
      series: [
        {
          type: "line",
          smooth: true,
          data: portfolio?.portfolio_trend.map((point) => point.risk) ?? [],
          symbolSize: 7,
          lineStyle: { color: "#008fc4", width: 3 },
          itemStyle: { color: "#00a4d6" },
          areaStyle: { color: "rgba(0,143,196,.12)" },
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
        splitLine: { lineStyle: { color: "#e2e8f0" } },
        axisLabel: { color: "#475569" },
      },
      yAxis: {
        type: "category",
        data:
          portfolio?.ministry_comparison.map((item) =>
            item.name.replace("Ministry of ", "")
          ) ?? [],
        axisLabel: {
          color: "#334155",
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
                      : "#008fc4",
                borderRadius: [0, 4, 4, 0],
              },
            })) ?? [],
          barWidth: 13,
          label: {
            show: true,
            position: "right",
            color: "#475569",
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
        axisLabel: { color: "#475569", fontSize: 9, rotate: 28 },
        axisLine: { lineStyle: { color: "#cbd5e1" } },
      },
      yAxis: {
        type: "value",
        max: 100,
        splitLine: { lineStyle: { color: "#e2e8f0" } },
        axisLabel: { color: "#475569" },
      },
      series: [
        {
          type: "bar",
          data: portfolio?.sector_comparison.map((item) => item.risk) ?? [],
          barWidth: "48%",
          itemStyle: { color: "#3d88bd", borderRadius: [3, 3, 0, 0] },
        },
      ],
    }),
    [portfolio]
  );

  if (error)
    return (
      <DashboardShell>
        <div className="m-8 panel-card p-8 text-rose-700">
          The monitoring API could not be reached. Start the FastAPI service and
          refresh this dashboard.
        </div>
      </DashboardShell>
    );
  if (!statistics || !portfolio)
    return (
      <DashboardShell>
        <div className="grid min-h-[60vh] place-items-center text-sm tracking-wide text-[#006b9a]">
          INITIALISING PORTFOLIO INTELLIGENCE…
        </div>
      </DashboardShell>
    );

  return (
    <DashboardShell>
      <header className="flex flex-col gap-4 border-b border-slate-200 bg-white px-5 py-5 md:flex-row md:items-center md:justify-between md:px-8">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#006b9a]">
            Infrastructure Command Center
          </p>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-[#173b5d]">
            Portfolio Risk Intelligence
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded border border-amber-200 bg-amber-50 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-amber-800">
            Synthetic Demonstration Data
          </span>
          <span className="hidden text-xs italic text-slate-500 sm:inline">
            Updated Jul 2026 · Prototype
          </span>
        </div>
      </header>
      <section className="px-5 py-6 md:px-8">
        <div className="mb-6 flex flex-col justify-between gap-3 xl:flex-row xl:items-end">
          <div>
            <h2 className="text-2xl font-semibold text-[#173b5d]">
              Early warning, before project failure
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
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
              <p className="mt-1 text-xs text-slate-600">
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
                className="group flex items-center gap-3 rounded px-2 py-2.5 transition hover:bg-[#eff8fc]"
              >
                <span className="w-4 text-xs text-slate-400">0{index + 1}</span>
                <span className="min-w-0 flex-1 truncate text-xs font-medium text-slate-700 group-hover:text-[#006b9a]">
                  {project.project_name}
                </span>
                <span className="text-sm font-semibold text-rose-700">
                  {project.overall_risk}
                </span>
                <span className="text-slate-400">›</span>
              </Link>
            ))}
          </div>
          <Link
            href="#portfolio-table"
            className="mt-3 block border-t border-slate-200 pt-3 text-center text-xs font-semibold text-[#006b9a]"
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
          <div className="border-b border-slate-200 px-5 py-5">
            <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
              <div>
                <h3 className="section-title">Project risk register</h3>
                <p className="mt-1 text-xs text-slate-600">
                  Sorted by calculated overall risk · {filteredProjects.length}{" "}
                  projects shown
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:flex">
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
                  value={mlLevel}
                  onChange={setMlLevel}
                  label="ML Risk"
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
              <thead className="sticky top-0 z-10 bg-[#eef6fa]">
                <tr>
                  {[
                    "Project",
                    "Ministry",
                    "Sector",
                    "Cost",
                    "Schedule",
                    "Execution",
                    "Overall",
                    "ML Risk",
                    "Trend",
                    "Alert",
                  ].map((item) => (
                    <th
                      key={item}
                      className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#36536c]"
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
                    className="border-t border-slate-200 transition hover:bg-[#f3faff]"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/projects/${project.project_id}`}
                        className="block max-w-[245px] text-sm font-semibold text-slate-800 hover:text-[#006b9a]"
                      >
                        {project.project_name}
                      </Link>
                      <span className="text-[10px] text-slate-500">
                        {project.project_id}
                      </span>
                    </td>
                    <td className="max-w-[200px] truncate px-4 text-xs text-slate-600">
                      {project.ministry.replace("Ministry of ", "")}
                    </td>
                    <td className="px-4 text-xs text-slate-600">
                      {project.sector}
                    </td>
                    <ScoreCell value={project.risk.scores.cost_risk} />
                    <ScoreCell value={project.risk.scores.schedule_risk} />
                    <ScoreCell value={project.risk.scores.execution_risk} />
                    <ScoreCell
                      value={project.risk.scores.overall_risk}
                      strong
                    />
                    <td className="px-4 text-xs font-semibold text-indigo-700">
                      {project.ml_risk ? `${Math.round(project.ml_risk.overall_risk_probability * 100)}%` : "—"}
                    </td>
                    <td className="px-4">
                      <RiskBadge
                        value={project.risk.trajectory.trend}
                        compact
                      />
                    </td>
                    <td className="px-4">
                      {project.risk.alerts.length ? (
                        <span className="text-xs text-rose-700">
                          {project.risk.alerts[0].type.replace(" WARNING", "")}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
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
    <label className="filter-field">
      <span className="filter-label">{label}</span>
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
    </label>
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
      className={`px-4 text-sm font-semibold ${strong ? (value >= 80 ? "text-rose-700" : value >= 65 ? "text-orange-700" : "text-[#006b9a]") : "text-slate-700"}`}
    >
      {value}
    </td>
  );
}
