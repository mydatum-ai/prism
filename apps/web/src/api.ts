const API_BASE_URL = import.meta.env.VITE_PRISM_API_URL ?? "http://127.0.0.1:8004";

export type TransformResponse = {
  transformed_text: string;
  detections: Array<{ text: string; entity_type: string }>;
  audit_event: { request_id: string; tenant_id: string; event_type: string };
};

export type ChatResponse = {
  message: { role: string; content: string };
  audit_event: { request_id: string; tenant_id: string; event_type: string };
};

export type AuditResponse = {
  tenant_id: string;
  events: Array<{ request_id: string; event_type: string; app_id: string; session_id: string }>;
};

export type RuntimePolicyStatusResponse = {
  tenant_id: string;
  app_id: string;
  policy_id: string;
  policy_version: string;
  policy_source: "enterprise" | "cache" | "fallback" | "local";
  policy_cache_hit: boolean;
  policy_cache_stale: boolean;
  policy_provider_latency_ms: number;
};

export type AuthMeResponse = {
  authenticated: boolean;
  account: {
    tenant_id: string;
    email?: string | null;
    name?: string | null;
    subject: string;
  };
};

export const loginUrl = `${API_BASE_URL}/auth/login`;

const authHeaders = (tenantId: string, apiKey: string) => {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (apiKey.trim()) {
    headers["X-Prism-Tenant"] = tenantId;
    headers["X-Prism-API-Key"] = apiKey;
  }
  return headers;
};

export async function transformText(params: {
  tenantId: string;
  apiKey: string;
  appId: string;
  sessionId: string;
  text: string;
}): Promise<TransformResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/transform`, {
    method: "POST",
    headers: authHeaders(params.tenantId, params.apiKey),
    credentials: "include",
    body: JSON.stringify({
      tenant_id: params.tenantId,
      app_id: params.appId,
      session_id: params.sessionId,
      text: params.text
    })
  });
  if (!response.ok) throw new Error(`Transform failed: ${response.status}`);
  return (await response.json()) as TransformResponse;
}

export async function chatMock(params: {
  tenantId: string;
  apiKey: string;
  appId: string;
  sessionId: string;
  text: string;
}): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/chat/mock`, {
    method: "POST",
    headers: authHeaders(params.tenantId, params.apiKey),
    credentials: "include",
    body: JSON.stringify({
      tenant_id: params.tenantId,
      app_id: params.appId,
      session_id: params.sessionId,
      messages: [{ role: "user", content: params.text }]
    })
  });
  if (!response.ok) throw new Error(`Chat failed: ${response.status}`);
  return (await response.json()) as ChatResponse;
}

export async function getAudit(tenantId: string, apiKey: string): Promise<AuditResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/audit/${encodeURIComponent(tenantId)}`, {
    headers: authHeaders(tenantId, apiKey),
    credentials: "include"
  });
  if (!response.ok) throw new Error(`Audit failed: ${response.status}`);
  return (await response.json()) as AuditResponse;
}

export async function getRuntimePolicyStatus(params: {
  tenantId: string;
  apiKey: string;
  appId: string;
}): Promise<RuntimePolicyStatusResponse> {
  const search = new URLSearchParams({
    tenant_id: params.tenantId,
    app_id: params.appId
  });
  const response = await fetch(`${API_BASE_URL}/v1/policies/runtime/status?${search}`, {
    headers: authHeaders(params.tenantId, params.apiKey),
    credentials: "include"
  });
  if (!response.ok) throw new Error(`Runtime policy status failed: ${response.status}`);
  return (await response.json()) as RuntimePolicyStatusResponse;
}

export async function getAuthMe(): Promise<AuthMeResponse | null> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, { credentials: "include" });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Auth check failed: ${response.status}`);
  return (await response.json()) as AuthMeResponse;
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE_URL}/auth/logout`, { method: "POST", credentials: "include" });
}
