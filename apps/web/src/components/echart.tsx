"use client";

import type { EChartsOption } from "echarts";
import { useEffect, useRef } from "react";

type EChartProps = {
  option: EChartsOption;
  className?: string;
};

export function EChart({ option, className = "" }: EChartProps) {
  const chartElement = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartElement.current) return;
    let chart: import("echarts").ECharts | undefined;
    let observer: ResizeObserver | undefined;
    let disposed = false;

    async function renderChart() {
      const echarts = await import("echarts");
      if (!chartElement.current || disposed) return;
      chart = echarts.init(chartElement.current, undefined, {
        renderer: "svg",
      });
      chart.setOption(option);
      observer = new ResizeObserver(() => chart?.resize());
      observer.observe(chartElement.current);
    }

    renderChart();
    return () => {
      disposed = true;
      observer?.disconnect();
      chart?.dispose();
    };
  }, [option]);

  return (
    <div
      aria-label="Data visualization"
      className={className}
      ref={chartElement}
    />
  );
}
