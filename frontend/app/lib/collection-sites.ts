// Portais de entrada usados pelos coletores; perfis do TRF5 compartilham o portal.
const tre = "https://www.tre-rn.jus.br/servicos-judiciais/processos/processo-judicial-eletronico";
const trf = "https://www.trf5.jus.br/index.php/pje#container";

const sites = new Map<string, { name: string; href: string }>([
  ["pje-tjrn", { name: "TJRN · 1º Grau", href: "https://pje1g.tjrn.jus.br/pje/Painel/painel_usuario/advogado.seam" }],
  ["pje2g-tjrn", { name: "TJRN · 2º Grau", href: "https://pje2g.tjrn.jus.br/pje/Painel/painel_usuario/advogado.seam" }],
  ["tre-rn-1g", { name: "TRE-RN · 1º Grau", href: tre }],
  ["tre-rn-2g", { name: "TRE-RN · 2º Grau", href: tre }],
  ["tse-3g", { name: "TSE · 3º Grau", href: "https://www.tse.jus.br/servicos-judiciais/processos/pje" }],
  ["trt21", { name: "TRT21 · 1º Grau", href: "https://pje.trt21.jus.br/primeirograu/login.seam" }],
  ["trt21-2g", { name: "TRT21 · 2º Grau", href: "https://pje.trt21.jus.br/segundograu/login.seam" }],
  ["trf5-2g-tru", { name: "TRF5 · 2º Grau / TRU", href: trf }],
  ["varas-justica-comum", { name: "TRF5 · Varas federais", href: trf }],
  ["jef-5-regiao", { name: "TRF5 · JEF", href: trf }],
  ["trs-5-regiao", { name: "TRF5 · Turmas recursais", href: trf }],
  ["tru-5-regiao", { name: "TRF5 · TRU — perfil alternativo", href: trf }],
  ["djen", { name: "DJEN", href: "https://comunica.pje.jus.br/" }],
]);

export function getCollectionSite(code: string) {
  return sites.get(code);
}
