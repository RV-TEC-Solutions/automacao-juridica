"""Importação local de um cadastro do Google Authenticator, sem rede ou Django.

Esquema: https://github.com/beemdevelopment/Aegis/blob/master/app/src/main/proto/google_auth.proto
Wire format: https://protobuf.dev/programming-guides/encoding/
"""

import argparse
import base64
import binascii
from dataclasses import dataclass, field
import getpass
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import unquote, urlsplit
import warnings

from dotenv import dotenv_values, set_key
import pyotp


ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class TotpImportError(ValueError):
    """Mensagem segura, sem incluir o conteúdo da exportação."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normalmente repete argumentos inválidos; eles podem conter o QR.
        self.print_usage(sys.stderr)
        self.exit(2, "Argumentos inválidos. Use --titular cristiano [--salvar | --diagnostico] e cole a URI somente na solicitação de entrada oculta.\n")


@dataclass(frozen=True)
class ExportedAccount:
    secret: str = field(repr=False)
    name: str
    issuer: str


def _varint(data, offset):
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            break
        byte = data[offset]
        offset += 1
        if shift == 63 and byte > 1:
            break
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, offset
    raise TotpImportError("Exportação truncada ou número Protobuf inválido.")


def _fields(data):
    offset = 0
    while offset < len(data):
        tag, offset = _varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if not 0 < number < 2**29:
            raise TotpImportError("Campo Protobuf inválido.")
        if wire == 0:
            value, offset = _varint(data, offset)
        elif wire in (1, 2, 5):
            if wire == 2:
                size, offset = _varint(data, offset)
            else:
                size = 8 if wire == 1 else 4
            end = offset + size
            if end > len(data):
                raise TotpImportError("Exportação truncada.")
            value, offset = data[offset:end], end
        else:
            raise TotpImportError("Formato Protobuf não suportado.")
        yield number, wire, value


def _single_fields(data, expected):
    result = {}
    for number, wire, value in _fields(data):
        if number not in expected:
            continue
        if wire != expected[number] or number in result:
            raise TotpImportError("Exportação com campo incompatível ou duplicado.")
        result[number] = value
    return result


def _export_parts(content):
    """Lê o envelope; aceita também a linha QR-Code: emitida pelo zbarimg."""
    if not isinstance(content, str) or len(content) > 16384:
        raise TotpImportError("Exportação inválida ou maior que um QR esperado.")
    content = content.strip().removeprefix("QR-Code:").strip()
    try:
        uri = urlsplit(content)
        if (uri.scheme != "otpauth-migration" or uri.netloc != "offline"
                or uri.path not in ("", "/") or uri.fragment):
            raise TotpImportError("Cole a URI completa otpauth-migration://offline?data=...")
        # unquote preserva '+' literal de Base64; unquote_plus o transformaria em espaço.
        values = [unquote(item.partition("=")[2]) for item in uri.query.split("&")
                  if unquote(item.partition("=")[0]) == "data"]
        if len(values) != 1 or not values[0]:
            raise TotpImportError("A exportação precisa conter um único parâmetro data.")
        encoded = values[0]
        payload = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as error:
        if isinstance(error, TotpImportError):
            raise
        raise TotpImportError("URI ou Base64 inválido; confira se o conteúdo está completo.") from None

    accounts = []
    metadata = {}
    for number, wire, value in _fields(payload):
        if number == 1:
            if wire != 2:
                raise TotpImportError("Cadastro Protobuf inválido.")
            accounts.append(value)
        elif number in (2, 3, 4, 5):
            if wire != 0 or number in metadata:
                raise TotpImportError("Metadados da exportação inválidos.")
            metadata[number] = value
    return accounts, metadata


def inspect_export(content):
    """Apenas metadados numéricos; nunca retorna a URI, nomes ou o segredo."""
    accounts, metadata = _export_parts(content)
    parameters = []
    for account in accounts:
        values = _single_fields(account, {1: 2, 2: 2, 3: 2, 4: 0, 5: 0, 6: 0, 7: 0})
        parameters.append({
            "algorithm_enum": values.get(4, 0),
            "digits_enum": values.get(5, 0),
            "type_enum": values.get(6, 0),
        })
    return {
        "version": metadata.get(2, 0), "version_present": 2 in metadata,
        "batch_size": metadata.get(3, 0), "batch_index": metadata.get(4, 0),
        "account_count": len(accounts), "parameters": parameters,
    }


def decode_export(content):
    accounts, metadata = _export_parts(content)
    # Inteiros omitidos em proto3 têm valor zero. O importador do Aegis também
    # interpreta enums UNSPECIFIED como SHA1, seis dígitos e TOTP.
    # https://github.com/beemdevelopment/Aegis/blob/master/app/src/main/java/com/beemdevelopment/aegis/otp/GoogleAuthInfo.java
    version = metadata.get(2, 0)
    # O número do envelope não substitui as verificações dos campos abaixo.
    # A gravação ainda exige que o código calculado coincida com o app.
    if version not in (0, 1, 2):
        raise TotpImportError(f"Versão de exportação não suportada: {version}. Use --diagnostico para mostrar somente metadados seguros.")
    if metadata.get(3, 0) not in (0, 1) or metadata.get(4, 0) != 0 or len(accounts) != 1:
        raise TotpImportError("Exporte somente um cadastro, em um único QR, para evitar escolher a conta errada.")

    values = _single_fields(accounts[0], {1: 2, 2: 2, 3: 2, 4: 0, 5: 0, 6: 0, 7: 0})
    if not values.get(1):
        raise TotpImportError("O cadastro não contém uma chave secreta.")
    if (values.get(4, 0) not in (0, 1) or values.get(5, 0) not in (0, 1)
            or values.get(6, 0) not in (0, 2)):
        algorithm = {1: "SHA1", 2: "SHA256", 3: "SHA512", 4: "MD5"}.get(values.get(4), "não informado/desconhecido")
        digits = {1: "6", 2: "8"}.get(values.get(5), "não informado/desconhecido")
        kind = {1: "HOTP", 2: "TOTP"}.get(values.get(6), "não informado/desconhecido")
        raise TotpImportError(f"Cadastro: {kind}, {algorithm}, dígitos={digits}. O coletor requer TOTP, SHA1 e 6 dígitos. Nenhum valor foi salvo.")
    try:
        name = values.get(2, b"").decode("utf-8")
        issuer = values.get(3, b"").decode("utf-8")
    except UnicodeDecodeError:
        raise TotpImportError("Nome ou emissor do cadastro não está em UTF-8 válido.") from None
    return ExportedAccount(base64.b32encode(values[1]).decode("ascii").rstrip("="), name, issuer)


def check_app_code(account, code):
    if not re.fullmatch(r"[0-9]{6}", code.strip()):
        raise TotpImportError("Digite os seis dígitos do cadastro selecionado no app.")
    if not pyotp.TOTP(account.secret).verify(code.strip(), valid_window=1):
        raise TotpImportError("O código não coincide com o app. Confira o cadastro e o horário; o .env não foi alterado.")


def save_secret(env_path, account, owner):
    if owner not in ("cristiano", "murilo"):
        raise TotpImportError("Titular desconhecido.")
    env_path = Path(env_path)
    if not env_path.is_file() or env_path.is_symlink():
        raise TotpImportError("O .env da raiz precisa ser um arquivo local existente.")
    original = env_path.read_bytes()
    before = dotenv_values(env_path, interpolate=False)
    key = f"PJE_{owner.upper()}_TOTP_SECRET"
    if owner == "murilo" and not before.get(key):
        key = "PJE_TOTP_SECRET"
    if before.get(key) == account.secret:
        if env_path.read_bytes() != original:
            raise TotpImportError("O .env foi editado durante a importação; tente novamente.")
        env_path.chmod(0o600)
        return key, False
    descriptor, name = tempfile.mkstemp(prefix=".env.import-", dir=env_path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(original)
        set_key(temporary, key, account.secret, quote_mode="always")
        expected = {**before, key: account.secret}
        if dotenv_values(temporary, interpolate=False) != expected:
            raise TotpImportError("Falha na conferência do .env; arquivo original preservado.")
        if env_path.read_bytes() != original:
            raise TotpImportError("O .env foi editado durante a importação; tente novamente para preservar suas mudanças.")
        temporary.chmod(0o600)
        temporary.replace(env_path)
    finally:
        temporary.unlink(missing_ok=True)
    return key, True


def _hidden_input(prompt):
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            return getpass.getpass(prompt)
        except getpass.GetPassWarning:
            raise TotpImportError("Execute em um terminal interativo com entrada oculta.") from None


def _label(value):
    # Evita controles de terminal vindos dos nomes contidos no QR.
    return "".join(char for char in value if char.isprintable())[:200] or "não informado"


def main(argv=None):
    parser = _ArgumentParser(description="Decodifica um QR de exportação do Google Authenticator localmente, sem rede nem exibição da chave.")
    parser.add_argument("--titular", choices=("cristiano", "murilo"), required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--salvar", action="store_true", help="Confere um código do app e grava somente o segredo TOTP do titular no .env raiz.")
    mode.add_argument("--diagnostico", action="store_true", help="Mostra somente versão, lote e enums; não grava nem revela o segredo.")
    args = parser.parse_args(argv)
    try:
        content = _hidden_input("Cole a URI completa ou a linha QR-Code: (entrada oculta): ")
        if args.diagnostico:
            metadata = inspect_export(content)
            print(f"Versão: {metadata['version']} (campo presente: {metadata['version_present']})")
            print(f"Lote: tamanho={metadata['batch_size']}; índice={metadata['batch_index']}")
            print(f"Cadastros neste QR: {metadata['account_count']}")
            for index, parameters in enumerate(metadata["parameters"], 1):
                print(f"Cadastro {index}: algoritmo_enum={parameters['algorithm_enum']}; digitos_enum={parameters['digits_enum']}; tipo_enum={parameters['type_enum']}")
            print("Diagnóstico concluído. Nenhuma chave exibida e nenhum arquivo alterado.")
            return 0
        account = decode_export(content)
        print(f"Cadastro: {_label(account.name)} | Emissor: {_label(account.issuer)}")
        print("Parâmetros compatíveis: TOTP / SHA1 / 6 dígitos; coletor com período de 30 segundos.")
        if not args.salvar:
            print("Inspeção concluída. Para gravar após conferir o app, execute novamente com --salvar.")
            return 0
        print(f"Destino: segredo TOTP de {args.titular.upper()} no .env raiz. Confira se o cadastro acima é o correto.")
        check_app_code(account, _hidden_input("Código atual de seis dígitos desse cadastro no Authenticator: "))
        key, changed = save_secret(ROOT_ENV, account, args.titular)
        print("Código coincide com o app (tolerância de um intervalo).")
        if changed:
            print(f"{key} atualizado; permissão 600. Chave não exibida.")
        else:
            print(f"A chave exportada já coincide com {key}; o conteúdo do .env foi preservado. Permissão 600.")
        print("Fora de uma coleta ativa, atualize a montagem dos serviços:")
        print("docker compose up -d --force-recreate --no-deps backend worker")
        print("A aceitação pelo TJRN ainda precisa ser testada.")
        return 0
    except (TotpImportError, OSError) as error:
        message = str(error) if isinstance(error, TotpImportError) else "Não foi possível ler ou atualizar o .env; confira suas permissões."
        print(f"Erro: {message}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nImportação interrompida.", file=sys.stderr)
        return 130
