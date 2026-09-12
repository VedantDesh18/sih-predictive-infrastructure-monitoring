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
import type { Project } from "@/lib/types";

function Metric({
  label,
  value,
  description,
  accent = "cyan",
}: {
  label: string;
  value: string | number;
  description: string;
  accent?: "cyan" | "rose" | "amber";
}) {
  return (
    <div className="panel-card p-5">
      <p className="text-[11px] font-bold uppercase tracking-[.13em] text-slate-500">
        {label}
      </p>
      <p
        className={`mt-2 text-3xl font-semibold ${accent === "rose" ? "text-rose-300" : accent === "amber" ? "text-amber-200" : "text-cyan-200"}`}
      >
        {value}
      </p>
      <p className="mt-2 text-xs text-slate-500">{description}</p>
    </div>
  );
}

export default function ProjectDetail({
  params,
}: PageProps<"/projects/[projectId]">) {
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    params.then(({ projectId }) =>
      fetch(`/api/v1/projects/${projectId}`, { cache: "no-store" })
        .then((response) => (response.ok ? response.json() : Promise.reject()))
        .then(setProject)
        .catch(() => setError(true))
    );
  }, [params]);
  const trajectoryOption: EChartsOption = useMemo(
    () => ({
      grid: { left: 38, right: 24, top: 30, bottom: 28 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#12243a",
        textStyle: { color: "#e2e8f0" },
      },
      xAxis: {
        type: "category",
        data:
          project?.risk.trajectory.history.map((point) => point.month) ?? [],
        axisLabel: { color: "#94a3b8" },
        axisLine: { lineStyle: { color: "#25415e" } },
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 100,
        axisLabel: { color: "#94a3b8" },
        splitLine: { lineStyle: { color: "#1a3049" } },
      },
      series: [
        {
          type: "line",
          smooth: true,
          data:
            project?.risk.trajectory.history.map((point) => point.risk) ?? [],
          lineStyle: { color: "#fb7185", width: 4 },
          itemStyle: { color: "#fda4af" },
          symbolSize: 10,
          areaStyle: { color: "rgba(251,113,133,.12)" },
          markLine: {
            symbol: "none",
            lineStyle: { color: "#f59e0b", type: "dashed" },
            label: { color: "#fbbf24" },
            data: [{ yAxis: 65, label: { formatter: "HIGH RISK" } }],
          },
        },
      ],
    }),
    [project]
  );
  if (error)
    return (
      <DashboardShell>
        <div className="m-8 panel-card p-8 text-rose-300">
          Project not found or API unavailable.
        </div>
      </DashboardShell>
    );
  if (!project)
    return (
      <DashboardShell>
        <div className="grid min-h-screen place-items-center text-sm tracking-wide text-cyan-300">
          LOADING PROJECT RISK PROFILE…
        </div>
      </DashboardShell>
    );
  const risk = project.risk;
  return (
    <DashboardShell>
      <header className="border-b border-slate-700/50 bg-[#091827]/80 px-5 py-5 md:px-8">
        <Link
          href="/"
          className="text-xs font-semibold text-cyan-300 hover:text-cyan-100"
        >
          ← Back to portfolio command
        </Link>
        <div className="mt-5 flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-amber-300/25 bg-amber-300/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-amber-200">
                Synthetic Demonstration Data
              </span>
              <RiskBadge value={risk.scores.risk_level} />
            </div>
            <p className="text-[10px] font-bold uppercase tracking-[.18em] text-slate-500">
              {project.project_id} · {project.sector}
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white md:text-3xl">
              {project.project_name}
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              {project.agency} · {project.location}
            </p>
          </div>
          <div className="rounded-xl border border-rose-400/25 bg-rose-400/10 px-5 py-3">
            <p className="text-[10px] font-bold uppercase tracking-[.15em] text-rose-200">
              Overall calculated risk
            </p>
            <p className="mt-1 text-4xl font-semibold text-rose-300">
              {risk.scores.overall_risk}
              <span className="text-lg text-rose-200/60">/100</span>
            </p>
          </div>
        </div>
      </header>
      <section className="grid gap-4 px-5 py-6 md:grid-cols-3 md:px-8">
        <Metric
          label="Cost risk"
          value={risk.scores.cost_risk}
          description={`${risk.features.cost_growth}% cost growth`}
          accent="amber"
        />
        <Metric
          label="Schedule risk"
          value={risk.scores.schedule_risk}
          description={`${risk.features.milestone_delay} days milestone delay`}
          accent="rose"
        />
        <Metric
          label="Execution risk"
          value={risk.scores.execution_risk}
          description={`${risk.features.progress_variance} pp progress variance`}
        />
      </section>
      <section className="grid gap-5 px-5 pb-5 md:px-8 xl:grid-cols-12">
        <article className="panel-card p-5 xl:col-span-7">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
            <div>
              <h2 className="section-title">Risk trajectory</h2>
              <p className="mt-1 text-sm text-slate-400">
                Risk is rising from {risk.trajectory.history[0].risk} to{" "}
                {risk.trajectory.history.at(-1)?.risk} across the reporting
                history.
              </p>
            </div>
            <RiskBadge value={risk.trajectory.trend} />
          </div>
          <EChart option={trajectoryOption} className="mt-2 h-[310px] w-full" />
          <div className="mt-1 grid grid-cols-2 border-t border-slate-700/50 pt-4 text-xs sm:grid-cols-4">
            <Info
              label="Velocity"
              value={`${risk.trajectory.risk_velocity > 0 ? "+" : ""}${risk.trajectory.risk_velocity} pts / period`}
            />
            <Info
              label="Acceleration"
              value={`${risk.trajectory.risk_acceleration > 0 ? "+" : ""}${risk.trajectory.risk_acceleration} pts`}
            />
            <Info
              label="Delay probability"
              value={`${risk.predictions.delay_probability}%`}
            />
            <Info
              label="Estimated overrun"
              value={`${risk.predictions.estimated_cost_overrun}%`}
            />
          </div>
        </article>
        <article className="panel-card p-5 xl:col-span-5">
          <h2 className="section-title">Top risk drivers</h2>
          <p className="mt-1 text-xs text-slate-500">
            Calculated directly from the submitted project indicators.
          </p>
          <div className="mt-6 space-y-5">
            {risk.drivers.map((driver) => (
              <div key={driver.driver}>
                <div className="mb-2 flex justify-between text-sm">
                  <span className="font-medium text-slate-200">
                    {driver.driver}
                  </span>
                  <span className="font-bold text-rose-300">
                    +{driver.contribution}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-300 to-rose-400"
                    style={{
                      width: `${Math.min(driver.contribution * 3.6, 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-8 rounded-lg border border-cyan-400/15 bg-cyan-400/[.045] p-4">
            <p className="text-[10px] font-bold uppercase tracking-[.14em] text-cyan-300">
              Engine boundary
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-400">
              Predictive Risk Engine — prototype. These transparent rules may
              later be replaced by calibrated statistical or ML models.
            </p>
          </div>
        </article>
      </section>
      <section className="grid gap-5 px-5 pb-10 md:px-8 xl:grid-cols-12">
        <article className="panel-card p-5 xl:col-span-7">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="section-title">Early warnings</h2>
              <p className="mt-1 text-xs text-slate-500">
                Prioritised using risk level and trajectory.
              </p>
            </div>
            <span className="pulse-dot">ACTION REQUIRED</span>
          </div>
          <div className="mt-4 space-y-3">
            {risk.alerts.map((alert) => (
              <div
                key={alert.type}
                className="rounded-xl border border-rose-400/15 bg-rose-400/[.045] p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <RiskBadge value={alert.severity} compact />
                  <h3 className="text-sm font-semibold text-slate-100">
                    {alert.type}
                  </h3>
                </div>
                <p className="mt-2 text-sm text-slate-300">{alert.reason}</p>
                <p className="mt-2 text-xs font-medium text-rose-200">
                  {alert.supporting_metric}
                </p>
              </div>
            ))}
          </div>
        </article>
        <article className="panel-card p-5 xl:col-span-5">
          <h2 className="section-title">Recommended investigation</h2>
          <p className="mt-1 text-xs text-slate-500">
            Decision-support prompts for intervention owners.
          </p>
          <ol className="mt-5 space-y-4">
            {[
              "Review milestone slippage and the schedule recovery plan.",
              "Examine expenditure against physical delivery progress.",
              "Investigate execution bottlenecks with the implementing agency.",
              "Validate revised cost assumptions and contingency utilisation.",
            ].map((item, index) => (
              <li
                key={item}
                className="flex gap-3 text-sm leading-6 text-slate-300"
              >
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full border border-cyan-400/30 bg-cyan-400/10 text-xs font-bold text-cyan-200">
                  {index + 1}
                </span>
                {item}
              </li>
            ))}
          </ol>
          <div className="mt-7 grid grid-cols-3 gap-3 border-t border-slate-700/50 pt-5">
            <Info label="Approved" value={formatCrore(project.approved_cost)} />
            <Info label="Revised" value={formatCrore(project.revised_cost)} />
            <Info label="Spent" value={formatCrore(project.expenditure)} />
          </div>
        </article>
      </section>
    </DashboardShell>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-[.11em] text-slate-500">
        {label}
      </p>
      <p className="mt-1 text-xs font-semibold text-slate-200">{value}</p>
    </div>
  );
}
