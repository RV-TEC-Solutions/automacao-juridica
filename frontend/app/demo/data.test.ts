import { describe, expect, it } from "vitest";
import { advanceCollection, dashboard, filteredExpedientes, filteredPublications, startCollection, statistics } from "./data";
import { demoPdf } from "./pdf";
import { createSeed, dayOffset } from "./seed";

const day = "2026-10-04";

describe("cenário de demonstração", () => {
  it("uses relative dates and contains only fictional identifiers", () => {
    const state = createSeed(day);
    expect(state.seedDay).toBe(day);
    expect(dayOffset(day, -1)).toBe("2026-10-03");
    expect(state.expedientes[0].processo.numero).toMatch(/^9\d{6}-00\.2026/);
    expect(state.expedientes[0].processo.partes_texto).toContain("Parte autora");
    expect(state.publications[0].recipients[0].name).toContain("Parte destinatária");
    expect(state.publications.every((item) => item.link_inteiro_teor.startsWith("/demo/"))).toBe(true);
  });

  it("keeps dashboard counts, filters and collection changes consistent", () => {
    const state = createSeed(day);
    const before = dashboard(state);
    const today = new URLSearchParams({ event_kind: "new", date_from: day, date_to: day });
    expect(filteredExpedientes(state, today)).toHaveLength(before.today.new);
    startCollection(state);
    expect(dashboard(state).collection_pipeline.active).toBe(true);
    advanceCollection(state);
    expect(dashboard(state).collection_pipeline.completed).toBe(1);
    advanceCollection(state, true);
    const after = dashboard(state);
    expect(after.collection_pipeline.active).toBe(false);
    expect(after.collection_pipeline.completed).toBe(after.collection_pipeline.total);
    expect(after.today.new).toBeGreaterThan(before.today.new);
    expect(filteredExpedientes(state, today)).toHaveLength(after.today.new);
    expect(filteredPublications(state, new URLSearchParams({ collected_from: day, collected_to: day })).length).toBeGreaterThan(0);
    expect(statistics(state, 7).totals.current).toBeGreaterThan(before.today.new);
  });

  it("exports a valid PDF header with a demo label", () => {
    const bytes = demoPdf("Expedientes", ["Parte autora 01"]);
    expect(bytes.subarray(0, 8).toString()).toBe("%PDF-1.4");
    expect(bytes.toString("latin1")).toContain("xref\n");
    expect(bytes.toString("latin1")).toContain("%%EOF");
    expect(bytes.toString("latin1")).toContain("AMBIENTE DE DEMONSTRAÇÃO");
    expect(bytes.toString("latin1")).toContain("Parte autora 01");
  });
});
