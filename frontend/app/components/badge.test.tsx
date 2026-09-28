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

  it("always shows a distinct, labelled badge for the source", () => {
    const item = { unread: false, ativo: true, tipo_pendencia_label: "", latest_event: { kind: "new", kind_label: "Novo" }, source: { code: "trt21", system: "PJe 1º Grau", tribunal: "TRT21" } } as Expediente;
    render(<EventBadges item={item} />);
    const badge = screen.getByText("PJe 1º Grau · TRT21");
    expect(badge).toBeInTheDocument();
    expect(badge.parentElement).toHaveClass("source-badge-trt21-1g");
  });

  it("uses the dedicated badge style for TRE-RN first degree", () => {
    const item = { unread: false, ativo: true, tipo_pendencia_label: "", latest_event: { kind: "new", kind_label: "Novo" }, source: { code: "tre-rn-1g", system: "PJe 1º Grau", tribunal: "TRE-RN" } } as Expediente;
    render(<EventBadges item={item} />);
    const badge = screen.getByText("PJe 1º Grau · TRE-RN");
    expect(badge.parentElement).toHaveClass("source-badge-tre-rn-1g");
  });

  it("uses the dedicated badge style for TRE-RN second degree", () => {
    const item = { unread: false, ativo: true, tipo_pendencia_label: "", latest_event: { kind: "new", kind_label: "Novo" }, source: { code: "tre-rn-2g", system: "PJe 2º Grau", tribunal: "TRE-RN" } } as Expediente;
    render(<EventBadges item={item} />);
    const badge = screen.getByText("PJe 2º Grau · TRE-RN");
    expect(badge.parentElement).toHaveClass("source-badge-tre-rn-2g");
  });

  it("uses the dedicated badge style for TSE third degree", () => {
    const item = { unread: false, ativo: true, tipo_pendencia_label: "", latest_event: { kind: "new", kind_label: "Novo" }, source: { code: "tse-3g", system: "PJe 3º Grau", tribunal: "TSE" } } as Expediente;
    render(<EventBadges item={item} />);
    const badge = screen.getByText("PJe 3º Grau · TSE");
    expect(badge.parentElement).toHaveClass("source-badge-tse-3g");
  });
});
