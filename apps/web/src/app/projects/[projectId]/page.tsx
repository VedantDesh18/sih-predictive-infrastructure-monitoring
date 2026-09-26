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
import type { Project, ProjectTrajectoryResponse } from "@/lib/types";

function Metric({
  label,
  value,
  description,
  accent = "cyan",
}: {
  label: string;
  value: string | number;
  description: string;
  accent?: "cyan" | "rose" | "amber" | "indigo" | "emerald";
}) {
  const accentColor = {
    cyan: "text-[#006b9a]",
    rose: "text-rose-700",
    amber: "text-amber-700",
    indigo: "text-indigo-700",
    emerald: "text-emerald-700",
  }[accent];

  return (
    <div className={`panel-card stat-card stat-card-${accent === "indigo" ? "cyan" : accent === "emerald" ? "cyan" : accent} p-5 pl-6`}>
      <p className="text-[11px] font-bold uppercase tracking-[.1em] text-slate-600">
        {label}
      </p>
      <p className={`mt-2 text-3xl font-semibold ${accentColor}`}>
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
  const [trajectoryData, setTrajectoryData] = useState<ProjectTrajectoryResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    params.then(({ projectId }) => {
      Promise.all([
        fetch(`/api/v1/projects/${projectId}`, { cache: "no-store" }).then((r) =>
          r.ok ? r.json() : Promise.reject()
        ),
        fetch(`/api/v1/projects/${projectId}/trajectory`, { cache: "no-store" }).then((r) =>
          r.ok ? r.json() : null
        ),
      ])
        .then(([proj, traj]) => {
          setProject(proj);
          if (traj) setTrajectoryData(traj);
        })
        .catch(() => setError(true));
    });
  }, [params]);

  // Full multi-series trajectory chart: Predicted risk vs Realized overrun/delay
  const trajectoryOption: EChartsOption = useMemo(() => {
    if (!trajectoryData?.trajectory?.length) {
      // Fallback to project's recent risk history if trajectory endpoint is not yet loaded
      return {
        grid: { left: 45, right: 30, top: 30, bottom: 30 },
        xAxis: {
          type: "category",
          data: project?.risk.trajectory.history.map((point) => point.month) ?? [],
          axisLabel: { color: "#475569" },
        },
        yAxis: { type: "value", min: 0, max: 100 },
        series: [
          {
            type: "line",
            smooth: true,
            data: project?.risk.trajectory.history.map((point) => point.risk) ?? [],
            lineStyle: { color: "#6366f1", width: 3 },
          },
        ],
      };
    }

    const dates = trajectoryData.trajectory.map((p) => p.snapshot_date);
    const overallRiskProbs = trajectoryData.trajectory.map((p) =>
      Math.round(p.overall_probability * 100)
    );
    const costProbs = trajectoryData.trajectory.map((p) =>
      Math.round(p.cost_probability * 100)
    );
    const realizedOverruns = trajectoryData.trajectory.map((p) =>
      p.realized_cost_overrun !== null ? Number(p.realized_cost_overrun.toFixed(1)) : null
    );
    const realizedDelays = trajectoryData.trajectory.map((p) =>
      p.realized_schedule_delay !== null ? Number(p.realized_schedule_delay.toFixed(1)) : null
    );

    return {
      tooltip: {
        trigger: "axis",
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        borderWidth: 1,
        padding: [10, 14],
        textStyle: { color: "#1e293b", fontSize: 12 },
        formatter: (params: any) => {
          if (!Array.isArray(params) || params.length === 0) return "";
          const dateStr = params[0].axisValue;
          let html = `<div class="font-bold text-slate-800 pb-1 mb-1 border-b border-slate-200">Snapshot: ${dateStr}</div>`;
          params.forEach((item: any) => {
            if (item.value !== null && item.value !== undefined) {
              const unit = item.seriesName.includes("(%)") ? "%" : item.seriesName.includes("Delay") ? " mo" : "";
              html += `<div class="flex items-center justify-between gap-4 py-0.5">
                <span style="color: ${item.color}" class="font-medium">${item.seriesName}:</span>
                <span class="font-semibold">${item.value}${unit}</span>
              </div>`;
            }
          });
          return html;
        },
      },
      legend: {
        top: 0,
        right: 10,
        textStyle: { color: "#475569", fontSize: 11 },
        itemWidth: 14,
        itemHeight: 10,
      },
      grid: { left: 45, right: 55, top: 40, bottom: 45 },
      dataZoom: [
        {
          type: "slider",
          show: true,
          bottom: 2,
          height: 18,
          borderColor: "#e2e8f0",
          fillerColor: "rgba(99, 102, 241, 0.15)",
          handleStyle: { color: "#6366f1" },
          textStyle: { color: "#64748b", fontSize: 10 },
        },
        { type: "inside" },
      ],
      xAxis: {
        type: "category",
        data: dates,
        axisLabel: {
          color: "#475569",
          fontSize: 10,
          formatter: (val: string) => {
            const parts = val.split("-");
            return parts.length >= 2 ? `${parts[0].slice(2)}-${parts[1]}` : val;
          },
        },
        axisLine: { lineStyle: { color: "#cbd5e1" } },
      },
      yAxis: [
        {
          type: "value",
          name: "ML Risk Prob (%)",
          nameTextStyle: { color: "#6366f1", fontSize: 10, align: "left" },
          min: 0,
          max: 100,
          axisLabel: { color: "#6366f1", formatter: "{value}%" },
          splitLine: { lineStyle: { color: "#f1f5f9" } },
        },
        {
          type: "value",
          name: "Realized Overrun / Delay",
          nameTextStyle: { color: "#0284c7", fontSize: 10, align: "right" },
          axisLabel: { color: "#0284c7" },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: "ML Overall Risk (%)",
          type: "line",
          yAxisIndex: 0,
          smooth: true,
          connectNulls: true,
          data: overallRiskProbs,
          lineStyle: { color: "#6366f1", width: 3.5 },
          itemStyle: { color: "#6366f1" },
          showSymbol: false,
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(99, 102, 241, 0.28)" },
                { offset: 1, color: "rgba(99, 102, 241, 0.02)" },
              ],
            },
          },
          markLine: {
            symbol: "none",
            lineStyle: { color: "#e11d48", type: "dashed", width: 1.5 },
            label: {
              formatter: "ML High Risk (65%)",
              color: "#be123c",
              fontSize: 10,
              position: "insideEndTop",
            },
            data: [{ yAxis: 65 }],
          },
        },
        {
          name: "ML Cost Prob (%)",
          type: "line",
          yAxisIndex: 0,
          smooth: true,
          connectNulls: true,
          data: costProbs,
          lineStyle: { color: "#f59e0b", width: 1.8, type: "dashed" },
          itemStyle: { color: "#f59e0b" },
          showSymbol: false,
        },
        {
          name: "Realized Cost Overrun (%)",
          type: "line",
          yAxisIndex: 1,
          smooth: false,
          connectNulls: true,
          data: realizedOverruns,
          lineStyle: { color: "#0284c7", width: 2.8 },
          itemStyle: { color: "#0284c7" },
          symbol: "circle",
          symbolSize: 5,
        },
        {
          name: "Realized Delay (Mo)",
          type: "line",
          yAxisIndex: 1,
          smooth: true,
          connectNulls: true,
          data: realizedDelays,
          lineStyle: { color: "#ea580c", width: 2.2, type: "dotted" },
          itemStyle: { color: "#ea580c" },
          showSymbol: false,
        },
      ],
    };
  }, [trajectoryData, project]);

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
  const costGrowth = risk.features.cost_growth;
  const totalSnapshots = trajectoryData?.total_snapshots ?? project.risk.trajectory.history.length;

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
              <span className="rounded border border-emerald-300 bg-emerald-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-800">
                {project.data_source || "PAIMANA Real Ongoing Dataset"}
              </span>
              <RiskBadge value={risk.scores.risk_level} />
              {project.ml_risk && (
                <span className={`rounded border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${
                  project.ml_risk.risk_level === "CRITICAL"
                    ? "border-rose-300 bg-rose-50 text-rose-800"
                    : project.ml_risk.risk_level === "HIGH"
                      ? "border-orange-300 bg-orange-50 text-orange-800"
                      : project.ml_risk.risk_level === "MEDIUM"
                        ? "border-amber-300 bg-amber-50 text-amber-800"
                        : "border-emerald-300 bg-emerald-50 text-emerald-800"
                }`}>
                  ML Risk: {project.ml_risk.risk_level}
                </span>
              )}
            </div>
            <p className="text-[10px] font-bold uppercase tracking-[.14em] text-slate-500">
              Project ID: {project.project_id} · Sector: {project.sector}
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[#173b5d] md:text-3xl">
              {project.project_name}
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              {project.agency} · {project.ministry} · {totalSnapshots} monthly snapshots scored
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded border border-rose-200 bg-rose-50 px-5 py-3 shadow-sm">
              <p className="text-[10px] font-bold uppercase tracking-[.1em] text-rose-700">
                Rule-based Risk Score
              </p>
              <p className="mt-1 text-3xl font-semibold text-rose-700">
                {risk.scores.overall_risk}
                <span className="text-sm font-normal text-rose-700/60"> / 100</span>
              </p>
            </div>
            {project.ml_risk && (
              <div className="rounded border border-indigo-200 bg-indigo-50 px-5 py-3 shadow-sm">
                <p className="text-[10px] font-bold uppercase tracking-[.1em] text-indigo-700">
                  ML Predicted Risk Prob
                </p>
                <div className="flex items-baseline gap-2">
                  <p className="mt-1 text-3xl font-semibold text-indigo-700">
                    {Math.round(project.ml_risk.overall_risk_probability * 100)}%
                  </p>
                  <span className="text-xs font-semibold uppercase text-indigo-900">
                    {project.ml_risk.risk_level}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Primary KPI row */}
      <section className="grid gap-4 px-5 py-6 sm:grid-cols-2 md:grid-cols-4 md:px-8">
        <Metric
          label="Approved Budget"
          value={`₹${formatCrore(project.approved_cost)}`}
          description="Original approved project cost"
          accent="cyan"
        />
        <Metric
          label="Revised / Anticipated"
          value={`₹${formatCrore(project.revised_cost)}`}
          description={`${costGrowth > 0 ? `+${costGrowth}%` : "On budget"} cost variation`}
          accent={costGrowth > 10 ? "rose" : costGrowth > 0 ? "amber" : "emerald"}
        />
        <Metric
          label="Cumulative Expenditure"
          value={`₹${formatCrore(project.expenditure)}`}
          description={`${Math.round(risk.features.expenditure_ratio)}% of revised budget utilized`}
          accent="indigo"
        />
        <Metric
          label="Physical Progress"
          value={`${project.physical_progress}%`}
          description={`Planned completion: ${project.planned_completion}`}
          accent="emerald"
        />
      </section>

      {/* Risk Trajectory Section — The heart of Step 2/3 */}
      <section className="grid gap-5 px-5 pb-5 md:px-8 xl:grid-cols-12">
        <article className="panel-card p-5 xl:col-span-8">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="section-title">Risk Trajectory & Early Warning Timeline</h2>
                <span className="rounded bg-indigo-100 px-2 py-0.5 text-[10px] font-bold uppercase text-indigo-800">
                  ML vs Realized Outcomes
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-600">
                Predicted risk probability over time plotted against actual realized cost overrun and schedule slippage across {totalSnapshots} monthly snapshots.
              </p>
            </div>
            <RiskBadge value={risk.trajectory.trend} />
          </div>

          <EChart option={trajectoryOption} className="mt-3 h-[360px] w-full" />

          <div className="mt-2 grid grid-cols-2 gap-3 border-t border-slate-200 pt-4 text-xs sm:grid-cols-4">
            <div className="rounded bg-slate-50 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-500">ML Cost Overrun Prob</p>
              <p className="mt-1 text-base font-semibold text-indigo-700">
                {project.ml_risk ? `${Math.round(project.ml_risk.cost_overrun_probability * 100)}%` : "—"}
              </p>
            </div>
            <div className="rounded bg-slate-50 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-500">ML Schedule Overrun Prob</p>
              <p className="mt-1 text-base font-semibold text-indigo-700">
                {project.ml_risk ? `${Math.round(project.ml_risk.schedule_overrun_probability * 100)}%` : "—"}
              </p>
            </div>
            <div className="rounded bg-slate-50 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-500">Realized Cost Growth</p>
              <p className={`mt-1 text-base font-semibold ${costGrowth > 10 ? "text-rose-700" : "text-slate-800"}`}>
                {costGrowth > 0 ? `+${costGrowth}%` : "0.0%"}
              </p>
            </div>
            <div className="rounded bg-slate-50 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-500">Timeline Slippage</p>
              <p className="mt-1 text-base font-semibold text-slate-800">
                {risk.features.milestone_delay > 0 ? `${risk.features.milestone_delay} days` : "On schedule"}
              </p>
            </div>
          </div>
        </article>

        {/* Top risk drivers */}
        <article className="panel-card p-5 xl:col-span-4">
          <h2 className="section-title">Top Risk Drivers</h2>
          <p className="mt-1 text-xs text-slate-600">
            Calculated transparently from latest monthly reporting data.
          </p>
          <div className="mt-6 space-y-5">
            {risk.drivers.length ? (
              risk.drivers.map((driver) => (
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
              ))
            ) : (
              <p className="py-4 text-center text-xs text-slate-500">
                Project metrics within stable operating envelope.
              </p>
            )}
          </div>
          <div className="mt-8 rounded border border-indigo-200 bg-indigo-50/50 p-4">
            <p className="text-[10px] font-bold uppercase tracking-[.1em] text-indigo-800">
              Phase 2 Inference Architecture
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Scored via Phase 2 leakage-safe LogisticRegression models with 6-month backward snapshot lookback. Models trained on completed infrastructure projects and served against ongoing project journeys.
            </p>
          </div>
        </article>
      </section>

      {/* Early warnings section */}
      <section className="px-5 pb-10 md:px-8">
        <article className="panel-card p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="section-title">Active Early Warnings & Alerts</h2>
              <p className="mt-1 text-xs text-slate-600">
                Prioritised alerts combining transparent rule thresholds and Phase 2 machine learning signals.
              </p>
            </div>
            {(risk.alerts.length > 0 || (project.ml_alerts && project.ml_alerts.length > 0)) && (
              <span className="pulse-dot">ACTION REQUIRED</span>
            )}
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {project.ml_alerts?.map((alert) => (
              <div
                key={`ml-${alert.type}`}
                className="rounded border border-indigo-300 bg-indigo-50/80 p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-indigo-700 px-2 py-0.5 text-[10px] font-bold uppercase text-white">
                    ML Alert
                  </span>
                  <RiskBadge value={alert.severity} compact />
                  <h3 className="text-sm font-semibold text-slate-800">
                    {alert.type}
                  </h3>
                </div>
                <p className="mt-2 text-sm text-slate-700">{alert.reason}</p>
                <p className="mt-2 text-xs font-semibold text-indigo-700">
                  {alert.supporting_metric}
                </p>
              </div>
            ))}

            {risk.alerts.map((alert) => (
              <div
                key={`rule-${alert.type}`}
                className="rounded border border-rose-200 bg-rose-50 p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-rose-600 px-2 py-0.5 text-[10px] font-bold uppercase text-white">
                    Rule Alert
                  </span>
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

            {!risk.alerts.length && (!project.ml_alerts || !project.ml_alerts.length) && (
              <div className="col-span-2 rounded border border-emerald-200 bg-emerald-50 p-4 text-emerald-800 text-sm">
                No active critical overrun alerts. Project is progressing within nominal risk parameters.
              </div>
            )}
          </div>
        </article>
      </section>
    </DashboardShell>
  );
}
