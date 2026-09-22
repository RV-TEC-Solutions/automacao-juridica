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

export type Run = {
  id: number;
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

export type Dashboard = {
  display_name: string;
  today: {
    new: number;
    updated: number;
    unread: number;
    urgent: number;
    calculating: number;
  };
  since_last_visit: {
    since: string | null;
    new: number;
    updated: number;
    resolved: number;
  };
  latest_run: Run | null;
  recent: Expediente[];
  notices: { unread: number; recent: Notice[] };
};
