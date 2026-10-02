import os
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

    # 0. Trata janela de autorização de site do PJeOffice (ex: "Autorização de site")
    for wid, titulo in janelas_ativas:
        tit_lower = titulo.lower()
        if any(aut in tit_lower for aut in titulos_autorizacao):
            subprocess.run(["xdotool", "windowactivate", "--sync", wid], capture_output=True, check=False)
            subprocess.run(["xdotool", "windowfocus", "--sync", wid], capture_output=True, check=False)
            time.sleep(0.3)
            # Envia atalhos para autorizar
            subprocess.run(["xdotool", "key", "--window", wid, "alt+s"], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "--window", wid, "alt+a"], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "--window", wid, "space"], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "--window", wid, "Return"], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "Return"], capture_output=True, check=False)
            time.sleep(0.8)
            break

    # 1. Trata janela intermediária de seleção de múltiplos certificados (caso haja mais de um token USB plugado)
    for wid, titulo in janelas_ativas:
        tit_lower = titulo.lower()
        if any(sel in tit_lower for sel in titulos_selecao):
            # Foca e confirma seleção com Enter
            subprocess.run(["xdotool", "windowactivate", "--sync", wid], capture_output=True, check=False)
            subprocess.run(["xdotool", "windowfocus", "--sync", wid], capture_output=True, check=False)
            time.sleep(0.3)
            subprocess.run(["xdotool", "key", "--window", wid, "Return"], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "Return"], capture_output=True, check=False)
            time.sleep(0.8)
            break

    # 2. Busca e preenche estritamente a janela de PIN / Senha
    for wid, titulo in janelas_ativas:
        tit_lower = titulo.lower()

        # Ignora janelas do sistema ou a janela estática de fundo do PJeOffice
        if any(ign in tit_lower for ign in ("chromium", "chrome", "firefox", "bash", "terminal")):
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
            # Ativa e foca a janela de senha
            subprocess.run(["xdotool", "windowactivate", "--sync", wid], capture_output=True, check=False)
            subprocess.run(["xdotool", "windowfocus", "--sync", wid], capture_output=True, check=False)
            time.sleep(0.4)

            # Digita o PIN com precisão
            subprocess.run(
                ["xdotool", "type", "--window", wid, "--delay", "50", "--", pin],
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["xdotool", "type", "--delay", "50", "--", pin],
                capture_output=True,
                check=False,
            )
            time.sleep(0.1)

            # Envia Return para submeter o diálogo modal
            subprocess.run(["xdotool", "key", "--window", wid, "Return"], capture_output=True, check=False)
            subprocess.run(["xdotool", "key", "Return"], capture_output=True, check=False)

            # Aguarda a submissão e confirmação de fechamento
            time.sleep(1.0)
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

    limite = time.monotonic() + 45
    ultimo_erro = None
    todas_janelas = set()

    while time.monotonic() < limite:
        # Tenta autorizar site via acessibilidade se o diálogo modal estiver na árvore AT-SPI
        try:
            dispensar_autorizacao_atspi()
        except Exception:
            pass

        # Coleta nomes de janelas para diagnóstico caso ocorra timeout
        try:
            if shutil.which("wmctrl"):
                res = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=False)
                for l in res.stdout.strip().splitlines():
                    p = l.split(None, 3)
                    if len(p) >= 4:
                        todas_janelas.add(p[3].strip())
        except Exception:
            pass

        # 1. Tenta método nativo X11 (rápido e determinístico no Xvfb do container)
        try:
            if preencher_pin_x11(pin):
                return
        except Exception as erro:
            ultimo_erro = f"X11: {erro}"

        # 2. Tenta método AT-SPI (acessibilidade GNOME / Java ATK)
        try:
            if preencher_pin_atspi(pin):
                return
        except Exception as erro:
            ultimo_erro = f"AT-SPI: {erro}"

        time.sleep(0.5)

    raise RuntimeError(
        "Não foi possível concluir o PIN em 45 segundos. "
        f"Janelas vistas no X11: {list(todas_janelas)}. "
        f"Último erro: {ultimo_erro}"
    )


if __name__ == "__main__":
    try:
        preencher_pin()
    except Exception as erro:
        print(f"erro: {erro}", file=sys.stderr)
        raise SystemExit(2)
