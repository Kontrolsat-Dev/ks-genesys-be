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


def _get_extra(extra: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    """
    Lê um comando de extra ou extra["extra_fields"].

    Dá prioridade ao topo, depois a extra_fields.
    """
    if not isinstance(extra, dict):
        return default
    if key in extra and extra[key] is not None:
        return extra[key]
    ef = extra.get("extra_fields")
    if isinstance(ef, dict) and key in ef and ef[key] is not None:
        return ef[key]
    return default


class FtpDownloader:
    """
    Downloader FTP/FTPS simples para feeds.

    Host/porta/credenciais podem vir:
      - embutidos no URL (ftp://user:pass@host:21/path)
      - ou em auth_json com chaves: host/hostname/server/ftp_hostname,
        username/user/ftp_username, password/pass/ftp_password, port.

    Suporta ainda comandos em extra / extra["extra_fields"]:
      - ftp_file_ext: "csv", "zip", ... (filtra ficheiros por extensão)
      - ftp_auto_latest: "1"/"true"/"yes"/"on" → escolhe ficheiro mais "recente"
      - ftp_dir: diretoria específica (ex.: "/feeds")
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
        extra: dict[str, Any] | None = None,
    ) -> tuple[int, str | None, bytes, str | None]:
        """
        Faz download via FTP/FTPS.

        Devolve (status_code, content_type_guess, raw_bytes, error_text).
        Em caso de erro devolve status_code 599 e error_text com a mensagem.
        """
        timeout = int(timeout_s or self.timeout_s)

        def _run_sync() -> tuple[int, str | None, bytes, str | None]:
            import ftplib  # stdlib

            parsed = urlparse(url or "")
            scheme = (parsed.scheme or "").lower()
            host = parsed.hostname
            port = parsed.port or 21
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

            if ak == "ftp_password" and isinstance(auth, dict):
                user = auth.get("username") or auth.get("user") or auth.get("ftp_username") or user
                pwd = auth.get("password") or auth.get("pass") or auth.get("ftp_password") or pwd

            if not host:
                return 599, None, b"", "FTP host not provided"

            user = user or "anonymous"
            pwd = pwd or "anonymous@"

            # ---- comandos extra: auto-latest + extensão + diretoria ----
            ftp_file_ext_raw = _get_extra(extra, "ftp_file_ext")
            ftp_file_ext = ""
            if isinstance(ftp_file_ext_raw, str) and ftp_file_ext_raw.strip():
                ftp_file_ext = ftp_file_ext_raw.lower().lstrip(".")

            ftp_auto_latest_raw = _get_extra(extra, "ftp_auto_latest")
            ftp_auto_latest = False
            if ftp_auto_latest_raw is not None:
                ftp_auto_latest = str(ftp_auto_latest_raw).lower() in {
                    "1",
                    "true",
                    "yes",
                    "on",
                }

            ftp_dir_extra = _get_extra(extra, "ftp_dir")

            path_local = path or ""
            ftp_cls = ftplib.FTP_TLS if scheme == "ftps" else ftplib.FTP

            try:
                with ftp_cls() as ftp:
                    ftp.connect(host, port, timeout=timeout)
                    ftp.login(user, pwd)
                    ftp.set_pasv(True)

                    target_path = path_local
                    is_dir = False
                    dir_path: str | None = None

                    if ftp_auto_latest:
                        # modo auto-latest: lista sempre diretoria
                        if isinstance(ftp_dir_extra, str) and ftp_dir_extra.strip():
                            dir_path = ftp_dir_extra
                        else:
                            # se o path começa por '/', assumimos diretoria; senão, root
                            if path_local.startswith("/"):
                                dir_path = path_local
                            else:
                                dir_path = "."
                        is_dir = True
                    else:
                        # comportamento "normal": diretoria se vazio, '/', '.', ou terminar em '/'
                        is_dir = path_local in {"", "/", "."} or path_local.endswith("/")
                        if is_dir:
                            dir_path = path_local or "."

                    if is_dir:
                        listing = ftp.nlst(dir_path or ".")
                        candidates: list[str] = []

                        for name in listing:
                            if not name:
                                continue
                            base = name.rsplit("/", 1)[-1]
                            if base in {".", "..", ".ftpquota"}:
                                continue

                            if ftp_file_ext and not base.lower().endswith("." + ftp_file_ext):
                                continue

                            candidates.append(name)

                        if not candidates:
                            return (
                                404,
                                None,
                                b"",
                                "No matching files found in FTP directory",
                            )

                        # ordenação determinística por nome
                        candidates_sorted = sorted(candidates)
                        chosen = candidates_sorted[-1] if ftp_auto_latest else candidates_sorted[0]
                        target_path = chosen

                    # se não for diretoria nem auto-latest, target_path = path_local

                    chunks: list[bytes] = []

                    def _collector(data: bytes) -> None:
                        chunks.append(data)

                    ftp.retrbinary(f"RETR {target_path}", _collector)
                    raw = b"".join(chunks)

                    # Se não quiseres apagar no fornecedor, comenta isto:
                    try:
                        ftp.delete(target_path)
                    except Exception:
                        pass

                    ct = _guess_content_type_from_path(target_path)
                    return 200, ct, raw, None
            except Exception as e:
                return 599, None, b"", str(e)

        try:
            return await asyncio.to_thread(_run_sync)
        except Exception as e:
            return 599, None, b"", str(e)
