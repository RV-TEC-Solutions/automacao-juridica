import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DjenList } from "./djen-list";
import type { DjenCommunication } from "../lib/types";

describe("DjenList attorney badges", () => {
  afterEach(cleanup);
  it("identifies both attorneys from the publication without duplicating badges", () => {
    const item = {
      id: 1, processo: { numero: "123" }, tribunal: "TJRN", data_disponibilizacao: "2026-10-28",
      recipients: [], attorneys: [{ name: "CRISTIANO LUIZ SILVA" }, { name: "MURILO MARIZ DE FARIA NETO" }, { name: "Cristiano Luiz Silva" }],
    } as unknown as DjenCommunication;
    render(<DjenList items={[item]} onSelect={vi.fn()} />);
    expect(screen.getAllByText("Dr. Cristiano")).toHaveLength(1);
    expect(screen.getAllByText("Dr. Murilo")).toHaveLength(1);
  });

  it("does not attribute an unrelated attorney", () => {
    const item = {
      id: 2, processo: { numero: "456" }, tribunal: "TJRN", data_disponibilizacao: "2026-10-28",
      recipients: [], attorneys: [{ name: "MURILO OUTRO" }],
    } as unknown as DjenCommunication;
    render(<DjenList items={[item]} onSelect={vi.fn()} />);
    expect(screen.queryByText("Dr. Murilo")).not.toBeInTheDocument();
    expect(screen.queryByText("Dr. Cristiano")).not.toBeInTheDocument();
  });
});
