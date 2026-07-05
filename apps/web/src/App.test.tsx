import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders Prism web operations UI", () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ status: 401, ok: false }) as Promise<Response>));
    render(<App />);

    expect(screen.getByText("Transform, chat, and audit operations")).toBeInTheDocument();
    expect(screen.getByText("Login with MyDatum")).toBeInTheDocument();
    expect(screen.getByLabelText("App / domain")).toHaveValue("pulse");
    expect(screen.getByRole("button", { name: /Transform/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Runtime/i })).toBeInTheDocument();
    expect(screen.getByText("Audit Log")).toBeInTheDocument();
  });

  it("uses the selected app domain for transform requests", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      void init;
      const url = new URL(String(input));
      if (url.pathname === "/auth/me") {
        return Promise.resolve({ status: 401, ok: false }) as Promise<Response>;
      }
      if (url.pathname === "/v1/transform") {
        return Promise.resolve(jsonResponse({
          transformed_text: "done",
          detections: [],
          audit_event: { request_id: "req_1", tenant_id: "tenant_dev", event_type: "transform" }
        }));
      }
      if (url.pathname === "/v1/policies/runtime/status") {
        return Promise.resolve(jsonResponse({
          tenant_id: "tenant_dev",
          app_id: url.searchParams.get("app_id"),
          policy_id: "support",
          policy_version: "1",
          policy_source: "enterprise",
          policy_cache_hit: false,
          policy_cache_stale: false,
          policy_provider_latency_ms: 10
        }));
      }
      return Promise.resolve(jsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.change(screen.getByLabelText("App / domain"), { target: { value: "support" } });
    fireEvent.click(screen.getByRole("button", { name: /Transform/i }));

    await waitFor(() => expect(screen.getByText("support v1")).toBeInTheDocument());
    const transformCall = fetchMock.mock.calls.find(([input]) =>
      String(input).includes("/v1/transform")
    );
    expect(JSON.parse(String(transformCall?.[1]?.body))).toEqual(
      expect.objectContaining({ app_id: "support" })
    );
  });
});

function jsonResponse(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(body)
  } as Response;
}
