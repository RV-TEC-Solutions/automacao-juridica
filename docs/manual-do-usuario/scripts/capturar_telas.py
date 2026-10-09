"""Captura a interface real com API fictícia isolada; não acessa o backend.

Uso: .venv/bin/python docs/manual-do-usuario/scripts/capturar_telas.py
Requer frontend ativo em http://localhost:3002 (ou MANUAL_BASE_URL) e Playwright/Chromium.
"""
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("MANUAL_BASE_URL", "http://localhost:3002")
STAMP = "2026-10-08T09:00:00-03:00"
USER = dict(id=999, username="demonstracao", display_name="Usuário de demonstração", theme="light", collection_time="06:00")
SOURCES = [
    ("pje-tjrn", "TJRN", "1º Grau"), ("pje2g-tjrn", "TJRN", "2º Grau"),
    ("tre-rn-1g", "Justiça Eleitoral", "TRE-RN · 1º Grau"), ("tre-rn-2g", "Justiça Eleitoral", "TRE-RN · 2º Grau"),
    ("tse-3g", "Justiça Eleitoral", "TSE · 3º Grau"), ("trt21", "TRT21", "1º Grau"),
    ("trt21-2g", "TRT21", "2º Grau"), ("trf5-2g-tru", "TRF5", "2º Grau / TRU"),
    ("varas-justica-comum", "TRF5", "Varas federais"), ("jef-5-regiao", "TRF5", "JEF · 5ª Região"),
    ("trs-5-regiao", "TRF5", "Turmas recursais"), ("tru-5-regiao", "TRF5", "TRU · perfil alternativo"),
    ("djen", "DJEN", "Publicações DJEN"),
]
SOURCE_SETTINGS = [dict(code=c, system="DJEN" if c=="djen" else "PJe "+l.replace("TRE-RN · ","").replace("TSE · ",""),
    tribunal="Nacional" if c=="djen" else "TSE" if c=="tse-3g" else "TRE-RN" if c.startswith("tre-rn") else g,enabled=True) for c,g,l in SOURCES]
ITEM = dict(id=901, identificador_pje="DEMO-001", tipo_pendencia="resposta", tipo_pendencia_label="Pendente de resposta",
    acao_pje="responder", acao_pje_label="Responder", caixa="Pendentes", destinatario="Parte demonstrativa",
    tipo_documento="Intimação", meio_comunicacao="Sistema", data_expedicao=STAMP, prazo_texto="5 dias",
    status_prazo_fatal="calculado", status_prazo_fatal_label="Calculado", prazo_fatal="2026-10-09T18:00:00-03:00",
    ciencia_texto="", capturado_em=STAMP, atualizado_em=STAMP, ativo=True, arquivado_em=None, unread=True,
    source=dict(code="pje-tjrn", system="PJe 1º Grau", tribunal="TJRN"),
    processo=dict(id=901, numero="0800001-00.2026.8.20.0001", tribunal="TJRN", classe="Procedimento comum",
    assunto="Exemplo fictício · obrigação de fazer", partes_texto="Parte demonstrativa A × Parte demonstrativa B", unidade_judiciaria="Vara de demonstração"),
    latest_event=dict(id=901, kind="updated", kind_label="Alterado", changes={"prazo_fatal":dict(before="08/10/2026 18:00", after="09/10/2026 18:00")}, created_at=STAMP, read_at=None))
NEW = json.loads(json.dumps(ITEM))
NEW.update(id=902, status_prazo_fatal="em_calculo", status_prazo_fatal_label="Em cálculo", prazo_fatal=None)
NEW["processo"]["numero"]="0800002-00.2026.8.20.0001"
NEW["latest_event"].update(kind="new", kind_label="Novo", changes={})
PUB = dict(id=903, api_id=903, numero_comunicacao=101, hash="demonstracao", data_disponibilizacao="2026-10-07",
    tribunal="TJRN", orgao="Vara de demonstração", tipo_comunicacao="Intimação", meio="D", link_inteiro_teor="https://comunica.pje.jus.br/",
    tipo_documento="Intimação", nome_classe="Procedimento comum", codigo_classe="7",
    texto="PUBLICAÇÃO FICTÍCIA PARA O MANUAL.\n\nIntimem-se as partes para manifestação. Consulte o inteiro teor na plataforma de origem. Este texto não corresponde a um processo real.",
    read_at=None, collected_at=STAMP, updated_at=STAMP, unread=True, processo=dict(id=903, numero="0800003-00.2026.8.20.0001"),
    recipients=[dict(name="Parte demonstrativa A", pole="Ativo"), dict(name="Parte demonstrativa B", pole="Passivo")],
    attorneys=[dict(name="Advogado de demonstração", oab_number="00000", oab_state="RN")])
NOTICE = dict(id=904, title="Aviso fictício · manutenção programada", included_by="Equipe de demonstração", included_at=STAMP,
    published_at=STAMP, content_html="<p>Exemplo de comunicado institucional coletado no PJe.</p><p>Confira aqui o texto e as origens do aviso.</p>",
    content_text="Exemplo de comunicado", links=[], read_at=None, created_at=STAMP, updated_at=STAMP, unread=True,
    sources=[dict(code="pje-tjrn", system="PJe 1º Grau · TJRN", tribunal="TJRN", pje_confirmed_at=STAMP)])

async def main():
    ROOT.joinpath("imagens").mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        context = await browser.new_context(viewport=dict(width=1440, height=900), device_scale_factor=1, timezone_id="America/Fortaleza", locale="pt-BR")
        authenticated = False
        async def api(route):
            nonlocal authenticated
            path = route.request.url.split("/api/")[-1].split("?")[0]
            method = route.request.method
            payload = {}
            status = 200
            if path == "auth/me/":
                payload = USER if authenticated else dict(detail="auth")
                status = 200 if authenticated else 403
            elif path == "auth/login/":
                authenticated = True
                payload = USER
            elif path == "auth/csrf/": payload = dict(detail="ok")
            elif path == "dashboard/":
                payload = dict(display_name=USER["display_name"], today=dict(new=1, updated=1, unread=2, urgent=1, next_week=1, calculating=1, resolved=0, discardable=1),
                    since_last_visit=dict(since=None,new=1,updated=1,resolved=0), recent=[ITEM,NEW], notices=dict(unread=1,recent=[NOTICE]),
                    latest_run=dict(id=1, status="success"), collection_pipeline=dict(cycle_id="demo",status="failed",active=False,completed=12,total=13,
                    started_at=STAMP,finished_at="2026-10-08T09:08:00-03:00",current_step=None,
                    steps=[dict(code=c,group=g,label=l,status="failed" if c=="tre-rn-1g" else "success",run_id=i+1,
                    error="Exemplo: serviço do tribunal indisponível." if c=="tre-rn-1g" else "",message="") for i,(c,g,l) in enumerate(SOURCES)]))
            elif path == "automation/token-status/": payload = dict(available=True,message="Token de demonstração disponível")
            elif path == "expedientes/": payload = dict(count=2,next=None,previous=None,results=[ITEM,NEW])
            elif path == "history/": payload = dict(period_start="2026-09-09",period_end="2026-10-08",count=1,page=1,page_size=50,days=[dict(date="2026-10-08",new_count=1,items=[dict(event=NEW["latest_event"],expediente=NEW)])])
            elif path == "djen/communications/": payload = dict(count=1,next=None,previous=None,results=[PUB])
            elif path == "djen/history/": payload = dict(count=1,page=1,page_size=20,days=[dict(date="2026-10-08",items=[PUB])])
            elif path == "notices/": payload = dict(count=1,next=None,previous=None,results=[NOTICE])
            elif path == "settings/": payload = dict(display_name=USER["display_name"],theme="light",collection_time="06:00",timezone="America/Fortaleza",credential_status=dict(credential_file=True,pin=True,totp=True))
            elif path == "sources/": payload = SOURCE_SETTINGS
            elif path == "automation/history/":
                runs = [dict(id=i+1,cycle_id="demo",status="failed" if i else "success",status_label="Falhou" if i else "Concluída",trigger="manual",trigger_label="Manual",
                    created_at=STAMP,started_at=STAMP,finished_at="2026-10-08T09:02:00-03:00",duration_seconds=120,found=0 if i else 2,created=0 if i else 1,updated=0 if i else 1,resolved=0,
                    error="Exemplo: serviço do tribunal indisponível. Tente reexecutar a fonte após normalização." if i else "",message="",source=dict(code=c,system=l,tribunal=g)) for i,(c,g,l) in enumerate(SOURCES[:2])]
                payload=dict(period_start="2026-09-09",period_end="2026-10-08",days=[dict(date="2026-10-08",runs=runs)])
            elif path == "statistics/": payload=dict(period=7,time_saved=dict(total_seconds=28800,today_seconds=3600,source_days=24,items=40,tabs=20),
                totals=dict(current=12,previous=10,change_percent=20,new=7,updated=4,resolved=1),
                timeline=[dict(day=f"2026-10-{d:02}",kind=k,total=n) for d,k,n in [(2,"new",2),(3,"new",1),(4,"updated",1),(5,"new",3),(6,"resolved",1),(7,"updated",3),(8,"new",1)]],
                pending_distribution=[dict(tipo_pendencia="ciencia",total=1),dict(tipo_pendencia="resposta",total=1)],deadline_distribution=[dict(status_prazo_fatal="calculado",total=1),dict(status_prazo_fatal="em_calculo",total=1)])
            elif path.endswith("/read/"):
                payload = {**PUB,"unread":False,"read_at":STAMP} if path.startswith("djen/") else dict(events_marked=1)
            else:
                raise RuntimeError(f"Endpoint inesperado na captura: {method} {path}")
            await route.fulfill(status=status,json=payload)
        await context.route("**/api/**", api)
        page = await context.new_page()
        errors=[]
        page.on("pageerror",lambda error: errors.append(str(error)))
        await page.clock.set_fixed_time("2026-10-08T12:15:00Z")

        async def shot(name, locators, clip=None):
            await page.evaluate("document.querySelectorAll('[data-manual]').forEach(e=>e.remove())")
            await page.add_style_tag(content="nextjs-portal { display: none !important; }")
            await page.evaluate("document.fonts.ready")
            await page.wait_for_timeout(400)
            boxes=[]
            for number,loc in enumerate(locators,1):
                await loc.first.wait_for(state="visible")
                box=await loc.first.bounding_box()
                if not box: raise RuntimeError(f"Destaque ausente: {name} / {number}")
                boxes.append(dict(**box,number=number))
            await page.evaluate("""boxes => {
                for (const b of boxes) {
                    const r=document.createElement('div'); r.dataset.manual='highlight';
                    Object.assign(r.style,{position:'absolute',left:(b.x+scrollX-4)+'px',top:(b.y+scrollY-4)+'px',width:(b.width+8)+'px',height:(b.height+8)+'px',border:'3px solid #dc2626',borderRadius:'5px',zIndex:'2147483647',pointerEvents:'none'});
                    const n=document.createElement('span'); n.textContent=b.number;
                    Object.assign(n.style,{position:'absolute',left:'-12px',top:'-15px',background:'#dc2626',color:'white',border:'2px solid white',borderRadius:'50%',width:'26px',height:'26px',font:'bold 16px Arial',textAlign:'center',lineHeight:'23px'});
                    r.append(n);document.body.append(r);
                }
            }""",boxes)
            opts=dict(path=str(ROOT/"imagens"/f"{name}.png"),animations="disabled")
            if clip: opts["clip"]=clip
            await page.screenshot(**opts)
            print(f"Capturada: {name}",flush=True)
            await page.evaluate("document.querySelectorAll('[data-manual]').forEach(e=>e.remove())")

        await page.goto(BASE_URL+"/login")
        await page.get_by_label("Usuário",exact=True).fill("demonstracao")
        await shot("01-login",[page.get_by_label("Usuário",exact=True),page.get_by_label("Senha",exact=True),page.get_by_role("button",name="Entrar",exact=True),page.get_by_role("button",name="Esqueceu sua senha?")])
        authenticated = True
        await page.goto(BASE_URL+"/")
        await page.get_by_role("heading",name="Visão executiva").wait_for()
        await shot("02-visao-geral",[page.get_by_role("navigation").first,page.get_by_role("button",name="Filtrar expedientes: Novos",exact=True).locator(".."),page.get_by_text("Pipeline de coleta",exact=True)])
        await shot("03-coleta",[page.get_by_role("button",name="Executar coleta",exact=True),page.get_by_role("button",name="Atualizar status da coleta"),page.get_by_role("link",name="Ver relatório de coletas"),page.get_by_test_id("pipeline-scroll-region")],dict(x=715,y=260,width=710,height=490))
        await page.get_by_test_id("pipeline-scroll-region").evaluate("e=>e.scrollLeft=e.scrollWidth")
        await shot("20-djen-coleta",[page.get_by_role("button",name="Reexecutar somente Publicações DJEN"),page.get_by_test_id("pipeline-scroll-region")],dict(x=715,y=260,width=710,height=490))
        await page.get_by_test_id("pipeline-scroll-region").evaluate("e=>e.scrollLeft=0")
        await page.get_by_role("button",name="Descartar coleta do dia").click()
        await shot("04-descarte",[page.get_by_role("alertdialog"),page.get_by_role("button",name="Cancelar",exact=True),page.get_by_role("button",name="Descartar coleta",exact=True)],dict(x=380,y=220,width=680,height=460))
        await page.get_by_role("button",name="Cancelar",exact=True).click()
        await page.goto(BASE_URL+"/expedientes")
        await page.get_by_text("Filtros avançados",exact=False).click()
        await page.get_by_text(ITEM['processo']['numero'],exact=True).wait_for()
        await shot("05-expedientes",[page.get_by_role("textbox",name="Buscar expedientes"),page.locator("details"),page.get_by_role("button",name="Exportar expedientes em PDF"),page.get_by_text(ITEM['processo']['numero'],exact=True)])
        await page.get_by_text(ITEM['processo']['numero'],exact=True).click()
        dialog=page.get_by_role("dialog")
        await shot("06-detalhe-expediente",[page.get_by_role("button",name="Copiar processo"),dialog.locator("section").filter(has=page.get_by_role("heading",name="Prazo e ação processual")),dialog.locator("section").filter(has=page.get_by_role("heading",name="Dados do processo"))],dict(x=780,y=0,width=660,height=900))
        await dialog.get_by_role("heading",name="Última alteração identificada").scroll_into_view_if_needed()
        await shot("19-alteracoes",[dialog.locator("section").filter(has=page.get_by_role("heading",name="Última alteração identificada"))],dict(x=780,y=300,width=660,height=600))
        await page.get_by_label("Fechar",exact=True).click()
        await page.get_by_role("button",name="Exportar expedientes em PDF").click()
        await shot("07-exportacao",[page.get_by_role("dialog"),page.get_by_role("button",name="Analítico",exact=True),page.get_by_role("button",name="Sintético",exact=True)],dict(x=380,y=220,width=680,height=460))
        await page.get_by_role("button",name="Cancelar",exact=True).click()
        await page.goto(BASE_URL+"/djen")
        await page.get_by_text(PUB['processo']['numero'],exact=True).wait_for()
        await shot("08-djen",[page.get_by_role("textbox",name="Pesquisar publicações DJEN"),page.get_by_role("search"),page.get_by_role("button",name="Exportar publicações em PDF"),page.get_by_text(PUB['processo']['numero'],exact=True)])
        await page.get_by_text(PUB['processo']['numero'],exact=True).click()
        await shot("09-detalhe-djen",[page.get_by_role("link",name="Abrir inteiro teor"),page.get_by_role("dialog").locator("section").filter(has=page.get_by_role("heading",name="Partes e advogados")),page.get_by_role("dialog").locator("section").filter(has=page.get_by_role("heading",name="Texto publicado"))],dict(x=670,y=0,width=770,height=900))
        await page.get_by_label("Fechar",exact=True).click()
        await page.goto(BASE_URL+"/historico")
        await page.get_by_text(NEW['processo']['numero'],exact=True).wait_for()
        await shot("10-historico",[page.get_by_role("tablist"),page.locator("main form"),page.get_by_role("button",name="Exportar histórico de expedientes em PDF"),page.get_by_text(NEW['processo']['numero'],exact=True)])
        await page.get_by_role("tab",name="Publicações Processuais").click()
        await page.get_by_text(PUB['processo']['numero'],exact=True).wait_for()
        await shot("11-historico-djen",[page.get_by_role("tab",name="Publicações Processuais"),page.get_by_role("button",name="Exportar histórico de publicações em PDF"),page.get_by_text(PUB['processo']['numero'],exact=True)])
        await page.get_by_role("tab",name="Orquestração de coletas").click()
        await page.get_by_role("button",name="Ver erro").click()
        await shot("12-orquestracao",[page.get_by_role("tab",name="Orquestração de coletas"),page.get_by_role("table"),page.get_by_role("alert")])
        await page.goto(BASE_URL+"/avisos")
        await page.get_by_role("button",name="Marcar como lido").wait_for()
        await shot("13-avisos",[page.get_by_role("button",name="Somente não lidos"),page.get_by_role("article"),page.get_by_role("button",name="Marcar como lido")])
        await page.goto(BASE_URL+"/estatisticas")
        await page.get_by_role("heading",name="Entradas e movimentações").wait_for()
        await shot("14-estatisticas",[page.get_by_role("button",name="30 dias",exact=True),page.get_by_role("region",name="Tempo economizado estimado"),page.get_by_role("heading",name="Entradas e movimentações")])
        await page.goto(BASE_URL+"/configuracoes")
        await page.get_by_role("button",name="Salvar alterações").wait_for()
        await shot("15-configuracoes",[page.get_by_label("Nome de exibição"),page.get_by_label("Tema visual"),page.get_by_label("Horário diário"),page.get_by_role("button",name="Salvar alterações")])
        await page.get_by_role("heading",name="Fontes conectadas").scroll_into_view_if_needed()
        await shot("16-fontes",[page.get_by_role("switch",name="Habilitar todas as fontes"),page.get_by_role("heading",name="Prontidão operacional"),page.get_by_role("switch",name="Coleta PJe 1º Grau TJRN",exact=True)])
        await page.get_by_role("button",name="Alterar senha",exact=True).scroll_into_view_if_needed()
        await shot("17-senha",[page.get_by_label("Senha atual",exact=True),page.get_by_label("Nova senha",exact=True),page.get_by_label("Confirmar nova senha",exact=True),page.get_by_role("button",name="Alterar senha",exact=True)],dict(x=0,y=560,width=1440,height=340))
        await page.goto(BASE_URL+"/")
        await page.get_by_role("heading",name="Visão executiva").wait_for()
        await shot("18-navegacao",[page.get_by_role("navigation").first,page.get_by_role("button",name="Mudar para tema escuro"),page.get_by_role("button",name="Sair",exact=True)],dict(x=0,y=0,width=1440,height=130))
        if errors: raise RuntimeError("Erros de interface: "+"; ".join(errors))
        await browser.close()

if __name__ == "__main__": asyncio.run(main())
