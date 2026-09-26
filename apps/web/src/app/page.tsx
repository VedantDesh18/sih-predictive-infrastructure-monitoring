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
  LOW: "#10b981",
  MEDIUM: "#f59e0b",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};

const bucketPalette: Record<string, string> = {
  "on-budget": "#10b981",
  "0-10%": "#06b6d4",
  "10-20%": "#f59e0b",
  "20-50%": "#f97316",
  ">50%": "#ef4444",
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
  tone?: "cyan" | "rose" | "amber" | "emerald" | "indigo";
}) {
  const toneClass = {
    cyan: "text-[#006b9a]",
    rose: "text-[#b74643]",
    amber: "text-[#a66b00]",
    emerald: "text-[#16734b]",
    indigo: "text-indigo-700",
  }[tone];

  return (
    <article className={`panel-card stat-card stat-card-${tone === "indigo" ? "cyan" : tone} p-5 pl-6`}>
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
  const [costBucket, setCostBucket] = useState("ALL");
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
    () => [...new Set(projects.map((project) => project.ministry))].filter(Boolean),
    [projects]
  );
  const sectors = useMemo(
    () => [...new Set(projects.map((project) => project.sector))].filter(Boolean),
    [projects]
  );

  const filteredProjects = useMemo(
    () =>
      projects.filter((project) => {
        if (ministry !== "ALL" && project.ministry !== ministry) return false;
        if (sector !== "ALL" && project.sector !== sector) return false;
        if (level !== "ALL" && project.risk.scores.risk_level !== level) return false;
        if (mlLevel !== "ALL" && project.ml_risk?.risk_level !== mlLevel) return false;
        if (trend !== "ALL" && project.risk.trajectory.trend !== trend) return false;

        if (costBucket !== "ALL") {
          const app = project.approved_cost;
          const rev = project.revised_cost;
          const growth = app > 0 ? ((rev - app) / app) * 100 : 0;
          if (costBucket === "on-budget" && growth > 0) return false;
          if (costBucket === "0-10%" && (growth <= 0 || growth > 10)) return false;
          if (costBucket === "10-20%" && (growth <= 10 || growth > 20)) return false;
          if (costBucket === "20-50%" && (growth <= 20 || growth > 50)) return false;
          if (costBucket === ">50%" && growth <= 50) return false;
        }

        return true;
      }),
    [projects, ministry, sector, level, mlLevel, costBucket, trend]
  );

  // Portfolio-level Cost Overrun Risk Buckets Chart
  const costBucketOption: EChartsOption = useMemo(() => {
    const rawBuckets = portfolio?.cost_risk_buckets ?? [
      { bucket: "on-budget", count: 65 },
      { bucket: "0-10%", count: 5 },
      { bucket: "10-20%", count: 5 },
      { bucket: "20-50%", count: 12 },
      { bucket: ">50%", count: 13 },
    ];

    return {
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        borderWidth: 1,
        padding: [8, 12],
        textStyle: { color: "#1e293b", fontSize: 12 },
        formatter: (params: any) => {
          const p = Array.isArray(params) ? params[0] : params;
          const descriptions: Record<string, string> = {
            "on-budget": "Projects without cost escalation (revised ≤ approved)",
            "0-10%": "Minor cost escalation (0 to 10% overrun)",
            "10-20%": "Material cost overrun (10 to 20% growth)",
            "20-50%": "Substantial cost overrun (20 to 50% growth)",
            ">50%": "Critical cost overrun (>50% cost blowout)",
          };
          return `<b>Bucket: ${p.name}</b><br/>${descriptions[p.name] || ""}<br/>Projects: <b>${p.value}</b> (${p.value}% of portfolio)`;
        },
      },
      grid: { left: 40, right: 20, top: 25, bottom: 35 },
      xAxis: {
        type: "category",
        data: rawBuckets.map((item) => item.bucket),
        axisLabel: { color: "#334155", fontWeight: 600, fontSize: 11 },
        axisLine: { lineStyle: { color: "#cbd5e1" } },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#475569" },
        splitLine: { lineStyle: { color: "#e2e8f0" } },
      },
      series: [
        {
          name: "Projects",
          type: "bar",
          barWidth: "46%",
          data: rawBuckets.map((item) => ({
            value: item.count,
            itemStyle: {
              color: bucketPalette[item.bucket] || "#0284c7",
              borderRadius: [4, 4, 0, 0],
            },
          })),
          label: {
            show: true,
            position: "top",
            color: "#334155",
            fontWeight: 700,
            fontSize: 11,
            formatter: "{c}",
          },
        },
      ],
    };
  }, [portfolio]);

  // ML Risk Probability Distribution Donut
  const mlDistributionOption: EChartsOption = useMemo(() => {
    const rawDist = portfolio?.ml_risk_distribution ?? [
      { level: "LOW", count: 59 },
      { level: "MEDIUM", count: 8 },
      { level: "HIGH", count: 8 },
      { level: "CRITICAL", count: 25 },
    ];

    return {
      tooltip: {
        trigger: "item",
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        borderWidth: 1,
        textStyle: { color: "#1e293b" },
        formatter: "{b}: <b>{c}</b> projects ({d}%)",
      },
      legend: {
        bottom: 0,
        textStyle: { color: "#475569", fontSize: 10 },
        itemWidth: 10,
        itemHeight: 10,
      },
      series: [
        {
          name: "ML Risk Level",
          type: "pie",
          radius: ["52%", "74%"],
          center: ["50%", "45%"],
          label: { show: false },
          itemStyle: {
            borderColor: "#ffffff",
            borderWidth: 3,
            borderRadius: 4,
          },
          data: rawDist.map((item) => ({
            name: item.level,
            value: item.count,
            itemStyle: { color: riskPalette[item.level] || "#94a3b8" },
          })),
        },
      ],
    };
  }, [portfolio]);

  // Sector risk comparison
  const sectorOption: EChartsOption = useMemo(
    () => ({
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        borderWidth: 1,
        textStyle: { color: "#1e293b" },
      },
      grid: { left: 40, right: 15, top: 20, bottom: 65 },
      xAxis: {
        type: "category",
        data: portfolio?.sector_comparison.map((item) => item.name) ?? [],
        axisLabel: {
          color: "#475569",
          fontSize: 9,
          rotate: 22,
          interval: 0,
          formatter: (val: string) => (val.length > 18 ? `${val.slice(0, 16)}…` : val),
        },
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
          name: "Average Risk Score",
          data:
            portfolio?.sector_comparison.map((item) => ({
              value: item.risk,
              itemStyle: {
                color: item.risk >= 65 ? "#f97316" : "#0284c7",
                borderRadius: [3, 3, 0, 0],
              },
            })) ?? [],
          barWidth: "44%",
          label: {
            show: true,
            position: "top",
            color: "#475569",
            fontSize: 10,
          },
        },
      ],
    }),
    [portfolio]
  );

  // Ministry risk comparison
  const ministryOption: EChartsOption = useMemo(
    () => ({
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        borderWidth: 1,
        textStyle: { color: "#1e293b" },
      },
      grid: { left: 140, right: 30, top: 15, bottom: 20 },
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
          width: 125,
          overflow: "truncate",
        },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [
        {
          type: "bar",
          name: "Risk Score",
          data:
            portfolio?.ministry_comparison.map((item) => ({
              value: item.risk,
              itemStyle: {
                color:
                  item.risk >= 80
                    ? "#ef4444"
                    : item.risk >= 65
                      ? "#f97316"
                      : "#0284c7",
                borderRadius: [0, 4, 4, 0],
              },
            })) ?? [],
          barWidth: 14,
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

  return (
    <DashboardShell>
      <header className="border-b border-slate-200 bg-white px-5 py-6 md:px-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded border border-emerald-300 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-800">
                {statistics?.data_source || "PAIMANA Real Ongoing Dataset (100 Projects)"}
              </span>
              <span className="rounded border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-indigo-700">
                Phase 2 ML Model Active
              </span>
            </div>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[#173b5d] md:text-3xl">
              National Infrastructure Monitoring Command
            </h1>
            <p className="mt-1 text-xs text-slate-600">
              Live portfolio of 100 ongoing central sector infrastructure projects tracked under PAIMANA OCMS.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="#portfolio-table"
              className="rounded bg-[#006b9a] px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-[#005277]"
            >
              View 100 Projects Register ↓
            </a>
          </div>
        </div>
      </header>

      {/* KPI Cards Row */}
      <section className="grid gap-4 px-5 py-6 sm:grid-cols-2 md:grid-cols-4 md:px-8">
        <StatCard
          label="Ongoing Projects"
          value={statistics?.total_projects ?? 100}
          detail="100 real ongoing projects monitored"
          tone="emerald"
        />
        <StatCard
          label="Elevated Risk Projects"
          value={
            statistics
              ? statistics.high_risk_projects + statistics.critical_projects
              : "—"
          }
          detail="Projects with High / Critical risk scores"
          tone="rose"
        />
        <StatCard
          label="Potential Cost Overrun"
          value={
            statistics
              ? `₹${formatCrore(statistics.potential_cost_exposure)}`
              : "—"
          }
          detail="Cumulative budget escalation exposure"
          tone="amber"
        />
        <StatCard
          label="Total Portfolio Value"
          value={
            statistics ? `₹${formatCrore(statistics.total_revised_cost)}` : "—"
          }
          detail="Combined revised budget under monitoring"
          tone="cyan"
        />
      </section>

      {/* Charts Grid */}
      <section className="grid gap-5 px-5 pb-8 md:px-8 xl:grid-cols-12">
        {/* Step 3 required: Portfolio-level Cost Overrun Risk Buckets Chart */}
        <article className="panel-card p-5 xl:col-span-8">
          <div className="flex flex-col justify-between gap-1 sm:flex-row sm:items-center">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="section-title">Portfolio Cost Overrun Risk Buckets</h3>
                <span className="rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-800">
                  Latest Snapshot Data
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Categorization of the 100 ongoing projects by realized cost growth over approved budget.
              </p>
            </div>
            <span className="text-xs font-semibold text-slate-600">
              100 Total Projects
            </span>
          </div>
          <EChart option={costBucketOption} className="mt-2 h-[270px] w-full" />
        </article>

        {/* Phase 2 ML Risk Category Donut */}
        <article className="panel-card p-5 xl:col-span-4">
          <div className="flex items-center justify-between">
            <h3 className="section-title">ML Risk Categorization</h3>
            <span className="rounded bg-indigo-100 px-2 py-0.5 text-[10px] font-bold uppercase text-indigo-800">
              Phase 2 Inference
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Probability distribution from Phase 2 model scoring.
          </p>
          <EChart option={mlDistributionOption} className="mt-2 h-[270px] w-full" />
        </article>

        {/* Ministry Comparison */}
        <article className="panel-card p-5 xl:col-span-6">
          <h3 className="section-title">Ministry Risk Comparison</h3>
          <p className="mt-1 text-xs text-slate-500">
            Average composite risk scores across central ministries.
          </p>
          <EChart option={ministryOption} className="mt-2 h-[260px] w-full" />
        </article>

        {/* Sector Comparison */}
        <article className="panel-card p-5 xl:col-span-6">
          <h3 className="section-title">Sector Risk Comparison</h3>
          <p className="mt-1 text-xs text-slate-500">
            Average composite risk across the 7 tracked infrastructure sectors.
          </p>
          <EChart option={sectorOption} className="mt-2 h-[260px] w-full" />
        </article>
      </section>

      {/* Projects Table — Risk Register */}
      <section id="portfolio-table" className="px-5 pb-10 md:px-8">
        <div className="panel-card overflow-hidden">
          <div className="border-b border-slate-200 px-5 py-5">
            <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="section-title">Project Risk Register</h3>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-700">
                    Real-Data Register
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-600">
                  Showing {filteredProjects.length} of 100 ongoing projects · Rule-based and Machine Learning risk side-by-side
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
                <Filter
                  value={sector}
                  onChange={setSector}
                  label="Sector"
                  options={sectors}
                />
                <Filter
                  value={costBucket}
                  onChange={setCostBucket}
                  label="Cost Bucket"
                  options={["on-budget", "0-10%", "10-20%", "20-50%", ">50%"]}
                />
                <Filter
                  value={level}
                  onChange={setLevel}
                  label="Rule Risk"
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

          <div className="max-h-[780px] overflow-auto">
            <table className="w-full min-w-[1150px] text-left">
              <thead className="sticky top-0 z-10 bg-[#eef6fa]">
                <tr>
                  <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#36536c]">
                    Project Details
                  </th>
                  <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#36536c]">
                    Sector
                  </th>
                  <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#36536c]">
                    Budget (₹ Cr)
                  </th>
                  <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#36536c]">
                    Cost Growth
                  </th>
                  <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#36536c]">
                    Rule Risk Score
                  </th>
                  <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#36536c] bg-indigo-50/60">
                    Phase 2 ML Risk (Prob)
                  </th>
                  <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#36536c]">
                    Trend
                  </th>
                  <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#36536c]">
                    Active Warnings
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredProjects.map((project) => {
                  const growth =
                    project.approved_cost > 0
                      ? ((project.revised_cost - project.approved_cost) /
                          project.approved_cost) *
                        100
                      : 0;

                  return (
                    <tr
                      key={project.project_id}
                      className="transition hover:bg-[#f3faff]"
                    >
                      <td className="px-4 py-3">
                        <Link
                          href={`/projects/${project.project_id}`}
                          className="block max-w-[280px] truncate text-sm font-semibold text-slate-800 hover:text-[#006b9a]"
                          title={project.project_name}
                        >
                          {project.project_name}
                        </Link>
                        <span className="font-mono text-[10px] font-medium text-slate-500">
                          ID: {project.project_id}
                        </span>
                      </td>
                      <td className="px-4 text-xs font-medium text-slate-700">
                        {project.sector}
                      </td>
                      <td className="px-4 text-xs text-slate-700">
                        <div>₹{formatCrore(project.revised_cost)}</div>
                        <div className="text-[10px] text-slate-400">
                          Orig: ₹{formatCrore(project.approved_cost)}
                        </div>
                      </td>
                      <td className="px-4 text-xs font-semibold">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[11px] ${
                            growth > 20
                              ? "bg-rose-100 text-rose-800"
                              : growth > 10
                                ? "bg-orange-100 text-orange-800"
                                : growth > 0
                                  ? "bg-amber-100 text-amber-800"
                                  : "bg-emerald-100 text-emerald-800"
                          }`}
                        >
                          {growth > 0 ? `+${growth.toFixed(1)}%` : "On budget"}
                        </span>
                      </td>

                      {/* Rule-Based Risk Column */}
                      <td className="px-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-sm font-bold ${
                              project.risk.scores.overall_risk >= 80
                                ? "text-rose-700"
                                : project.risk.scores.overall_risk >= 65
                                  ? "text-orange-700"
                                  : project.risk.scores.overall_risk >= 40
                                    ? "text-amber-700"
                                    : "text-emerald-700"
                            }`}
                          >
                            {project.risk.scores.overall_risk}
                          </span>
                          <RiskBadge value={project.risk.scores.risk_level} compact />
                        </div>
                      </td>

                      {/* ML Predicted Risk Column — Side-by-side */}
                      <td className="px-4 bg-indigo-50/30">
                        {project.ml_risk ? (
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-bold text-indigo-800">
                              {Math.round(
                                project.ml_risk.overall_risk_probability * 100
                              )}
                              %
                            </span>
                            <span
                              className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                                project.ml_risk.risk_level === "CRITICAL"
                                  ? "bg-rose-100 text-rose-800 border border-rose-300"
                                  : project.ml_risk.risk_level === "HIGH"
                                    ? "bg-orange-100 text-orange-800 border border-orange-300"
                                    : project.ml_risk.risk_level === "MEDIUM"
                                      ? "bg-amber-100 text-amber-800 border border-amber-300"
                                      : "bg-emerald-100 text-emerald-800 border border-emerald-300"
                              }`}
                            >
                              {project.ml_risk.risk_level}
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>

                      <td className="px-4">
                        <RiskBadge
                          value={project.risk.trajectory.trend}
                          compact
                        />
                      </td>

                      <td className="px-4">
                        {project.ml_alerts && project.ml_alerts.length > 0 ? (
                          <span className="rounded bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold text-indigo-800">
                            {project.ml_alerts[0].type.replace(" WARNING", "")}
                          </span>
                        ) : project.risk.alerts.length > 0 ? (
                          <span className="rounded bg-rose-100 px-2 py-0.5 text-[10px] font-semibold text-rose-800">
                            {project.risk.alerts[0].type.replace(" WARNING", "")}
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
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
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}
