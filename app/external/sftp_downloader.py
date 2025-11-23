from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings


def _guess_content_type_from_path(path: str | None) -> str | None:
    if not path:
        return None
    lower = path.lower()
    if lower.endswith(".json"):
        return "application/json"
    if lower.endswith(".csv"):
        return "text/csv"
    if lower.endswith(".txt"):
        return "text/plain"
    if lower.endswith(".zip"):
        return "application/zip"
    return None


class SftpDownloader:
    """
    Downloader SFTP simples (SSH, porto 22 por default).

    Host/porta/credenciais podem vir:
      - embutidos no URL (sftp://user:pass@host:22/path)
      - ou em auth_json com chaves: host/hostname/server/ftp_hostname,
        username/user/ftp_username, password/pass/ftp_password, port.

    Não faz listagens nem auto-latest; assume que o path é o ficheiro a descarregar.
    """

    def __init__(self, timeout_s: int | None = None) -> None:
        self.timeout_s = int(timeout_s or getattr(settings, "FEED_DOWNLOAD_TIMEOUT", 30))

    async def fetch(
        self,
        *,
        url: str,
        auth_kind: str | None = None,
        auth: dict[str, Any] | None = None,
        timeout_s: int | None = None,
        extra: dict[str, Any] | None = None,  # assinatura simétrica com FTP
    ) -> tuple[int, str | None, bytes, str | None]:
        """
        Faz download via SFTP.

        Devolve (status_code, content_type_guess, raw_bytes, error_text).
        Em caso de erro devolve status_code 599 e error_text com a mensagem.
        """
        timeout = int(timeout_s or self.timeout_s)

        def _run_sync() -> tuple[int, str | None, bytes, str | None]:
            import paramiko  # type: ignore[import]

            parsed = urlparse(url or "")
            scheme = (parsed.scheme or "").lower()
            if scheme != "sftp":
                return 599, None, b"", "Invalid scheme for SFTP (expected sftp://)"

            host = parsed.hostname
            port = parsed.port or 22
            path = parsed.path or ""

            # host/porta vindos de auth têm prioridade
            if isinstance(auth, dict):
                host_local = (
                    auth.get("host")
                    or auth.get("hostname")
                    or auth.get("server")
                    or auth.get("ftp_hostname")
                )
                if host_local:
                    host = str(host_local)
                port_val = auth.get("port")
                try:
                    if port_val is not None:
                        port = int(port_val)
                except Exception:
                    pass

            ak = (auth_kind or "").lower()
            user = parsed.username
            pwd = parsed.password

            if ak in {"ftp_password", "sftp_password"} and isinstance(auth, dict):
                user = auth.get("username") or auth.get("user") or auth.get("ftp_username") or user
                pwd = auth.get("password") or auth.get("pass") or auth.get("ftp_password") or pwd

            if not host:
                return 599, None, b"", "SFTP host not provided"

            if not path or path in {"/", "."}:
                return 599, None, b"", "SFTP path is required"

            user = user or "anonymous"
            pwd = pwd or ""

            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=host,
                    port=port,
                    username=user,
                    password=pwd,
                    timeout=timeout,
                )

                sftp = ssh.open_sftp()
                try:
                    with sftp.open(path, "rb") as f:
                        raw = f.read()
                finally:
                    sftp.close()
                    ssh.close()

                ct = _guess_content_type_from_path(path)
                return 200, ct, raw, None
            except Exception as e:
                return 599, None, b"", str(e)

        try:
            return await asyncio.to_thread(_run_sync)
        except Exception as e:
            return 599, None, b"", str(e)
