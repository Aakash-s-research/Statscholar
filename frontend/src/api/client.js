import axios from "axios";

// In local dev, "/api" is proxied to the backend by Vite (see
// vite.config.js) — that proxy doesn't exist in a production build, where
// the frontend (a static site) and backend (a separate web service) are
// on two different domains. VITE_API_BASE_URL, set at build time, points
// the deployed frontend at the real backend URL instead.
const client = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "/api" });

const TOKEN_STORAGE_KEY = "statscholar_token";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

// Attaches the current token (if any) to every request automatically, so
// call sites elsewhere in the app don't need to think about auth at all.
client.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// If a token expires or is otherwise rejected mid-session, clear it and
// tell App.jsx (via a custom event) to drop back to the login screen —
// otherwise the user is stuck seeing broken requests with no explanation.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401 && getStoredToken()) {
      clearStoredToken();
      window.dispatchEvent(new Event("statscholar:auth-expired"));
    }
    return Promise.reject(error);
  }
);

export async function register(email, password) {
  const { data } = await client.post("/auth/register", { email, password });
  return data; // { access_token, user }
}

export async function login(email, password) {
  const { data } = await client.post("/auth/login", { email, password });
  return data; // { access_token, user }
}

export async function fetchCurrentUser() {
  const { data } = await client.get("/auth/me");
  return data;
}

export async function resendVerification() {
  const { data } = await client.post("/auth/resend-verification");
  return data;
}

export async function verifyEmail(token) {
  const { data } = await client.post("/auth/verify-email", { token });
  return data;
}

export async function forgotPassword(email) {
  const { data } = await client.post("/auth/forgot-password", { email });
  return data;
}

export async function resetPassword(token, newPassword) {
  const { data } = await client.post("/auth/reset-password", { token, new_password: newPassword });
  return data;
}

export async function getSeries(datasetId, columns) {
  const { data } = await client.get(`/data/${datasetId}/series`, {
    params: { columns: columns.join(",") },
  });
  return data;
}

export async function uploadDataset(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post("/data/upload", form);
  return data;
}

export async function runTrendTest({ datasetId, variable, timeColumn, test, mode, alpha = 0.05, seasonColumn }) {
  const { data } = await client.post("/trend/run", {
    dataset_id: datasetId,
    variable,
    time_column: timeColumn,
    test,
    mode,
    alpha,
    ...(seasonColumn ? { season_column: seasonColumn } : {}),
  });
  return data;
}

export async function runCorrelation({ datasetId, variables, method, mode }) {
  const { data } = await client.post("/correlation/run", {
    dataset_id: datasetId,
    variables,
    method,
    mode,
  });
  return data;
}

export async function runRegression({ datasetId, predictor, outcome, mode }) {
  const { data } = await client.post("/regression/run", {
    dataset_id: datasetId,
    predictor,
    outcome,
    mode,
  });
  return data;
}

export async function describeVariable(datasetId, variable) {
  const { data } = await client.get(`/descriptive/${datasetId}/${variable}`);
  return data;
}

export async function exportReport({ projectTitle, sections }) {
  const response = await client.post(
    "/report/export/docx",
    { project_title: projectTitle, sections },
    { responseType: "blob" }
  );
  return response.data;
}

export async function exportReportPdf({ projectTitle, sections }) {
  const response = await client.post(
    "/report/export/pdf",
    { project_title: projectTitle, sections },
    { responseType: "blob" }
  );
  return response.data;
}

export async function getChartRecommendations(datasetId) {
  const { data } = await client.get(`/visualization/${datasetId}/recommend`);
  return data.recommendations;
}

export default client;
