import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EventBadges } from "./badge";
import type { Expediente } from "../lib/types";

describe("EventBadges", () => {
  it("identifies an unread changed expediente", () => {
    const item = {
      unread: true, ativo: true, tipo_pendencia_label: "Pendente de resposta",
      latest_event: { kind: "updated", kind_label: "Alterado" },
    } as Expediente;
    render(<EventBadges item={item} />);
    expect(screen.getByText("Não lido")).toBeInTheDocument();
    expect(screen.getByText("Alterado")).toBeInTheDocument();
    expect(screen.getByText("resposta")).toBeInTheDocument();
  });

  it("shows the source when requested by a historical list", () => {
    const item = { unread: false, ativo: true, tipo_pendencia_label: "", latest_event: { kind: "new", kind_label: "Novo" }, source: { code: "trt21", system: "PJe 1º Grau", tribunal: "TRT21" } } as Expediente;
    render(<EventBadges item={item} showSource />);
    expect(screen.getByText("PJe 1º Grau · TRT21")).toBeInTheDocument();
  });
});
