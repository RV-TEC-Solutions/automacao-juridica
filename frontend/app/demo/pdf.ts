function encoded(value: string) {
  return Buffer.from(value.replace(/[\u2013\u2014]/g, "-").replace(/\u00d7/g, "x").replace(/[^\u0009\u000a\u000d\u0020-\u007e\u00a0-\u00ff]/g, "?"), "latin1");
}

function escapePdf(value: string) {
  return value.replaceAll("\\", "\\\\").replaceAll("(", "\\(").replaceAll(")", "\\)");
}

export function demoPdf(title: string, lines: string[]) {
  const pages: string[][] = [];
  for (let i = 0; i < Math.max(1, lines.length); i += 42) pages.push(lines.slice(i, i + 42));
  const objects: Buffer[] = [];
  const add = (content: string | Buffer) => { objects.push(typeof content === "string" ? encoded(content) : content); return objects.length; };
  const catalog = add("");
  const pagesId = add("");
  const font = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
  const pageIds: number[] = [];
  pages.forEach((rows, pageIndex) => {
    const content = ["BT", "/F1 17 Tf", "50 795 Td", `(${escapePdf(title)}) Tj`, "0 -28 Td", "/F1 10 Tf", "(AMBIENTE DE DEMONSTRAÇÃO - DADOS FICTÍCIOS) Tj", "0 -28 Td"];
    rows.forEach((row) => { content.push(`(${escapePdf(row.slice(0, 105))}) Tj`, "0 -16 Td"); });
    content.push("0 -12 Td", `(${escapePdf(`Página ${pageIndex + 1} de ${pages.length}`)}) Tj`, "ET");
    const stream = encoded(content.join("\n"));
    const streamId = add(Buffer.concat([encoded(`<< /Length ${stream.length} >>\nstream\n`), stream, encoded("\nendstream")]));
    pageIds.push(add(`<< /Type /Page /Parent ${pagesId} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 ${font} 0 R >> >> /Contents ${streamId} 0 R >>`));
  });
  objects[catalog - 1] = encoded(`<< /Type /Catalog /Pages ${pagesId} 0 R >>`);
  objects[pagesId - 1] = encoded(`<< /Type /Pages /Kids [${pageIds.map((id) => `${id} 0 R`).join(" ")}] /Count ${pageIds.length} >>`);
  const chunks: Buffer[] = [encoded("%PDF-1.4\n%\xff\xff\xff\xff\n")];
  const offsets = [0];
  let length = chunks[0].length;
  objects.forEach((object, index) => {
    offsets.push(length);
    const chunk = Buffer.concat([encoded(`${index + 1} 0 obj\n`), object, encoded("\nendobj\n")]);
    chunks.push(chunk); length += chunk.length;
  });
  const xref = length;
  chunks.push(encoded(`xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`));
  offsets.slice(1).forEach((offset) => chunks.push(encoded(`${String(offset).padStart(10, "0")} 00000 n \n`)));
  chunks.push(encoded(`trailer\n<< /Size ${objects.length + 1} /Root ${catalog} 0 R >>\nstartxref\n${xref}\n%%EOF`));
  return Buffer.concat(chunks);
}
