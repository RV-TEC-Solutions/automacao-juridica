"""Persistência e normalização dos avisos exibidos pelo PJe."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.db import transaction
from django.utils import timezone

from automation.models import Notice, NoticeSource


ALLOWED_TAGS = {"a", "b", "br", "em", "i", "li", "ol", "p", "strong", "ul"}
ALLOWED_ATTRIBUTES = {"a": {"href"}}
METADATA = re.compile(
    r"Inclu[ií]da\s+por\s*(?P<author>.*?)\s*em\s*(?P<included>\d{2}/\d{2}/\d{4}(?:\s+\d{2}:\d{2})?)"
    r"\s*Publicado\s+em\s*(?P<published>\d{2}/\d{2}/\d{4})",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class ParsedNotice:
    title: str
    included_by: str
    included_at: datetime | None
    published_at: datetime | None
    raw_html: str
    content_html: str
    content_text: str
    links: list[str]
    fingerprint: str


def _parse_date(value: str, formats: tuple[str, ...]) -> datetime | None:
    for fmt in formats:
        try:
            return timezone.make_aware(datetime.strptime(value.strip(), fmt))
        except ValueError:
            continue
    return None


def _normal_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def sanitize_html(raw_html: str) -> tuple[str, str, list[str]]:
    soup = BeautifulSoup(raw_html, "html.parser")
    links: list[str] = []
    for element in list(soup.find_all(True)):
        if element.name in {"script", "style", "iframe", "object"}:
            element.decompose()
            continue
        if element.name not in ALLOWED_TAGS:
            element.unwrap()
            continue
        for attribute in list(element.attrs):
            if attribute not in ALLOWED_ATTRIBUTES.get(element.name, set()):
                del element.attrs[attribute]
        if element.name == "a":
            href = str(element.get("href", "")).strip()
            parsed = urlparse(href)
            if parsed.scheme not in {"http", "https"}:
                element.attrs.pop("href", None)
            elif href:
                element["href"] = href
                links.append(href)
    return str(soup), _normal_text(soup.get_text(" ", strip=True)), list(dict.fromkeys(links))


def parse_notice_card(raw_html: str) -> ParsedNotice:
    """Converte o HTML de um cartão PJe em uma representação canônica."""
    soup = BeautifulSoup(raw_html, "html.parser")
    title_element = soup.find("h3")
    metadata_element = soup.find("em")
    title = _normal_text(title_element.get_text(" ", strip=True) if title_element else "")
    metadata = _normal_text(metadata_element.get_text(" ", strip=True) if metadata_element else "")
    if not title or not metadata_element:
        raise RuntimeError("Cartão de aviso sem título ou metadados reconhecíveis.")
    match = METADATA.search(metadata)
    if not match:
        raise RuntimeError("Metadados do aviso não seguem o formato esperado.")

    title_element.decompose()
    metadata_element.decompose()
    for form in soup.find_all("form"):
        form.decompose()
    content_html, content_text, links = sanitize_html(str(soup))
    if not content_text:
        raise RuntimeError("Cartão de aviso sem conteúdo legível.")

    included_at = _parse_date(match.group("included"), ("%d/%m/%Y %H:%M", "%d/%m/%Y"))
    published_at = _parse_date(match.group("published"), ("%d/%m/%Y",))
    fingerprint_input = "\n".join((title.casefold(), match.group("published"), content_text.casefold()))
    return ParsedNotice(
        title=title,
        included_by=_normal_text(match.group("author")),
        included_at=included_at,
        published_at=published_at,
        raw_html=raw_html,
        content_html=content_html,
        content_text=content_text,
        links=links,
        fingerprint=hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest(),
    )


def persist_notices(cards: list[str], source) -> list[NoticeSource]:
    """Persiste cartões antes de qualquer confirmação irreversível no PJe."""
    parsed_cards = [parse_notice_card(card) for card in cards]
    links: list[NoticeSource] = []
    with transaction.atomic():
        for parsed in parsed_cards:
            notice, created = Notice.objects.get_or_create(
                fingerprint=parsed.fingerprint,
                defaults={
                    "title": parsed.title,
                    "included_by": parsed.included_by,
                    "included_at": parsed.included_at,
                    "published_at": parsed.published_at.date() if parsed.published_at else None,
                    "raw_html": parsed.raw_html,
                    "content_html": parsed.content_html,
                    "content_text": parsed.content_text,
                    "links": parsed.links,
                },
            )
            if not created:
                notice.updated_at = timezone.now()
                notice.save(update_fields=("updated_at",))
            link, _ = NoticeSource.objects.get_or_create(notice=notice, source=source)
            links.append(link)
    return links


def mark_confirmed(link: NoticeSource) -> None:
    link.pje_confirmed_at = timezone.now()
    link.save(update_fields=("pje_confirmed_at",))
