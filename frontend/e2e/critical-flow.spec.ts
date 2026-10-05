import { expect, test } from "@playwright/test";

test("desktop navigation keeps labels on one line without page overflow", async ({ page }) => {
  for (const width of [1536, 1735, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const navigation = page.locator("header nav").first();
    await expect(navigation).toBeVisible();
    for (const label of ["Visão geral", "Publicações DJEN"]) {
      const text = navigation.getByRole("link", { name: label }).locator("span").first();
      await expect(text).toHaveCSS("white-space", "nowrap");
      expect(await text.evaluate((element) => element.getClientRects().length)).toBe(1);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("demo runs without backend and keeps state across pages", async ({ page, request }) => {
  await page.goto("/");
  await expect(page.getByText("Ambiente de demonstração").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /Operador\./ })).toBeVisible();
  const before = await (await request.get("/api/dashboard/")).json();
  expect(before.collection_pipeline.active).toBe(false);

  await page.getByRole("button", { name: "Executar coleta" }).click();
  await expect(page.getByRole("button", { name: "Próxima fonte" })).toBeVisible();
  await page.getByRole("button", { name: "Próxima fonte" }).click();
  const during = await (await request.get("/api/dashboard/")).json();
  expect(during.collection_pipeline.completed).toBe(1);
  await page.getByRole("button", { name: "Concluir coleta" }).click();
  await expect(page.getByRole("button", { name: "Executar coleta" })).toBeVisible();
  const after = await (await request.get("/api/dashboard/")).json();
  expect(after.collection_pipeline.status).toBe("success");
  expect(after.today.new).toBeGreaterThan(before.today.new);

  await page.getByRole("link", { name: "Expedientes", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Expedientes" })).toBeVisible();
  await page.getByRole("link", { name: "Publicações DJEN", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Publicações DJEN" })).toBeVisible();
  await page.getByRole("link", { name: "Histórico", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Histórico" })).toBeVisible();
  await page.getByRole("link", { name: /^Avisos/ }).first().click();
  await expect(page.getByRole("heading", { name: "Avisos" })).toBeVisible();
  await page.getByRole("link", { name: "Estatísticas", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Estatísticas" })).toBeVisible();
  await page.getByRole("link", { name: "Configurações", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Configurações" })).toBeVisible();
  await expect(page.getByText("Fontes conectadas")).toBeVisible();
});

test("reading and exporting use the same fictional records", async ({ page, request }) => {
  const list = await (await request.get("/api/expedientes/?read=unread")).json();
  expect(list.count).toBeGreaterThan(0);
  const id = list.results[0].id;
  await request.post(`/api/expedientes/${id}/read/`);
  const updated = await (await request.get("/api/expedientes/?read=unread")).json();
  expect(updated.count).toBe(list.count - 1);
  const pdf = await request.get("/api/expedientes/export.pdf/?read=unread");
  expect(pdf.ok()).toBe(true);
  expect(pdf.headers()["content-type"]).toBe("application/pdf");
  expect((await pdf.body())?.subarray(0, 8).toString()).toBe("%PDF-1.4");

  await page.goto("/djen");
  await expect(page.getByRole("heading", { name: "Publicações DJEN" })).toBeVisible();
  const publications = await (await request.get("/api/djen/communications/")).json();
  expect(publications.results[0].link_inteiro_teor).toMatch(/^\/demo\/inteiro-teor\//);
  await page.goto(publications.results[0].link_inteiro_teor);
  await expect(page.getByRole("heading", { name: "Inteiro teor fictício" })).toBeVisible();
});

test("settings, notices and publication reading persist locally", async ({ page, request }) => {
  await page.goto("/configuracoes");
  await expect(page.getByRole("heading", { name: "Configurações" })).toBeVisible();
  const source = page.getByRole("switch", { name: /Coleta PJe 1º grau TJRN/ });
  await expect(source).toBeChecked();
  await source.click();
  await expect(source).not.toBeChecked();
  let sources = await (await request.get("/api/sources/")).json();
  expect(sources.find((item: { code: string }) => item.code === "pje-tjrn").enabled).toBe(false);
  await source.click();
  sources = await (await request.get("/api/sources/")).json();
  expect(sources.find((item: { code: string }) => item.code === "pje-tjrn").enabled).toBe(true);

  await page.getByRole("button", { name: "Mudar para tema escuro" }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Mudar para tema claro" }).click();

  const notices = await (await request.get("/api/notices/?read=unread")).json();
  if (notices.count) {
    await request.post(`/api/notices/${notices.results[0].id}/read/`);
    expect((await (await request.get("/api/notices/?read=unread")).json()).count).toBe(notices.count - 1);
  }
  const publications = await (await request.get("/api/djen/communications/?read=unread")).json();
  if (publications.count) {
    await request.post(`/api/djen/communications/${publications.results[0].id}/read/`);
    expect((await (await request.get("/api/djen/communications/?read=unread")).json()).count).toBe(publications.count - 1);
  }
});
