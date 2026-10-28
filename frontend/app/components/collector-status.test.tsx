import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { CollectorStatusList } from "./collector-status";
import type { CollectorStatus } from "../lib/types";

afterEach(cleanup);

describe("titulares de coleta", () => {
  it("identifies both attorneys and distinguishes a configured credential from a completed source", () => {
    const collectors: CollectorStatus[] = [
      { code: "murilo", label: "Dr. Murilo", enabled: true, pin_configured: true, totp_configured: true, state: "success", last_success_at: "2026-10-26T10:00:00Z", error: "" },
      { code: "cristiano", label: "Dr. Cristiano", enabled: true, pin_configured: true, totp_configured: true, state: "blocked", last_success_at: null, error: "PIN rejeitado" },
    ];
    render(<CollectorStatusList collectors={collectors} detailed />);
    expect(screen.getByText("Dr. Murilo")).toBeVisible();
    expect(screen.getByText("Dr. Cristiano")).toBeVisible();
    expect(screen.getByText("Credencial suspensa neste ciclo")).toBeVisible();
    expect(screen.getByText("Nenhuma fonte concluída para este titular.")).toBeVisible();
    expect(screen.getByText(/Confira a credencial antes de reexecutar/)).toBeVisible();
    expect(screen.getAllByText(/PIN: configurado · TOTP: configurado/)).toHaveLength(2);
  });
});
