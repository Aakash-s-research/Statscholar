// Shared design tokens — single source of truth for color/type so pages
// don't drift from each other.

export const T = {
  ink: "#1B2A4A",
  paper: "#FAFAF7",
  surface: "#FFFFFF",
  line: "#E4E1D8",
  teal: "#2F6F6B",
  tealSoft: "#E7F0EF",
  amber: "#C97D34",
  amberSoft: "#F8EDE1",
  slate: "#64748B",
  sidebarGradient: "linear-gradient(160deg, #1B2A4A 0%, #0F4A42 100%)",
  heroGradient: "linear-gradient(120deg, #E7F0EF 0%, #FAFAF7 60%)",
};

export const serif = "'Source Serif 4', Georgia, serif";
export const sans = "'IBM Plex Sans', system-ui, sans-serif";
export const mono = "'IBM Plex Mono', ui-monospace, monospace";

export const MODULES = [
  { id: "dashboard", label: "Dashboard", path: "/" },
  { id: "prep", label: "Data Preparation", path: "/prep" },
  { id: "descriptive", label: "Descriptive Statistics", path: "/descriptive" },
  { id: "trend", label: "Trend Analysis", path: "/trend" },
  { id: "correlation", label: "Correlation", path: "/correlation" },
  { id: "regression", label: "Regression", path: "/regression" },
  { id: "visualization", label: "Visualization", path: "/visualization" },
  { id: "interpretation", label: "Automated Interpretation", path: "/interpretation" },
  { id: "report", label: "Report Generation", path: "/report" },
];
