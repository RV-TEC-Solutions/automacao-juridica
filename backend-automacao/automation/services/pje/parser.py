#!/usr/bin/env python3
"""Extrai expedientes das capturas HTML do painel do PJe.

O módulo pode ser importado por outros scripts ou executado diretamente para
gerar um arquivo JSON com os expedientes encontrados.
"""

import argparse
import json
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

# Beautiful Soup é a biblioteca que interpreta o texto HTML e o transforma em
# uma árvore de elementos pesquisável. Ela não acessa a internet: neste parser,
# recebe apenas o conteúdo dos arquivos HTML já salvos em disco.
from bs4 import BeautifulSoup


# Expressões regulares para localizar os valores relevantes dentro do texto
# visível dos elementos HTML do PJe.
PADRAO_PROCESSO = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4}")
PADRAO_DATA = re.compile(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2})")
PADRAO_DOCUMENTO = re.compile(r"\((\d+)\)")


def texto(elemento):
    """Retorna o texto visível de um elemento, normalizado em uma linha."""

    # get_text remove as tags internas, como <span> e <i>, e junta seus
    # conteúdos com espaços. Isso evita que o parser dependa da formatação.
    return elemento.get_text(" ", strip=True) if elemento else ""


def extrair_comunicacao(elemento):
    """Separa o meio de comunicação da data exibida pelo PJe."""

    valor = texto(elemento)
    data = PADRAO_DATA.search(valor)
    if not data:
        return valor, ""
    meio = valor[: data.start()].strip().rstrip("(").strip()
    return meio, data.group(1)


def extrair_acao(celula):
    """Normaliza os controles de ação exibidos na primeira célula da linha."""

    # Uma mesma célula pode conter vários botões (por exemplo, "Responder" e
    # "Sem interesse"). O texto bruto, portanto, não é um valor de ação útil.
    valor = texto(celula)
    valor_lower = valor.lower()

    # "Tomar ciência" tem prioridade porque identifica expedientes que ainda
    # aguardam ciência; os demais textos são classificados pela ação disponível.
    if "tomar ciência" in valor_lower:
        return "tomar_ciencia"
    if "sem interesse" in valor_lower:
        return "sem_interesse"
    if "responder" in valor_lower:
        return "responder"
    return None


def classificar_tipo_pendencia(caixa, acao_pje):
    """Converte a caixa do PJe no valor persistido pelo domínio."""
    valor = caixa.lower()

    # A tela principal pode manter no título as duas categorias. A ação da
    # linha é mais específica e deve ser usada antes do texto da caixa.
    if acao_pje == "tomar_ciencia":
        return "ciencia"
    if acao_pje == "responder":
        return "resposta"
    if "ciência" in valor:
        return "ciencia"
    if "resposta" in valor:
        return "resposta"
    return "nao_identificada"


def normalizar_data(valor):
    """Converte datas do PJe para ISO-8601 sem inventar fuso horário."""
    valor = (valor or "").strip()
    if not valor:
        return None

    for formato in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(valor, formato).isoformat()
        except ValueError:
            continue

    return None


def classificar_prazo(prazo_texto, limite):
    """Retorna o status e o prazo fatal normalizado."""
    limite_normalizado = normalizar_data(limite)
    if limite_normalizado:
        return "calculado", limite_normalizado

    if not prazo_texto or "sem prazo" in prazo_texto.lower():
        return "sem_prazo", None

    return "em_calculo", None


def _extrair_registro(linha, caixa):
    """Extrai um registro de uma linha ou retorna ``None`` se ela for inválida."""

    # No HTML do PJe, cada expediente é uma <tr>. A primeira célula contém as
    # ações e a segunda contém os dados do destinatário e do processo.
    celulas = linha.find_all("td", recursive=False)
    if len(celulas) < 2:
        return None

    # Estes seletores representam o modelo atual da tabela de expedientes:
    # bloco esquerdo = informações do expediente; bloco direito = processo.
    bloco_info = celulas[1].select_one(".col-md-4.informacoes-linha-expedientes")
    bloco_processo = celulas[1].select_one(".col-md-8.informacoes-linha-expedientes")
    if bloco_info is None or bloco_processo is None:
        return None

    # find_all(..., recursive=False) limita a busca aos campos imediatos do
    # bloco. Assim, detalhes internos do processo não são misturados aqui.
    campos = [texto(div) for div in bloco_info.find_all("div", recursive=False)]
    info_divs = bloco_info.find_all("div", recursive=False)
    conteudo_processo = bloco_processo.find("div", class_="col-md-12", recursive=False)
    if conteudo_processo is None:
        return None

    linhas_processo = conteudo_processo.find_all("div", recursive=False)
    if not linhas_processo:
        return None

    # A primeira linha combina classe, número CNJ e assunto. O número do
    # processo serve como ponto seguro para separar classe e assunto.
    primeira_linha = texto(linhas_processo[0])
    processo = PADRAO_PROCESSO.search(primeira_linha)
    if not processo:
        return None

    numero_processo = processo.group(0)
    antes, depois = primeira_linha.split(numero_processo, 1)
    classe = antes.strip()
    assunto = depois.strip()

    documento_bruto = campos[1] if len(campos) > 1 else ""
    identificador = PADRAO_DOCUMENTO.search(documento_bruto)
    if identificador is None:
        return None

    expediente_id = identificador.group(1)
    tipo_documento = documento_bruto[: identificador.start()].strip()

    meio = ""
    data_expedicao = ""
    if len(info_divs) > 2:
        meio, data_expedicao = extrair_comunicacao(info_divs[2])

    prazo = campos[3].replace("Prazo:", "", 1).strip() if len(campos) > 3 else ""
    ciencia = next(
        (campo for campo in campos if "ciência" in campo.lower() and "Data limite" not in campo),
        "",
    )
    limite = next(
        (
            campo.split(":", 1)[1].strip()
            for campo in campos
            if "Data limite" in campo and ":" in campo
        ),
        "",
    )

    acao_pje = extrair_acao(celulas[0])
    status_prazo_fatal, prazo_fatal = classificar_prazo(prazo, limite)

    return {
        "caixa": caixa,
        "acao_pje": acao_pje,
        "tipo_pendencia": classificar_tipo_pendencia(caixa, acao_pje),
        "destinatario": campos[0] if campos else "",
        "tipo_documento": tipo_documento,
        "identificador_pje": expediente_id,
        "meio_comunicacao": meio,
        "data_expedicao": normalizar_data(data_expedicao),
        "prazo_texto": prazo,
        "ciencia_texto": ciencia,
        "prazo_fatal": prazo_fatal,
        "status_prazo_fatal": status_prazo_fatal,
        "classe": classe,
        "numero_processo": numero_processo,
        "assunto": assunto,
        "partes_texto": texto(linhas_processo[1]) if len(linhas_processo) > 1 else "",
        "unidade_judiciaria": (
            texto(linhas_processo[2]).lstrip("/")
            if len(linhas_processo) > 2
            else ""
        ),
        "tribunal": "TJRN",
    }


def extrair_expedientes_arquivo(arquivo):
    """Extrai e deduplica os expedientes de uma captura HTML."""
    arquivo = Path(arquivo)
    soup = BeautifulSoup(
        arquivo.read_text(encoding="utf-8", errors="replace"),
        "html.parser",
    )

    titulo_caixa = soup.select_one("#divListaExpedientes h6")
    caixa = texto(titulo_caixa).replace(" Caixa de entrada", "")
    tabela = soup.find("tbody", id="formExpedientes:tbExpedientes:tb")
    if tabela is None:
        return []

    expedientes = OrderedDict()
    for linha in tabela.find_all("tr", recursive=False):
        registro = _extrair_registro(linha, caixa)
        if registro is not None:
            expedientes.setdefault(registro["identificador_pje"], registro)

    return list(expedientes.values())


def extrair_expedientes(pasta):
    """Extrai e deduplica os expedientes dos HTMLs de ``pasta``."""
    expedientes = OrderedDict()

    for arquivo in sorted(Path(pasta).glob("*.html")):
        for registro in extrair_expedientes_arquivo(arquivo):
            expedientes.setdefault(registro["identificador_pje"], registro)

    return list(expedientes.values())


def main():
    # A CLI recebe uma pasta de capturas e o caminho do JSON que será criado.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entrada", type=Path, help="Pasta com os HTMLs renderizados do PJe")
    parser.add_argument("saida", type=Path, help="Arquivo JSON de saída")
    args = parser.parse_args()

    registros = extrair_expedientes(args.entrada)
    if not registros:
        raise SystemExit("Nenhum expediente encontrado na pasta informada.")

    # ensure_ascii=False mantém caracteres portugueses, como "ciência", legíveis
    # no JSON. indent=2 deixa o arquivo adequado para leitura e versionamento.
    args.saida.write_text(
        json.dumps(registros, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{len(registros)} expedientes únicos gravados em {args.saida}")


if __name__ == "__main__":
    main()
