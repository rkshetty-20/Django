const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function normalizeApiErrorDetail(detail) {
  if (!detail) return { message: "Unable to analyze product.", debug: detail };
  if (typeof detail === "string") return { message: detail, debug: detail };
  if (typeof detail === "object") {
    const message =
      detail.user_message ||
      detail.message ||
      "Unable to analyze product.";
    return { message, debug: detail };
  }
  return { message: "Unable to analyze product.", debug: detail };
}

export async function analyzeProduct(payload) {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const normalized = normalizeApiErrorDetail(data.detail);
    const error = new Error(normalized.message);
    error.debug = normalized.debug;
    error.status = response.status;
    throw error;
  }

  return data;
}

export async function chatAboutProduct(payload) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const normalized = normalizeApiErrorDetail(data.detail);
    const error = new Error(normalized.message || "Unable to answer that question.");
    error.debug = normalized.debug;
    error.status = response.status;
    throw error;
  }

  return data;
}
