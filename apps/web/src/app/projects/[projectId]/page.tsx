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
    <div className={`panel-card stat-card stat-card-${accent} p-5 pl-6`}>
      <p className="text-[11px] font-bold uppercase tracking-[.1em] text-slate-600">
        {label}
      </p>
      <p
        className={`mt-2 text-3xl font-semibold ${accent === "rose" ? "text-rose-700" : accent === "amber" ? "text-amber-700" : "text-[#006b9a]"}`}
      >
        {value}
      </p>
      <p className="mt-2 text-xs text-slate-600">{description}</p>
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
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        borderWidth: 1,
        textStyle: { color: "#1e293b" },
      },
      xAxis: {
        type: "category",
        data:
          project?.risk.trajectory.history.map((point) => point.month) ?? [],
        axisLabel: { color: "#475569" },
        axisLine: { lineStyle: { color: "#cbd5e1" } },
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 100,
        axisLabel: { color: "#475569" },
        splitLine: { lineStyle: { color: "#e2e8f0" } },
      },
      series: [
        {
          type: "line",
          smooth: true,
          data:
            project?.risk.trajectory.history.map((point) => point.risk) ?? [],
          lineStyle: { color: "#d8504c", width: 4 },
          itemStyle: { color: "#d8504c" },
          symbolSize: 10,
          areaStyle: { color: "rgba(216,80,76,.1)" },
          markLine: {
            symbol: "none",
            lineStyle: { color: "#d48b00", type: "dashed" },
            label: { color: "#9a6500" },
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
        <div className="m-8 panel-card p-8 text-rose-700">
          Project not found or API unavailable.
        </div>
      </DashboardShell>
    );
  if (!project)
    return (
      <DashboardShell>
        <div className="grid min-h-[60vh] place-items-center text-sm tracking-wide text-[#006b9a]">
          LOADING PROJECT RISK PROFILE…
        </div>
      </DashboardShell>
    );
  const risk = project.risk;
  return (
    <DashboardShell>
      <header className="border-b border-slate-200 bg-white px-5 py-5 md:px-8">
        <Link
          href="/"
          className="text-xs font-semibold text-[#006b9a] hover:text-[#173b5d]"
        >
          ← Back to portfolio command
        </Link>
        <div className="mt-5 flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="rounded border border-amber-200 bg-amber-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-amber-800">
                Synthetic Demonstration Data
              </span>
              <RiskBadge value={risk.scores.risk_level} />
            </div>
            <p className="text-[10px] font-bold uppercase tracking-[.14em] text-slate-500">
              {project.project_id} · {project.sector}
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[#173b5d] md:text-3xl">
              {project.project_name}
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              {project.agency} · {project.location}
            </p>
          </div>
          <div className="rounded border border-rose-200 bg-rose-50 px-5 py-3 shadow-sm">
            <p className="text-[10px] font-bold uppercase tracking-[.1em] text-rose-700">
              Overall calculated risk
            </p>
            <p className="mt-1 text-4xl font-semibold text-rose-700">
              {risk.scores.overall_risk}
              <span className="text-lg text-rose-700/60">/100</span>
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
              <p className="mt-1 text-sm text-slate-600">
                Risk is rising from {risk.trajectory.history[0].risk} to{" "}
                {risk.trajectory.history.at(-1)?.risk} across the reporting
                history.
              </p>
            </div>
            <RiskBadge value={risk.trajectory.trend} />
          </div>
          <EChart option={trajectoryOption} className="mt-2 h-[310px] w-full" />
          <div className="mt-1 grid grid-cols-2 border-t border-slate-200 pt-4 text-xs sm:grid-cols-4">
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
          <p className="mt-1 text-xs text-slate-600">
            Calculated directly from the submitted project indicators.
          </p>
          <div className="mt-6 space-y-5">
            {risk.drivers.map((driver) => (
              <div key={driver.driver}>
                <div className="mb-2 flex justify-between text-sm">
                  <span className="font-medium text-slate-700">
                    {driver.driver}
                  </span>
                  <span className="font-bold text-rose-700">
                    +{driver.contribution}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-200">
                  <div
                    className="h-full rounded-full bg-[#df8e2d]"
                    style={{
                      width: `${Math.min(driver.contribution * 3.6, 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-8 rounded border border-[#bfe3f1] bg-[#f0f9fc] p-4">
            <p className="text-[10px] font-bold uppercase tracking-[.1em] text-[#006b9a]">
              Engine boundary
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-600">
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
              <p className="mt-1 text-xs text-slate-600">
                Prioritised using risk level and trajectory.
              </p>
            </div>
            <span className="pulse-dot">ACTION REQUIRED</span>
          </div>
          <div className="mt-4 space-y-3">
            {risk.alerts.map((alert) => (
              <div
                key={alert.type}
                className="rounded border border-rose-200 bg-rose-50 p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <RiskBadge value={alert.severity} compact />
                  <h3 className="text-sm font-semibold text-slate-800">
                    {alert.type}
                  </h3>
                </div>
                <p className="mt-2 text-sm text-slate-700">{alert.reason}</p>
                <p className="mt-2 text-xs font-medium text-rose-700">
                  {alert.supporting_metric}
                </p>
              </div>
            ))}
          </div>
        </article>
        <article className="panel-card p-5 xl:col-span-5">
          <h2 className="section-title">Recommended investigation</h2>
          <p className="mt-1 text-xs text-slate-600">
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
                className="flex gap-3 text-sm leading-6 text-slate-700"
              >
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded border border-[#addfee] bg-[#eff9fc] text-xs font-bold text-[#006b9a]">
                  {index + 1}
                </span>
                {item}
              </li>
            ))}
          </ol>
          <div className="mt-7 grid grid-cols-3 gap-3 border-t border-slate-200 pt-5">
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
      <p className="text-[10px] font-bold uppercase tracking-[.09em] text-slate-500">
        {label}
      </p>
      <p className="mt-1 text-xs font-semibold text-slate-700">{value}</p>
    </div>
  );
}
