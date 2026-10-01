export type User = {
  id: number;
  username: string;
  display_name: string;
  theme: "light" | "dark" | "system";
  collection_time: string;
};

export type Event = {
  id: number;
  kind: "new" | "updated" | "resolved";
  kind_label: string;
  changes: Record<string, { before: unknown; after: unknown }>;
  created_at: string;
  read_at: string | null;
};

export type Expediente = {
  id: number;
  identificador_pje: string;
  tipo_pendencia: string | null;
  tipo_pendencia_label: string;
  acao_pje: string | null;
  acao_pje_label: string;
  caixa: string;
  destinatario: string;
  tipo_documento: string;
  meio_comunicacao: string;
  data_expedicao: string | null;
  prazo_texto: string;
  status_prazo_fatal: string;
  status_prazo_fatal_label: string;
  prazo_fatal: string | null;
  ciencia_texto: string;
  capturado_em: string;
  atualizado_em: string;
  ativo: boolean;
  arquivado_em: string | null;
  unread: boolean;
  latest_event: Event | null;
  source: { code: string; system: string; tribunal: string } | null;
  processo: {
    id: number;
    numero: string;
    tribunal: string;
    classe: string;
    assunto: string;
    partes_texto: string;
    unidade_judiciaria: string;
  };
};

export type PipelineStepStatus = "pending" | "running" | "success" | "failed" | "cancelled" | "disabled" | "skipped";

export type PipelineStep = {
  code: string;
  group: string;
  label: string;
  status: PipelineStepStatus;
  run_id: number | null;
  error: string;
  message: string;
};

export type CollectionPipeline = {
  cycle_id: string | null;
  status: "idle" | "running" | "success" | "failed" | "cancelled";
  active: boolean;
  completed: number;
  total: number;
  started_at: string | null;
  finished_at: string | null;
  current_step: string | null;
  steps: PipelineStep[];
};

export type Run = {
  id: number;
  cycle_id: string;
  status: string;
  trigger: string;
  started_at: string | null;
  finished_at: string | null;
  found: number;
  created: number;
  updated: number;
  resolved: number;
  error: string;
  message: string;
  source: string | null;
};

export type Notice = {
  id: number;
  title: string;
  included_by: string;
  included_at: string | null;
  published_at: string | null;
  content_html: string;
  content_text: string;
  links: string[];
  read_at: string | null;
  created_at: string;
  updated_at: string;
  unread: boolean;
  sources: { code: string; system: string; tribunal: string; pje_confirmed_at: string | null }[];
};

export type NoticePage = {
  count: number;
  next: number | null;
  previous: number | null;
  results: Notice[];
};

export type DjenCommunication = {
  id: number;
  api_id: number | null;
  numero_comunicacao: number;
  hash: string;
  data_disponibilizacao: string;
  tribunal: string;
  orgao: string;
  tipo_comunicacao: string;
  meio: string;
  link_inteiro_teor: string;
  tipo_documento: string;
  nome_classe: string;
  codigo_classe: string;
  texto: string;
  read_at: string | null;
  collected_at: string;
  updated_at: string;
  unread: boolean;
  processo: { id: number; numero: string };
  recipients: { name: string; pole: string }[];
  attorneys: { name: string; oab_number: string; oab_state: string }[];
};

export type DjenCommunicationPage = {
  count: number;
  next: number | null;
  previous: number | null;
  results: DjenCommunication[];
};

export type Dashboard = {
  display_name: string;
  today: {
    new: number;
    updated: number;
    resolved: number;
    discardable: number;
    unread: number;
    urgent: number;
    next_week: number;
    calculating: number;
  };
  since_last_visit: {
    since: string | null;
    new: number;
    updated: number;
    resolved: number;
  };
  latest_run: Run | null;
  collection_pipeline: CollectionPipeline;
  recent: Expediente[];
  notices: { unread: number; recent: Notice[] };
};

export type ExpedientePage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Expediente[];
};

export type HistoryItem = { event: Event; expediente: Expediente };
export type HistoryDay = { date: string; new_count: number; items: HistoryItem[] };
export type History = {
  period_start: string;
  period_end: string;
  count: number;
  page: number;
  page_size: number;
  days: HistoryDay[];
};

export type CollectionRun = {
  id: number;
  cycle_id: string;
  status: PipelineStepStatus;
  status_label: string;
  trigger: string;
  trigger_label: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  found: number;
  created: number;
  updated: number;
  resolved: number;
  error: string;
  message: string;
  source: { code: string; system: string; tribunal: string } | null;
};

export type CollectionHistory = {
  period_start: string;
  period_end: string;
  days: { date: string; runs: CollectionRun[] }[];
};
