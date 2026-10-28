#!/usr/bin/env python3
"""Entrada local; não inicia Django, Docker, navegador nem autenticação remota."""

from automation.totp_import import main


if __name__ == "__main__":
    raise SystemExit(main())
