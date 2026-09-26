export type Alert = {
  type: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  reason: string;
  supporting_metric: string;
};

export type Driver = { driver: string; contribution: number };

export type Risk = {
  features: {
    cost_growth: number;
    progress_variance: number;
    schedule_variance: number;
    expenditure_ratio: number;
    milestone_delay: number;
    risk_trend: string;
  };
  scores: {
    cost_risk: number;
    schedule_risk: number;
    execution_risk: number;
    overall_risk: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  };
  trajectory: {
    history: { month: string; risk: number }[];
    risk_velocity: number;
    risk_acceleration: number;
    trend: string;
  };
  drivers: Driver[];
  alerts: Alert[];
  predictions: { estimated_cost_overrun: number; delay_probability: number };
};

export type Project = {
  project_id: string;
  project_name: string;
  ministry: string;
  sector: string;
  agency: string;
  location: string;
  approved_cost: number;
  revised_cost: number;
  expenditure: number;
  planned_progress: number;
  physical_progress: number;
  planned_completion: string;
  expected_completion: string;
  condition: string;
  data_source: string;
  risk: Risk;
  ml_risk?: {
    cost_overrun_probability: number;
    schedule_overrun_probability: number;
    overall_risk_probability: number;
    risk_level: string;
  };
  ml_alerts?: Alert[];
};

export type Statistics = {
  data_source: string;
  total_projects: number;
  high_risk_projects: number;
  critical_projects: number;
  rising_risk_projects: number;
  total_approved_cost: number;
  total_revised_cost: number;
  potential_cost_exposure: number;
};

export type Portfolio = {
  data_source: string;
  risk_distribution: { level: string; count: number }[];
  portfolio_trend: { month: string; risk: number }[];
  ministry_comparison: { name: string; risk: number }[];
  sector_comparison: { name: string; risk: number }[];
  top_risky_projects: {
    project_id: string;
    project_name: string;
    overall_risk: number;
    risk_level: string;
    trend: string;
  }[];
};
