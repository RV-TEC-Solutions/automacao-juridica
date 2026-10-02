import os
import re
import shutil
import subprocess
import sys
import time

try:
    import pyatspi
except ImportError:
    pyatspi = None

NOMES_APLICACAO = (
    "pjeoffice pro - 2.5.16u",
    "pjeoffice",
    "pjeoffice pro",
    "pjeoffice-pro",
)
NOME_JANELA_PIN = ("informe a senha")
NOMES_BOTAO_CONFIRMAR = ("ok", "confirmar", "prosseguir", "entrar")
KEYSYM_RETURN = 0xFF0D


def obter_geometria_janela(wid: str):
    """Obtém coordenadas (x, y, largura, altura) de uma janela X11."""
    try:
        res = subprocess.run(["xdotool", "getwindowgeometry", wid], capture_output=True, text=True, timeout=2, check=False)
        pos_match = re.search(r"Position:\s*(\d+),(\d+)", res.stdout)
        geo_match = re.search(r"Geometry:\s*(\d+)x(\d+)", res.stdout)
        if pos_match and geo_match:
            x, y = int(pos_match.group(1)), int(pos_match.group(2))
            w, h = int(geo_match.group(1)), int(geo_match.group(2))
            return x, y, w, h
    except Exception:
        pass
    return None


def percorrer(no):
    yield no

    for filho in no:
        yield from percorrer(filho)


def esta_visivel_e_editavel(no):
    if not pyatspi:
        return False
    estado = no.getState()

    return (
        estado.contains(pyatspi.STATE_SHOWING)
        and estado.contains(pyatspi.STATE_VISIBLE)
        and estado.contains(pyatspi.STATE_EDITABLE)
        and estado.contains(pyatspi.STATE_SENSITIVE)
    )


def localizar_aplicacao():
    if not pyatspi:
        raise RuntimeError("pyatspi não está instalado neste ambiente Python.")

    desktop = pyatspi.Registry.getDesktop(0)

    for aplicacao in desktop:
        nome = (aplicacao.name or "").lower()

        if any(alvo in nome for alvo in NOMES_APLICACAO):
            return aplicacao

    nomes = [
        aplicacao.name
        for aplicacao in desktop
        if aplicacao.name
    ]

    raise RuntimeError(
        "PJEOffice não foi encontrado no AT-SPI. "
        f"Aplicações visíveis: {nomes}"
    )


def localizar_janela(aplicacao):
    if not pyatspi:
        raise RuntimeError("pyatspi não está disponível.")

    janelas = [
        no
        for no in percorrer(aplicacao)
        if no.getRole() == pyatspi.ROLE_DIALOG
        and (no.name or "").strip().lower() == NOME_JANELA_PIN
        and no.getState().contains(pyatspi.STATE_SHOWING)
        and no.getState().contains(pyatspi.STATE_VISIBLE)
    ]

    if len(janelas) != 1:
        detalhes = [
            f"{janela.getRoleName()}: {janela.name!r}"
            for janela in janelas
        ]

        raise RuntimeError(
            f"Janela do PIN ausente: {detalhes}"
        )

    return janelas[0]


def localizar_campo_pin(janela):
    if not pyatspi:
        raise RuntimeError("pyatspi não está disponível.")

    campos = [
        no
        for no in percorrer(janela)
        if no.getRole() == pyatspi.ROLE_PASSWORD_TEXT
        and esta_visivel_e_editavel(no)
    ]

    if len(campos) != 1:
        detalhes = [
            f"{campo.getRoleName()}: {campo.name!r}"
            for campo in campos
        ]

        raise RuntimeError(
            f"Campo PIN ambíguo ou ausente: {detalhes}"
        )

    return campos[0]


def localizar_botao_confirmar(janela):
    if not pyatspi:
        raise RuntimeError("pyatspi não está disponível.")

    botoes = [
        no
        for no in percorrer(janela)
        if no.getRole() == pyatspi.ROLE_PUSH_BUTTON
        and (no.name or "").strip().lower() in NOMES_BOTAO_CONFIRMAR
        and no.getState().contains(pyatspi.STATE_SHOWING)
        and no.getState().contains(pyatspi.STATE_SENSITIVE)
    ]

    if len(botoes) != 1:
        detalhes = [
            f"{botao.getRoleName()}: {botao.name!r}"
            for botao in botoes
        ]

        raise RuntimeError(
            f"Botão OK ambíguo ou ausente: {detalhes}"
        )

    return botoes[0]


def acionar(botao):
    acoes = botao.queryAction()

    if acoes.nActions == 0:
        raise RuntimeError(
            "O botão OK não expõe nenhuma ação AT-SPI."
        )

    if not acoes.doAction(0):
        raise RuntimeError(
            "O AT-SPI recusou a ação do botão OK."
        )


def confirmar_com_enter(campo_pin):
    """Confirma o PIN sem depender do rótulo do botão do PJeOffice."""
    if not pyatspi:
        raise RuntimeError("pyatspi não está disponível.")

    componente = campo_pin.queryComponent()

    if not componente.grabFocus():
        raise RuntimeError(
            "Não foi possível focar o campo do PIN para confirmá-lo com Enter."
        )

    pyatspi.Registry.generateKeyboardEvent(
        KEYSYM_RETURN,
        None,
        pyatspi.KEY_SYM,
    )


def dispensar_autorizacao_atspi() -> bool:
    """Tenta clicar no botão de autorizar/sempre via AT-SPI se a janela de autorização estiver aberta."""
    if not pyatspi:
        return False
    try:
        desktop = pyatspi.Registry.getDesktop(0)
        for app in desktop:
            for no in percorrer(app):
                if no.getRole() == pyatspi.ROLE_PUSH_BUTTON:
                    nome = (no.name or "").strip().lower()
                    if any(alvo in nome for alvo in ("sempre", "autorizar", "permitir", "sim")):
                        if no.getState().contains(pyatspi.STATE_SHOWING) and no.getState().contains(pyatspi.STATE_SENSITIVE):
                            acoes = no.queryAction()
                            if acoes.nActions > 0 and acoes.doAction(0):
                                return True
    except Exception:
        pass
    return False


def preencher_pin_x11(pin: str) -> bool:
    """Preenche a senha no diálogo do PJeOffice diretamente via eventos de janela X11 (wmctrl/xdotool)."""
    if not (shutil.which("xdotool") or shutil.which("wmctrl")) or not os.environ.get("DISPLAY"):
        return False

    titulos_autorizacao = [
        "autorização de site",
        "autorizacao de site",
        "autorização",
        "autorizacao",
        "autorizar site",
        "permissão de acesso",
        "permissao de acesso",
    ]

    titulos_senha = [
        "informe a senha",
        "informe sua senha",
        "informe a sua senha",
        "informe o pin",
        "informe seu pin",
        "senha do certificado",
        "pin do certificado",
        "digite a senha",
        "digite o pin",
        "digite sua senha",
        "digite seu pin",
        "digite o seu pin",
        "autenticação",
        "autenticacao",
        "inserir pin",
        "inserir senha",
        "pin",
        "senha",
    ]

    titulos_selecao = [
        "selecione o certificado",
        "selecao de certificado",
        "seleção de certificado",
        "escolha o certificado",
        "escolha de certificado",
        "certificados",
    ]

    # Obter lista de janelas atuais via wmctrl
    janelas_ativas = []
    if shutil.which("wmctrl"):
        res = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=False)
        for linha in res.stdout.strip().splitlines():
            partes = linha.split(None, 3)
            if len(partes) >= 4:
                hex_id, _, _, titulo = partes
                try:
                    int_wid = str(int(hex_id, 16))
                    janelas_ativas.append((int_wid, titulo.strip()))
                except ValueError:
                    pass

    # Se wmctrl não achou ou não está instalado, usa xdotool
    if not janelas_ativas and shutil.which("xdotool"):
        for t in titulos_senha + titulos_selecao + titulos_autorizacao:
            res = subprocess.run(["xdotool", "search", "--name", t], capture_output=True, text=True, check=False)
            for wid in res.stdout.strip().splitlines():
                wid = wid.strip()
                if wid:
                    name_res = subprocess.run(["xdotool", "getwindowname", wid], capture_output=True, text=True, check=False)
                    janelas_ativas.append((wid, name_res.stdout.strip()))

    # Descarta popup xmessage se estiver bloqueando
    for wid, titulo in janelas_ativas:
        if "xmessage" in titulo.lower():
            print(f"[pjeoffice-gui] Fechando popup do sistema: '{titulo}' (ID: {wid})", flush=True)
            subprocess.run(["xdotool", "key", "--window", wid, "Return"], capture_output=True, check=False)
            subprocess.run(["xdotool", "windowkill", wid], capture_output=True, check=False)

    # Descarta popup de cancelamento anterior se estiver na tela
    for wid, titulo in janelas_ativas:
        if "cancelamento" in titulo.lower():
            print(f"[pjeoffice-gui] Fechando diálogo de cancelamento: '{titulo}' (ID: {wid})", flush=True)
            subprocess.run(["xdotool", "key", "--window", wid, "Return"], capture_output=True, check=False)
            subprocess.run(["xdotool", "windowkill", wid], capture_output=True, check=False)

    # 0. Trata janela de autorização de site do PJeOffice (ex: "Autorização de site")
    for wid, titulo in janelas_ativas:
        tit_lower = titulo.lower()
        if any(aut in tit_lower for aut in titulos_autorizacao):
            print(f"[pjeoffice-gui] Janela de AUTORIZAÇÃO detectada: '{titulo}' (ID: {wid}). Autorizando site...", flush=True)
            geo = obter_geometria_janela(wid)
            if geo:
                gx, gy, gw, gh = geo
                # Clica no centro da janela para garantir foco de entrada
                subprocess.run(["xdotool", "mousemove", str(gx + gw // 2), str(gy + gh // 2), "click", "1"], capture_output=True, check=False)
                time.sleep(0.1)
                # Clica no botão "Sempre" (geralmente à esquerda na barra inferior de botões do diálogo)
                btn_y = str(gy + gh - 35)
                btn_sempre_x = str(gx + int(gw * 0.28))
                subprocess.run(["xdotool", "mousemove", btn_sempre_x, btn_y, "click", "1"], capture_output=True, check=False)
                time.sleep(0.1)
                # Clica no botão "Autorizar" (ao centro da barra inferior)
                btn_autorizar_x = str(gx + int(gw * 0.50))
                subprocess.run(["xdotool", "mousemove", btn_autorizar_x, btn_y, "click", "1"], capture_output=True, check=False)
                time.sleep(0.1)

            # Envia também atalhos de teclado nativos (Alt+S para Sempre, Alt+A para Autorizar, Return, Space)
            subprocess.run(["xdotool", "windowactivate", wid], capture_output=True, check=False)
            subprocess.run(["xdotool", "windowfocus", wid], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "alt+s"], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "alt+a"], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "Return"], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "space"], capture_output=True, check=False)
            time.sleep(0.8)
            break

    # 1. Trata janela intermediária de seleção de múltiplos certificados (caso haja mais de um token USB plugado)
    for wid, titulo in janelas_ativas:
        tit_lower = titulo.lower()
        if any(sel in tit_lower for sel in titulos_selecao):
            print(f"[pjeoffice-gui] Janela de SELEÇÃO DE CERTIFICADO detectada: '{titulo}' (ID: {wid})", flush=True)
            geo = obter_geometria_janela(wid)
            if geo:
                gx, gy, gw, gh = geo
                # 1.1 Duplo-clique no primeiro certificado da lista/tabela para selecioná-lo e confirmar
                cert_row_y = str(gy + int(gh * 0.40))
                cert_row_x = str(gx + gw // 2)
                print(f"[pjeoffice-gui] Selecionando certificado na tabela (duplo-clique em {cert_row_x},{cert_row_y})...", flush=True)
                subprocess.run(["xdotool", "mousemove", cert_row_x, cert_row_y, "click", "--repeat", "2", "1"], capture_output=True, check=False)
                time.sleep(0.3)

                # 1.2 Clica no botão "Selecionar" / "OK" (normalmente na barra inferior)
                btn_sel_y = str(gy + gh - 35)
                btn_sel_x = str(gx + int(gw * 0.35))
                subprocess.run(["xdotool", "mousemove", btn_sel_x, btn_sel_y, "click", "1"], capture_output=True, check=False)
                time.sleep(0.1)

            subprocess.run(["xdotool", "windowactivate", wid], capture_output=True, check=False)
            subprocess.run(["xdotool", "windowfocus", wid], capture_output=True, check=False)
            # Envia atalho Alt+S (Selecionar) ou Alt+O (OK)
            subprocess.run(["xdotool", "key", "alt+s"], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "alt+o"], capture_output=True, check=False)
            time.sleep(0.8)
            break

    # 2. Busca e preenche estritamente a janela de PIN / Senha
    for wid, titulo in janelas_ativas:
        tit_lower = titulo.lower()

        # Ignora janelas do sistema ou a janela estática de fundo do PJeOffice
        if any(ign in tit_lower for ign in ("chromium", "chrome", "firefox", "bash", "terminal", "xmessage")):
            continue
        if tit_lower.startswith("pjeoffice pro") and not any(k in tit_lower for k in ("senha", "pin", "password")):
            continue
        if tit_lower == "pjeoffice" or tit_lower.startswith("br-jus-cnj"):
            continue

        # Verifica se corresponde a um diálogo de senha
        eh_janela_senha = (
            any(alvo in tit_lower for alvo in titulos_senha)
            or ("senha" in tit_lower or "pin" in tit_lower or "password" in tit_lower)
        )

        if eh_janela_senha:
            print(f"[pjeoffice-gui] >>> JANELA DE PIN/SENHA DETECTADA: '{titulo}' (ID: {wid})! <<<", flush=True)
            geo = obter_geometria_janela(wid)
            if geo:
                gx, gy, gw, gh = geo
                # Clica no centro (onde fica o campo de entrada da senha)
                subprocess.run(["xdotool", "mousemove", str(gx + gw // 2), str(gy + gh // 2), "click", "1"], capture_output=True, check=False)
                time.sleep(0.2)

            subprocess.run(["xdotool", "windowactivate", wid], capture_output=True, check=False)
            subprocess.run(["xdotool", "windowfocus", wid], capture_output=True, check=False)
            time.sleep(0.2)

            print("[pjeoffice-gui] Preenchendo PIN e enviando confirmação...", flush=True)
            # Digita o PIN com precisão
            subprocess.run(
                ["xdotool", "type", "--delay", "50", "--", pin],
                capture_output=True,
                check=False,
            )
            time.sleep(0.1)

            # Envia Return para submeter o diálogo modal
            subprocess.run(["xdotool", "key", "Return"], capture_output=True, check=False)

            # Clica no botão OK na barra inferior se a janela foi mapeada
            if geo:
                btn_ok_y = str(gy + gh - 35)
                btn_ok_x = str(gx + gw // 2)
                subprocess.run(["xdotool", "mousemove", btn_ok_x, btn_ok_y, "click", "1"], capture_output=True, check=False)

            # Aguarda a submissão e confirmação de fechamento
            time.sleep(1.0)
            print("[pjeoffice-gui] Submissão do PIN concluída!", flush=True)
            return True

    return False


def preencher_pin_atspi(pin: str) -> bool:
    """Preenche a senha utilizando a camada de acessibilidade AT-SPI."""
    if not pyatspi:
        return False

    aplicacao = localizar_aplicacao()
    janela = localizar_janela(aplicacao)
    campo_pin = localizar_campo_pin(janela)
    editor = campo_pin.queryEditableText()

    if not editor.setTextContents(pin):
        raise RuntimeError("AT-SPI recusou o preenchimento do PIN.")

    try:
        botao = localizar_botao_confirmar(janela)
    except RuntimeError:
        confirmar_com_enter(campo_pin)
    else:
        acionar(botao)

    return True


def preencher_pin():
    pin = os.environ.get("PJE_CERT_PIN")

    if not pin:
        raise RuntimeError("PJE_CERT_PIN não foi configurado.")

    inicio = time.monotonic()
    limite = inicio + 45
    ultimo_erro = None
    todas_janelas = set()
    segundo_anterior = -1

    print("[pjeoffice-gui] Monitor de interface X11 iniciado. Aguardando diálogos do PJeOffice...", flush=True)

    while time.monotonic() < limite:
        tempo_decorrido = int(time.monotonic() - inicio)

        # Loga a cada segundo as janelas presentes na tela virtual
        if tempo_decorrido != segundo_anterior:
            segundo_anterior = tempo_decorrido
            janelas_atuais = []
            if shutil.which("wmctrl"):
                res = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=False)
                for l in res.stdout.strip().splitlines():
                    p = l.split(None, 3)
                    if len(p) >= 4:
                        janelas_atuais.append(p[3].strip())
                        todas_janelas.add(p[3].strip())
            print(f"[pjeoffice-gui] T+{tempo_decorrido:02d}s | Janelas ativas: {janelas_atuais}", flush=True)

        # Tenta autorizar site via acessibilidade se o diálogo modal estiver na árvore AT-SPI
        try:
            dispensar_autorizacao_atspi()
        except Exception:
            pass

        # 1. Tenta método nativo X11 (rápido e determinístico no Xvfb do container)
        try:
            if preencher_pin_x11(pin):
                print(f"[pjeoffice-gui] >>> PIN preenchido e confirmado com sucesso em T+{tempo_decorrido}s! <<<", flush=True)
                return
        except Exception as erro:
            ultimo_erro = f"X11: {erro}"

        # 2. Tenta método AT-SPI (acessibilidade GNOME / Java ATK)
        try:
            if preencher_pin_atspi(pin):
                print(f"[pjeoffice-gui] >>> PIN preenchido via AT-SPI em T+{tempo_decorrido}s! <<<", flush=True)
                return
        except Exception as erro:
            ultimo_erro = f"AT-SPI: {erro}"

        time.sleep(0.5)

    dump_x11 = ""
    if shutil.which("xwininfo"):
        dump_res = subprocess.run(["xwininfo", "-root", "-tree"], capture_output=True, text=True, check=False)
        dump_x11 = "\n".join(dump_res.stdout.splitlines()[:60])

    raise RuntimeError(
        f"Não foi possível concluir o PIN em 45 segundos.\n"
        f"Janelas vistas no X11: {list(todas_janelas)}\n"
        f"Último erro: {ultimo_erro}\n"
        f"Árvore X11:\n{dump_x11}"
    )


if __name__ == "__main__":
    try:
        preencher_pin()
    except Exception as erro:
        print(f"erro: {erro}", file=sys.stderr)
        raise SystemExit(2)
