import type { CollectionRun, DjenCommunication, Event, Expediente, Notice, User } from "../lib/types";

export type DemoSource = { code: string; system: string; tribunal: string; enabled: boolean; group: string };
export type DemoState = {
  seedDay: string;
  user: User;
  sources: DemoSource[];
  expedientes: Expediente[];
  publications: DjenCommunication[];
  notices: Notice[];
  runs: CollectionRun[];
  collection: { active: boolean; current: number; codes: string[]; cycleId: string | null };
  lastVisit: string | null;
};

export const SOURCE_DEFINITIONS: Omit<DemoSource, "enabled">[] = [
  { code: "pje-tjrn", system: "PJe 1º grau", tribunal: "TJRN", group: "Justiça Estadual" },
  { code: "pje2g-tjrn", system: "PJe 2º grau", tribunal: "TJRN", group: "Justiça Estadual" },
  { code: "tre-rn-1g", system: "PJe 1º grau", tribunal: "TRE-RN", group: "Justiça Eleitoral" },
  { code: "tre-rn-2g", system: "PJe 2º grau", tribunal: "TRE-RN", group: "Justiça Eleitoral" },
  { code: "tse-3g", system: "PJe 3º grau", tribunal: "TSE", group: "Justiça Eleitoral" },
  { code: "trt21", system: "PJe 1º grau", tribunal: "TRT21", group: "Justiça do Trabalho" },
  { code: "trt21-2g", system: "PJe 2º grau", tribunal: "TRT21", group: "Justiça do Trabalho" },
  { code: "trf5-2g-tru", system: "PJe 2º grau", tribunal: "TRF5", group: "Justiça Federal" },
  { code: "varas-justica-comum", system: "PJe Justiça Comum", tribunal: "TRF5", group: "Justiça Federal" },
  { code: "jef-5-regiao", system: "PJe JEF", tribunal: "TRF5", group: "Justiça Federal" },
  { code: "trs-5-regiao", system: "PJe Turmas Recursais", tribunal: "TRF5", group: "Justiça Federal" },
  { code: "tru-5-regiao", system: "PJe TRU", tribunal: "TRF5", group: "Justiça Federal" },
  { code: "djen", system: "DJEN", tribunal: "CNJ", group: "Diário Nacional" },
];

export function localDay(value = new Date()) {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: "America/Fortaleza", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(value);
  const map = Object.fromEntries(parts.map(({ type, value: part }) => [type, part]));
  return `${map.year}-${map.month}-${map.day}`;
}

export function dayOffset(day: string, delta: number) {
  const date = new Date(`${day}T12:00:00-03:00`);
  date.setUTCDate(date.getUTCDate() + delta);
  return localDay(date);
}

export function at(day: string, hour: number, minute = 0) {
  return `${day}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00-03:00`;
}

const subject = ["Cumprimento de sentença", "Obrigação de fazer", "Direito administrativo", "Recurso cível", "Procedimento comum", "Execução fiscal", "Tutela de urgência", "Apelação cível"];
const classes = ["Procedimento Comum Cível", "Cumprimento de Sentença", "Execução Fiscal", "Recurso Inominado", "Apelação Cível"];
const documentTypes = ["Intimação", "Intimação", "Intimação", "Intimação", "Sentença", "Intimação de Pauta", "Acórdão", "Citação", "Ato Ordinatório", "Decisão"];
const channels = ["Diário Eletrônico", "Diário Eletrônico", "Diário Eletrônico", "Expedição eletrônica", "Expedição eletrônica", "Correios"];

function event(id: number, kind: Event["kind"], date: string, unread = true): Event {
  return { id, kind, kind_label: { new: "Novo", updated: "Alterado", resolved: "Resolvido" }[kind], changes: kind === "updated" ? { prazo_texto: { before: "10 dias", after: "15 dias" } } : {}, created_at: date, read_at: unread ? null : date };
}

function processNumber(i: number, year: number, tribunal: string) {
  // Número com aparência CNJ, mas dígito verificador 00 intencionalmente inválido.
  const segment = tribunal === "TJRN" ? "8.20" : tribunal === "TRE-RN" ? "6.20" : tribunal === "TSE" ? "6.00" : tribunal === "TRT21" ? "5.21" : "4.05";
  return `${String(9000000 + i).padStart(7, "0")}-00.${year}.${segment}.${String(9000 + i % 100).padStart(4, "0")}`;
}

export function createSeed(day = localDay()): DemoState {
  const year = Number(day.slice(0, 4));
  const sources = SOURCE_DEFINITIONS.map((source) => ({ ...source, enabled: true }));
  const expedientes: Expediente[] = Array.from({ length: 96 }, (_, index) => {
    const i = index + 1;
    const source = sources[index % 12];
    const collectedDay = dayOffset(day, -(index % 25));
    const kind: Event["kind"] = i % 7 === 0 ? "updated" : i % 9 === 0 ? "resolved" : "new";
    const active = kind !== "resolved";
    const deadline = i % 9 === 0 ? "sem_prazo" : i % 8 === 0 ? "em_calculo" : "calculado";
    const pending = i % 7 === 0 ? "nao_identificada" : i % 5 === 0 ? "ciencia" : "resposta";
    const date = at(collectedDay, 6 + i % 3, i % 59);
    return {
      id: i, identificador_pje: String(80000000 + i), tipo_pendencia: pending,
      tipo_pendencia_label: { resposta: "Pendente de resposta", ciencia: "Pendente de ciência", nao_identificada: "Não identificada" }[pending],
      acao_pje: pending === "ciencia" ? "tomar_ciencia" : "responder",
      acao_pje_label: pending === "ciencia" ? "Tomar ciência" : "Responder",
      caixa: i % 2 ? "Aguardando manifestação" : "Pendentes de ciência",
      destinatario: `Parte destinatária ${String(i).padStart(2, "0")}`,
      tipo_documento: documentTypes[index % documentTypes.length],
      meio_comunicacao: channels[index % channels.length],
      data_expedicao: at(dayOffset(collectedDay, -1), 14, 20),
      prazo_texto: deadline === "sem_prazo" ? "Sem prazo" : deadline === "em_calculo" ? "Em cálculo" : i % 4 === 0 ? "15 dias" : "10 dias",
      status_prazo_fatal: deadline,
      status_prazo_fatal_label: { calculado: "Calculado", em_calculo: "Em cálculo", sem_prazo: "Sem prazo" }[deadline],
      prazo_fatal: deadline === "calculado" ? at(dayOffset(day, i % 11 - 2), 23, 59) : null,
      ciencia_texto: "", capturado_em: date, atualizado_em: date, ativo: active,
      arquivado_em: active ? null : date, unread: i % 4 !== 0,
      latest_event: event(i, kind, date, i % 4 !== 0),
      source: { code: source.code, system: source.system, tribunal: source.tribunal },
      processo: { id: i, numero: processNumber(i, year, source.tribunal), tribunal: source.tribunal,
        classe: classes[index % classes.length], assunto: subject[index % subject.length],
        partes_texto: `Parte autora ${String(i).padStart(2, "0")} × Parte ré ${String(i).padStart(2, "0")}`,
        unidade_judiciaria: `${i % 5 + 1}ª Vara de Demonstração` },
    };
  });
  const publications: DjenCommunication[] = Array.from({ length: 23 }, (_, index) => {
    const i = index + 1;
    const collectedDay = dayOffset(day, -(index % 10));
    const tribunal = ["TJRN", "TRF5", "TRT21", "TRE-RN"][index % 4];
    const readAt = i % 3 === 0 ? at(collectedDay, 12) : null;
    return {
      id: i, api_id: null, numero_comunicacao: 9900000 + i, hash: `DEMO-${i}`,
      data_disponibilizacao: collectedDay, tribunal, orgao: `${i % 5 + 1}ª Unidade Judiciária de Demonstração`,
      tipo_comunicacao: i % 4 === 0 ? "Citação" : "Intimação", meio: "Diário de Justiça Eletrônico Nacional",
      link_inteiro_teor: `/demo/inteiro-teor/${i}`, tipo_documento: i % 4 === 0 ? "Citação" : "Intimação",
      nome_classe: classes[index % classes.length], codigo_classe: "DEMO", texto: `Comunicação fictícia para fins de demonstração. Processo ${processNumber(i + 100, year, tribunal)}. Parte autora ${String(i).padStart(2, "0")} e Parte ré ${String(i).padStart(2, "0")}. Prazo de 10 dias para manifestação.`,
      read_at: readAt, collected_at: at(collectedDay, 7, i % 59), updated_at: at(collectedDay, 7, i % 59), unread: !readAt,
      processo: { id: i + 100, numero: processNumber(i + 100, year, tribunal) },
      recipients: [{ name: `Parte destinatária ${String(i).padStart(2, "0")}`, pole: "Polo passivo" }],
      attorneys: [{ name: "Representante processual", oab_number: "", oab_state: "" }],
    };
  });
  const notices: Notice[] = Array.from({ length: 5 }, (_, index) => {
    const i = index + 1;
    const published = dayOffset(day, -i);
    return { id: i, title: ["Manutenção programada no sistema", "Atualização da consulta processual", "Orientação sobre indisponibilidade", "Novo horário de atendimento", "Comunicado operacional"][index],
      included_by: "Administração do sistema", included_at: at(published, 9), published_at: published,
      content_html: "<p>Comunicado fictício para demonstração. Consulte as informações operacionais neste painel.</p>",
      content_text: "Comunicado fictício para demonstração.", links: [],
      read_at: i > 2 ? at(published, 10) : null, created_at: at(published, 9), updated_at: at(published, 9), unread: i <= 2,
      sources: [{ code: sources[index].code, system: sources[index].system, tribunal: sources[index].tribunal, pje_confirmed_at: null }],
    };
  });
  const runs: CollectionRun[] = sources.slice(0, 12).map((source, index) => {
    const runDay = dayOffset(day, -(index % 8 + 1));
    const failed = index === 4;
    return { id: index + 1, cycle_id: `demo-historico-${index}`, status: failed ? "failed" : "success",
      status_label: failed ? "Erro" : "Sucesso", trigger: "scheduled", trigger_label: "Agendada",
      created_at: at(runDay, 6), started_at: at(runDay, 6, index), finished_at: at(runDay, 6, index + 2), duration_seconds: 120,
      found: failed ? 0 : 8 + index % 5, created: failed ? 0 : 2 + index % 3, updated: failed ? 0 : index % 2,
      resolved: failed ? 0 : index % 3, error: failed ? "Consulta simulada interrompida. A fonte foi processada na coleta seguinte." : "",
      message: failed ? "" : "Coleta fictícia concluída.", source: { code: source.code, system: source.system, tribunal: source.tribunal } };
  });
  return { seedDay: day, user: { id: 1, username: "demo", display_name: "Operador Demo", theme: "light", collection_time: "06:00" },
    sources, expedientes, publications, notices, runs, collection: { active: false, current: -1, codes: [], cycleId: null }, lastVisit: null };
}
