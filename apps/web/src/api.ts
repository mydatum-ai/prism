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

const authHeaders = (tenantId: string, apiKey: string) => ({
  "Content-Type": "application/json",
  "X-Prism-Tenant": tenantId,
  "X-Prism-API-Key": apiKey
});

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
    headers: authHeaders(tenantId, apiKey)
  });
  if (!response.ok) throw new Error(`Audit failed: ${response.status}`);
  return (await response.json()) as AuditResponse;
}
