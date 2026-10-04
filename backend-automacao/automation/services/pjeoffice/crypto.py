"""Motor Criptográfico A1 para PJe.

Responsável pelo gerenciamento do certificado digital ICP-Brasil A1 (PKCS#12 / .pfx),
armazenamento seguro de chaves exclusivamente na memória RAM e geração de
assinaturas digitais PKCS#7 / CMS Detached (SHA-256) exigidas pelo PJe.
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
    """Exceção levantada para falhas de carregamento ou assinatura com certificado A1."""


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
    """Motor em memória para operações criptográficas com Certificado Digital A1."""

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
        """Carrega o certificado a partir de variáveis de ambiente.

        Prioridade:
        1. PJE_CERT_A1_BASE64: Conteúdo binário do .pfx codificado em Base64 (ideal para Docker/Secrets).
        2. PJE_CERT_A1_PATH: Caminho do arquivo .pfx/.p12 no sistema de arquivos.

        A senha é obtida de PJE_CERT_A1_PASSWORD ou PJE_CERT_PIN.
        """
        password = os.environ.get("PJE_CERT_A1_PASSWORD") or os.environ.get("PJE_CERT_PIN")
        if not password:
            raise A1CryptoError("Senha do certificado A1 não encontrada (configure PJE_CERT_A1_PASSWORD ou PJE_CERT_PIN).")

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
            if not pfx_path.exists():
                raise A1CryptoError(f"Arquivo de certificado A1 não encontrado em: {path_str}")
            return cls.from_file(pfx_path, password)

        raise A1CryptoError(
            "Nenhuma fonte para o certificado A1 foi configurada. "
            "Defina PJE_CERT_A1_BASE64 ou PJE_CERT_A1_PATH e PJE_CERT_A1_PASSWORD."
        )

    @classmethod
    def from_file(cls, path: Path | str, password: str | bytes) -> A1CryptoEngine:
        """Carrega o certificado A1 a partir de um arquivo .pfx/.p12."""
        path = Path(path)
        if not path.is_file():
            raise A1CryptoError(f"Arquivo não encontrado: {path}")
        pfx_bytes = path.read_bytes()
        return cls.from_bytes(pfx_bytes, password)

    @classmethod
    def from_bytes(cls, pfx_bytes: bytes, password: str | bytes) -> A1CryptoEngine:
        """Carrega e decifra o arquivo PKCS#12 diretamente na memória RAM."""
        if isinstance(password, str):
            pwd_bytes = password.encode("utf-8")
        else:
            pwd_bytes = password

        try:
            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                pfx_bytes,
                pwd_bytes,
            )
        except Exception as exc:
            raise A1CryptoError(f"Erro ao abrir arquivo PKCS#12 (senha incorreta ou formato inválido): {exc}") from exc

        if private_key is None or certificate is None:
            raise A1CryptoError("O arquivo PKCS#12 não contém par de chaves ou certificado público.")

        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise A1CryptoError(f"Tipo de chave privada não suportado pelo PJe (esperado RSA, recebido {type(private_key)}).")

        return cls(private_key, certificate, additional_certs or [])

    @classmethod
    def create_ephemeral_test_engine(cls, common_name: str = "TESTE ADVOGADO:12345678900", oab: str = "12345/RN") -> tuple[A1CryptoEngine, bytes, str]:
        """Cria um motor e certificado efêmero em memória para execução de testes automatizados."""
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
        test_pwd = "teste_password_123"
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=b"test_cert",
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(test_pwd.encode("utf-8")),
        )
        engine = cls(key, cert, [])
        return engine, pfx_bytes, test_pwd

    def _extract_cert_info(self) -> CertificateInfo:
        """Extrai dados relevantes do sujeito do certificado X.509."""
        cn = ""
        oab = None
        for attr in self._certificate.subject:
            if attr.oid == x509.oid.NameOID.COMMON_NAME:
                cn = str(attr.value)
            elif attr.oid == x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME:
                val = str(attr.value)
                if "OAB" in val.upper():
                    oab = val

        # CPF geralmente está no Common Name: 'NOME DO ADVOGADO:12345678901'
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
        """Gera uma assinatura CAdES / PKCS#7 Detached (SHA-256) em Base64.

        Este é o padrão exigido pelo PJe para responder desafios de login (nonce)
        e assinar requisições no PJeOffice. O dado original não é incorporado ao
        envelope DER (Detached), apenas o hash SHA-256 e o certificado assinante.
        """
        if isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

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

    def sign_pkcs7_attached(self, data: bytes | str) -> str:
        """Gera uma assinatura PKCS#7 Attached (onde os dados são embutidos)."""
        if isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

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
            [pkcs7.PKCS7Options.Binary],
        )
        return base64.b64encode(der_bytes).decode("ascii")

    def get_certificate_der_base64(self) -> str:
        """Retorna o certificado público X.509 em formato DER codificado em Base64."""
        der_bytes = self._certificate.public_bytes(serialization.Encoding.DER)
        return base64.b64encode(der_bytes).decode("ascii")

    def get_certificate_chain_der_base64(self) -> list[str]:
        """Retorna a cadeia completa de certificados (titular + intermediárias) em Base64."""
        chain = [self.get_certificate_der_base64()]
        for cert in self._additional_certs:
            der_bytes = cert.public_bytes(serialization.Encoding.DER)
            chain.append(base64.b64encode(der_bytes).decode("ascii"))
        return chain

    def get_certificate_pem(self) -> str:
        """Retorna o certificado público X.509 em formato PEM."""
        pem_bytes = self._certificate.public_bytes(serialization.Encoding.PEM)
        return pem_bytes.decode("ascii")
