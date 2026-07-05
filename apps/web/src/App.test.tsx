import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders Prism web operations UI", () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ status: 401, ok: false }) as Promise<Response>));
    render(<App />);

    expect(screen.getByText("Transform, chat, and audit operations")).toBeInTheDocument();
    expect(screen.getByText("Login with MyDatum")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Transform/i })).toBeInTheDocument();
    expect(screen.getByText("Audit Log")).toBeInTheDocument();
  });
});
