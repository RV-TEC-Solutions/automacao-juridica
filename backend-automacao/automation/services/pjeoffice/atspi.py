import os
import sys
import time

import pyatspi

NOMES_APLICACAO = ("pjeoffice pro - 2.5.16u",)
NOME_JANELA_PIN = ("informe a senha")
NOMES_BOTAO_CONFIRMAR = ("ok", "confirmar", "prosseguir", "entrar")
KEYSYM_RETURN = 0xFF0D

def percorrer(no):
    yield no

    for filho in no:
        yield from percorrer(filho)

def esta_visivel_e_editavel(no):
    estado = no.getState()

    return (
        estado.contains(pyatspi.STATE_SHOWING)
        and estado.contains(pyatspi.STATE_VISIBLE)
        and estado.contains(pyatspi.STATE_EDITABLE)
        and estado.contains(pyatspi.STATE_SENSITIVE)
    )

def localizar_aplicacao():
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

def preencher_pin():
    pin = os.environ.get("PJE_CERT_PIN")

    if not pin:
        raise RuntimeError("PJE_CERT_PIN não foi configurado.")

    limite = time.monotonic() + 30
    ultimo_erro = None

    while time.monotonic() < limite:
        try:
            aplicacao = localizar_aplicacao()
            janela = localizar_janela(aplicacao)
            campo_pin = localizar_campo_pin(janela)
            editor = campo_pin.queryEditableText()

            if not editor.setTextContents(pin):
                raise RuntimeError(
                    "AT-SPI recusou o preenchimento do PIN."
                )

            try:
                botao = localizar_botao_confirmar(janela)
            except RuntimeError:
                confirmar_com_enter(campo_pin)
            else:
                acionar(botao)
            return
        except RuntimeError as erro:
            ultimo_erro = erro
            time.sleep(0.5)

    raise RuntimeError(
        "Não foi possível concluir o PIN em 30 segundos. "
        f"Último diagnóstico: {ultimo_erro}"
    )

if __name__ == "__main__":
    try:
        preencher_pin()
    except Exception as erro:
        print(f"erro: {erro}", file=sys.stderr)
        raise SystemExit(2)
