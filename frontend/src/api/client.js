const backendUrl = (
  import.meta.env.SKILLLOCK_BACKEND_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export const API_BASE_URL = `${backendUrl}/api`;
export const UPLOAD_BASE_URL = `${backendUrl}/uploads`;

export function apiUrl(path) {
  const endpoint = path.replace(/^\/?api\/?/, "");
  return `${API_BASE_URL}/${endpoint}`;
}

export function uploadUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  const filename = path.replace(/^\/?uploads\/?/, "");
  return `${UPLOAD_BASE_URL}/${filename.replace(/^\/+/, "")}`;
}

export async function request(path, options = {}) {
  const response = await fetch(apiUrl(path), { credentials: "include", ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Something went wrong. Please try again.");
  return body;
}
