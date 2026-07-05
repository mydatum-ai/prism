import { Activity, Bot, Database, Play, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import {
  chatMock,
  getAudit,
  getAuthMe,
  getRuntimePolicyStatus,
  loginUrl,
  logout,
  transformText,
  type AuditResponse,
  type AuthMeResponse,
  type ChatResponse,
  type RuntimePolicyStatusResponse,
  type TransformResponse
} from "./api";

const defaultPrompt = "Maria Santos emailed maria@example.com about the flood near 12 Rizal Street.";

export function App() {
  const [tenantId, setTenantId] = useState("tenant_dev");
  const [apiKey, setApiKey] = useState("dev");
  const [appId, setAppId] = useState("pulse");
  const [prompt, setPrompt] = useState(defaultPrompt);
  const [transform, setTransform] = useState<TransformResponse | null>(null);
  const [chat, setChat] = useState<ChatResponse | null>(null);
  const [audit, setAudit] = useState<AuditResponse | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimePolicyStatusResponse | null>(null);
  const [auth, setAuth] = useState<AuthMeResponse | null>(null);
  const [status, setStatus] = useState("Ready");

  const sessionId = "web-session";
  const appAuditEvents = (audit?.events ?? []).filter((event) => event.app_id === appId);

  useEffect(() => {
    void getAuthMe()
      .then((result) => {
        setAuth(result);
        if (result?.account.tenant_id) setTenantId(result.account.tenant_id);
      })
      .catch(() => setAuth(null));
  }, []);

  async function signOut() {
    await logout();
    setAuth(null);
  }

  async function runTransform() {
    setStatus("Transforming");
    const result = await transformText({ tenantId, apiKey, appId, sessionId, text: prompt });
    setTransform(result);
    await refreshRuntimeStatus();
    setStatus("Transform complete");
  }

  async function runChat() {
    setStatus("Running chat");
    const result = await chatMock({ tenantId, apiKey, appId, sessionId, text: prompt });
    setChat(result);
    await refreshRuntimeStatus();
    setStatus("Chat complete");
  }

  async function refreshAudit() {
    setStatus("Loading audit");
    const result = await getAudit(tenantId, apiKey);
    setAudit(result);
    setStatus("Audit loaded");
  }

  async function refreshRuntimeStatus() {
    const result = await getRuntimePolicyStatus({ tenantId, apiKey, appId });
    setRuntimeStatus(result);
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={26} />
          <div>
            <h1>Prism</h1>
            <span>Privacy Gateway</span>
          </div>
        </div>
        <label>
          Tenant
          <input value={tenantId} onChange={(event) => setTenantId(event.target.value)} />
        </label>
        <label>
          API key
          <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
        </label>
        <label>
          App / domain
          <input
            value={appId}
            onChange={(event) => {
              setAppId(event.target.value);
              setRuntimeStatus(null);
            }}
          />
        </label>
        <div className="auth-panel">
          <span>{auth ? auth.account.email || auth.account.subject : "Not signed in with MyDatum"}</span>
          {auth ? (
            <button type="button" onClick={signOut}>Logout</button>
          ) : (
            <a href={loginUrl}>Login with MyDatum</a>
          )}
        </div>
      </aside>

      <section className="workspace">
        <header className="toolbar">
          <div>
            <p>Gateway on port 8004</p>
            <h2>Transform, chat, and audit operations</h2>
          </div>
          <strong>{status}</strong>
        </header>

        <section className="panel transform-panel">
          <div>
            <h3>Prompt</h3>
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
            <div className="actions">
              <button type="button" onClick={runTransform}><Play size={18} /> Transform</button>
              <button type="button" onClick={runChat}><Bot size={18} /> Chat mock</button>
              <button type="button" onClick={refreshAudit}><Database size={18} /> Audit</button>
              <button type="button" onClick={refreshRuntimeStatus}><Activity size={18} /> Runtime</button>
            </div>
          </div>
          <div className="result-grid">
            <Result title="Transformed" value={transform?.transformed_text ?? "No transform yet"} />
            <Result title="Chat response" value={chat?.message.content ?? "No chat response yet"} />
          </div>
        </section>

        <section className="metric-grid">
          <article>
            <Activity size={18} />
            <span>Detections</span>
            <strong>{transform?.detections.length ?? 0}</strong>
          </article>
          <article>
            <Database size={18} />
            <span>Audit events</span>
            <strong>{appAuditEvents.length}</strong>
          </article>
          <article>
            <ShieldCheck size={18} />
            <span>Runtime policy</span>
            <strong>{runtimeStatus?.policy_source ?? "-"}</strong>
          </article>
          <article>
            <Activity size={18} />
            <span>Cache</span>
            <strong>{runtimeCacheLabel(runtimeStatus)}</strong>
          </article>
        </section>

        <section className="panel runtime-panel">
          <h3>Runtime Policy</h3>
          <div className="runtime-grid">
            <Metric label="App" value={appId} />
            <Metric label="Policy" value={runtimePolicyLabel(runtimeStatus)} />
            <Metric label="Source" value={runtimeStatus?.policy_source ?? "-"} />
            <Metric label="Latency" value={runtimeLatencyLabel(runtimeStatus)} />
          </div>
        </section>

        <section className="panel">
          <h3>Audit Log</h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Event</th><th>App</th><th>Session</th><th>Request</th></tr></thead>
              <tbody>
                {appAuditEvents.map((event) => (
                  <tr key={event.request_id}>
                    <td>{event.event_type}</td>
                    <td>{event.app_id}</td>
                    <td>{event.session_id}</td>
                    <td>{event.request_id.slice(0, 12)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}

function Result({ title, value }: { title: string; value: string }) {
  return <article className="result"><span>{title}</span><p>{value}</p></article>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric-line"><span>{label}</span><strong>{value}</strong></div>;
}

function runtimePolicyLabel(status: RuntimePolicyStatusResponse | null): string {
  if (!status) return "-";
  return `${status.policy_id} v${status.policy_version}`;
}

function runtimeCacheLabel(status: RuntimePolicyStatusResponse | null): string {
  if (!status) return "-";
  if (status.policy_cache_stale) return "stale";
  return status.policy_cache_hit ? "hit" : "miss";
}

function runtimeLatencyLabel(status: RuntimePolicyStatusResponse | null): string {
  if (!status) return "-";
  return `${Math.round(status.policy_provider_latency_ms)}ms`;
}
