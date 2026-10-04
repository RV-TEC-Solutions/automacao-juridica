"""Motor Criptográfico A1 Headless para PJe (Rota B).

Executa operações criptográficas ICP-Brasil em memória sem persistir chaves privadas em disco.
Suporta:
- Decodificação de contêiner PKCS#12 (.pfx/.p12) via Base64 ou arquivo local;
- Assinatura PKCS#7 / CMS Detached (SHA-256) para responder desafios de login (nonce);
- Assinatura CAdES-BES para documentos PDF no fluxo de peticionamento automático;
- Extração de certificados públicos e metadados de identidade (CPF, OAB, validade).
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12, pkcs7


class A1CryptoError(RuntimeError):
    """Erro em operações do motor criptográfico A1."""


@dataclass(frozen=True)
class CertificateInfo:
    """Metadados extraídos do certificado digital X.509."""
    common_name: str
    cpf: str | None
    oab: str | None
    not_valid_before: datetime
    not_valid_after: datetime
    serial_number: int
    issuer_common_name: str

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.not_valid_after

    @property
    def days_until_expiration(self) -> int:
        delta = self.not_valid_after - datetime.now(timezone.utc)
        return delta.days


class A1CryptoEngine:
    """Motor Criptográfico de alta performance em memória para automação PJe Headless."""

    def __init__(self, private_key: rsa.RSAPrivateKey, certificate: x509.Certificate, additional_certs: list[x509.Certificate] | None = None):
        self._private_key = private_key
        self._certificate = certificate
        self._additional_certs = additional_certs or []
        self._cert_info = self._extract_cert_info()

    @property
    def cert_info(self) -> CertificateInfo:
        return self._cert_info

    @property
    def certificate(self) -> x509.Certificate:
        return self._certificate

    @property
    def private_key(self) -> rsa.RSAPrivateKey:
        return self._private_key

    @property
    def additional_certs(self) -> list[x509.Certificate]:
        return list(self._additional_certs)

    @classmethod
    def from_env(cls) -> A1CryptoEngine:
        """Instancia o motor criptográfico a partir de variáveis de ambiente.

        Fontes suportadas:
        1. PJE_CERT_A1_BASE64: String Base64 do arquivo .pfx (recomendado para contêineres Docker/Secrets).
        2. PJE_CERT_A1_PATH: Caminho para o arquivo .pfx/.p12.
        Senha obtida de PJE_CERT_A1_PASSWORD ou PJE_CERT_PIN.
        """
        password = os.environ.get("PJE_CERT_A1_PASSWORD") or os.environ.get("PJE_CERT_PIN")
        if not password:
            raise A1CryptoError("Senha do certificado A1 não encontrada (defina PJE_CERT_A1_PASSWORD ou PJE_CERT_PIN).")

        b64_data = os.environ.get("PJE_CERT_A1_BASE64")
        if b64_data:
            try:
                pfx_bytes = base64.b64decode(b64_data)
                return cls.from_bytes(pfx_bytes, password)
            except Exception as exc:
                raise A1CryptoError(f"Falha ao decodificar PJE_CERT_A1_BASE64: {exc}") from exc

        path_str = os.environ.get("PJE_CERT_A1_PATH")
        if path_str:
            pfx_path = Path(path_str)
            if not pfx_path.is_file():
                raise A1CryptoError(f"Arquivo de certificado A1 não localizado: {path_str}")
            return cls.from_file(pfx_path, password)

        raise A1CryptoError(
            "Configuração do certificado A1 ausente. "
            "Defina PJE_CERT_A1_BASE64 ou PJE_CERT_A1_PATH e PJE_CERT_A1_PASSWORD."
        )

    @classmethod
    def from_file(cls, path: Path | str, password: str | bytes) -> A1CryptoEngine:
        path = Path(path)
        if not path.is_file():
            raise A1CryptoError(f"Arquivo não encontrado: {path}")
        return cls.from_bytes(path.read_bytes(), password)

    @classmethod
    def from_bytes(cls, pfx_bytes: bytes, password: str | bytes) -> A1CryptoEngine:
        pwd_bytes = password.encode("utf-8") if isinstance(password, str) else password
        try:
            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                pfx_bytes,
                pwd_bytes,
            )
        except Exception as exc:
            raise A1CryptoError(f"Falha ao abrir PKCS#12 (senha incorreta ou formato inválido): {exc}") from exc

        if private_key is None or certificate is None:
            raise A1CryptoError("O arquivo PKCS#12 não contém chave privada ou certificado X.509.")

        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise A1CryptoError(f"Chave privada incompatível (esperada RSA, encontrada {type(private_key)}).")

        return cls(private_key, certificate, additional_certs or [])

    @classmethod
    def create_ephemeral_test_engine(cls, common_name: str = "ADVOGADO HEADLESS:12345678900", oab: str = "5691/RN") -> tuple[A1CryptoEngine, bytes, str]:
        """Gera um certificado de testes auto-assinado válido em memória para suítes de teste."""
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(timezone.utc)
        subject = x509.Name([
            x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, "ICP-Brasil Test"),
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME, f"OAB-{oab}"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=365))
            .sign(key, hashes.SHA256())
        )
        test_pwd = "teste_headless_pwd"
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=b"test_headless",
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(test_pwd.encode("utf-8")),
        )
        engine = cls(key, cert, [])
        return engine, pfx_bytes, test_pwd

    def _extract_cert_info(self) -> CertificateInfo:
        cn = ""
        oab = None
        for attr in self._certificate.subject:
            if attr.oid == x509.oid.NameOID.COMMON_NAME:
                cn = str(attr.value)
            elif attr.oid == x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME:
                val = str(attr.value)
                if "OAB" in val.upper():
                    oab = val

        cpf_match = re.search(r":(\d{11})", cn)
        cpf = cpf_match.group(1) if cpf_match else None

        issuer_cn = ""
        for attr in self._certificate.issuer:
            if attr.oid == x509.oid.NameOID.COMMON_NAME:
                issuer_cn = str(attr.value)

        return CertificateInfo(
            common_name=cn,
            cpf=cpf,
            oab=oab,
            not_valid_before=self._certificate.not_valid_before_utc,
            not_valid_after=self._certificate.not_valid_after_utc,
            serial_number=self._certificate.serial_number,
            issuer_common_name=issuer_cn,
        )

    def sign_pkcs7_detached(self, data: bytes | str) -> str:
        """Gera envelope PKCS#7 / CMS Detached (SHA-256) em Base64.

        Formato DER exigido pelo PJe para responder ao desafio de login (nonce).
        O dado original não é duplicado no envelope (Detached).
        """
        data_bytes = data.encode("utf-8") if isinstance(data, str) else data

        builder = (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(data_bytes)
            .add_signer(self._certificate, self._private_key, hashes.SHA256())
            .add_certificate(self._certificate)
        )

        for ca_cert in self._additional_certs:
            builder.add_certificate(ca_cert)

        der_bytes = builder.sign(
            serialization.Encoding.DER,
            [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary],
        )
        return base64.b64encode(der_bytes).decode("ascii")

    def sign_document_cades(self, document_bytes: bytes) -> bytes:
        """Gera assinatura digital CAdES-BES para anexos e petições (PDF)."""
        builder = (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(document_bytes)
            .add_signer(self._certificate, self._private_key, hashes.SHA256())
            .add_certificate(self._certificate)
        )
        for ca_cert in self._additional_certs:
            builder.add_certificate(ca_cert)

        return builder.sign(
            serialization.Encoding.DER,
            [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary],
        )

    def get_certificate_der_base64(self) -> str:
        """Retorna o certificado público em DER codificado em Base64."""
        der_bytes = self._certificate.public_bytes(serialization.Encoding.DER)
        return base64.b64encode(der_bytes).decode("ascii")

    def get_certificate_chain_der_base64(self) -> list[str]:
        """Retorna a cadeia de certificados completa em Base64."""
        chain = [self.get_certificate_der_base64()]
        for cert in self._additional_certs:
            der_bytes = cert.public_bytes(serialization.Encoding.DER)
            chain.append(base64.b64encode(der_bytes).decode("ascii"))
        return chain
