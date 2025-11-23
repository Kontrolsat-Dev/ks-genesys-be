from __future__ import annotations

import csv
import io
import json
import zipfile
from typing import Any
from urllib.parse import urlparse

from app.external.ftp_downloader import FtpDownloader
from app.external.http_downloader import HttpDownloader
from app.external.sftp_downloader import SftpDownloader
from app.schemas.feeds import FeedTestRequest, FeedTestResponse

MAX_PREVIEW_BYTES = 256 * 1024


def _looks_like_html(raw: bytes) -> bool:
    if not raw:
        return False
    start = raw.lstrip()[:64].lower()
    return start.startswith(b"<!doctype html") or start.startswith(b"<html")


def _charset_from_content_type(ct: str | None) -> str | None:
    if not ct:
        return None
    for part in ct.split(";"):
        part = part.strip().lower()
        if part.startswith("charset="):
            return part.split("=", 1)[1].strip()
    return None


def _infer_format(format_hint: str | None, content_type: str | None, sample: bytes) -> str:
    """
    Decide 'json' vs 'csv' quando o cliente não define explicitamente.
    """
    if format_hint:
        return format_hint.lower()

    ct = (content_type or "").lower()
    if "application/json" in ct or "ld+json" in ct or "json" in ct:
        return "json"
    if "text/csv" in ct:
        return "csv"

    # Heurística rápida pelo conteúdo
    s = sample.lstrip()[:1]
    if s in (b"{", b"["):
        return "json"
    return "csv"


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

    Útil para:
      - compression, zip_entry_name, zip_entry_ext
      - trigger_http_* (na _run_trigger)
    """
    if not isinstance(extra, dict):
        return default
    if key in extra and extra[key] is not None:
        return extra[key]
    ef = extra.get("extra_fields")
    if isinstance(ef, dict) and key in ef and ef[key] is not None:
        return ef[key]
    return default


class FeedDownloader:
    """
    Orquestrador de download/preview de feeds HTTP/FTP/SFTP.

    - Para HTTP, delega em HttpDownloader;
    - Para FTP/FTPS, delega em FtpDownloader;
    - Para SFTP (sftp://), delega em SftpDownloader;
    - Suporta triggers HTTP para feeds FTP/SFTP via extra/extra_fields:
        * trigger_http_url
        * trigger_http_method
        * trigger_http_headers
        * trigger_http_params
        * trigger_http_body_json
    - Suporta compressão ZIP via extra/extra_fields:
        * compression = "zip"
        * zip_entry_name = "ficheiro.csv" (opcional, nome específico)
        * zip_entry_ext = "csv" (opcional, preferir essa extensão)
    """

    def __init__(self, timeout_s: int | None = None) -> None:
        from app.core.config import settings  # import tardio para evitar ciclos

        self.timeout_s = int(timeout_s or getattr(settings, "FEED_DOWNLOAD_TIMEOUT", 30))
        self._http = HttpDownloader(timeout_s=self.timeout_s)
        self._ftp = FtpDownloader(timeout_s=self.timeout_s)
        self._sftp = SftpDownloader(timeout_s=self.timeout_s)

    # -------------------- API principal --------------------

    async def download_feed(
        self,
        *,
        kind: str | None,
        url: str,
        headers: dict[str, Any] | None,
        params: dict[str, Any] | None,
        auth_kind: str | None,
        auth: dict[str, Any] | None,
        extra: dict[str, Any] | None,
        timeout_s: int | None = None,
    ) -> tuple[int, str | None, bytes, str | None]:
        """
        Faz o download do feed, aplicando trigger_http e compressão (zip) se configurados.

        Devolve: (status_code, content_type, raw_bytes, error_text).
        """
        timeout = int(timeout_s or self.timeout_s)
        url = url or ""
        parsed = urlparse(url)
        scheme = (parsed.scheme or "").lower()
        ak = (auth_kind or "").lower()
        k = (kind or "").lower()

        is_sftp = scheme == "sftp" or k == "sftp" or ak == "sftp_password"
        is_ftp = (not is_sftp) and (k == "ftp" or scheme in {"ftp", "ftps"} or ak == "ftp_password")

        # 1) Trigger HTTP opcional (para feeds FTP/SFTP que precisam "abrir a torneira")
        if (is_ftp or is_sftp) and extra:
            await self._run_trigger(extra, timeout)

        # 2) Download principal
        if is_sftp:
            status_code, content_type, raw, err_text = await self._sftp.fetch(
                url=url,
                auth_kind=auth_kind,
                auth=auth,
                timeout_s=timeout,
                extra=extra,
            )
        elif is_ftp:
            status_code, content_type, raw, err_text = await self._ftp.fetch(
                url=url,
                auth_kind=auth_kind,
                auth=auth,
                timeout_s=timeout,
                extra=extra,
            )
        else:
            method: str | None = None
            body_json: Any = None
            if extra:
                m = extra.get("method")
                if isinstance(m, str):
                    method = m.upper() or None
                body = extra.get("body_json")
                if isinstance(body, (dict, list)):
                    body_json = body

            status_code, content_type, raw, err_text = await self._http.fetch(
                url=url,
                method=method or "GET",
                headers=headers,
                params=params,
                auth_kind=auth_kind,
                auth=auth,
                json_body=body_json,
                timeout_s=timeout,
            )

        # 3) Compressão (zip) opcional
        if 200 <= status_code < 300 and extra:
            compression = str(_get_extra(extra, "compression", "") or "").lower()
            if compression == "zip":
                try:
                    raw, content_type = self._decompress_zip(raw, content_type, extra)
                except Exception as e:
                    return 599, content_type, b"", f"zip decompression failed: {e}"

        return status_code, content_type, raw, err_text

    async def preview(self, req: FeedTestRequest) -> FeedTestResponse:
        """
        Usa download_feed para obter um sample e tenta inferir CSV/JSON,
        devolvendo apenas uma amostra de linhas.
        """
        try:
            status_code, ct, raw, err_text = await self.download_feed(
                kind=req.kind,
                url=req.url,
                headers=req.headers,
                params=req.params,
                auth_kind=req.auth_kind,
                auth=req.auth,
                extra=req.extra,
                timeout_s=self.timeout_s,
            )
        except Exception as e:
            return FeedTestResponse(
                ok=False,
                status_code=599,
                content_type=None,
                bytes_read=0,
                preview_type=None,
                rows_preview=[],
                error=str(e)[:300],
            )

        # falha HTTP/FTP/SFTP → devolve erro + pequeno corpo para debug
        if status_code < 200 or status_code >= 300:
            return FeedTestResponse(
                ok=False,
                status_code=status_code,
                content_type=ct,
                bytes_read=len(raw or b""),
                preview_type=None,
                rows_preview=[],
                error=(err_text or self._decode_best(raw, ct))[:300],
            )

        sample = (raw or b"")[:MAX_PREVIEW_BYTES]

        # decidir formato com base no sample
        fmt = _infer_format(req.format, ct, sample)

        # opcional: root da data (ex.: "productos", "data.items", etc.)
        json_root: str | None = None
        try:
            if isinstance(req.extra, dict):
                json_root_raw = _get_extra(req.extra, "json_root") or _get_extra(
                    req.extra, "data_root"
                )
                if isinstance(json_root_raw, str) and json_root_raw.strip():
                    json_root = json_root_raw.strip()
        except Exception:
            json_root = None

        if fmt == "json":
            # usar o corpo completo, não o sample truncado
            rows = parse_rows_json(raw or b"", root_key=json_root)
            rows = rows[: (req.max_rows or 20)]
            return FeedTestResponse(
                ok=True,
                status_code=status_code,
                content_type=ct,
                bytes_read=len(raw or b""),
                preview_type="json",
                rows_preview=rows,
                error=None,
            )

        # default → CSV
        rows = parse_rows_csv(
            sample,
            delimiter=(req.csv_delimiter or ","),
            max_rows=(req.max_rows or 20),
        )
        return FeedTestResponse(
            ok=True,
            status_code=status_code,
            content_type=ct,
            bytes_read=len(raw or b""),
            preview_type="csv",
            rows_preview=rows,
            error=None,
        )

    # -------------------- Helpers internos --------------------

    async def _run_trigger(self, extra: dict[str, Any], timeout_s: int) -> None:
        """
        Executa trigger HTTP opcional (para feeds que precisam de "abrir a torneira"
        antes de ler o ficheiro real, típico em alguns fornecedores via FTP/SFTP).

        Lê as chaves quer em extra quer em extra["extra_fields"].
        """
        if not extra:
            return

        url = _get_extra(extra, "trigger_http_url")
        if not url:
            return

        method_raw = _get_extra(extra, "trigger_http_method")
        method = str(method_raw).upper() if method_raw else "GET"

        headers = _get_extra(extra, "trigger_http_headers")
        if not isinstance(headers, dict):
            headers = None

        params = _get_extra(extra, "trigger_http_params")
        if not isinstance(params, dict):
            params = None

        body_json = _get_extra(extra, "trigger_http_body_json")
        if not isinstance(body_json, (dict, list)):
            body_json = None

        status, _ct, _raw, err = await self._http.fetch(
            url=url,
            method=method or "GET",
            headers=headers,
            params=params,
            auth_kind=None,
            auth=None,
            json_body=body_json,
            timeout_s=timeout_s,
        )
        if status < 200 or status >= 300:
            msg = err or f"trigger_http failed with HTTP {status}"
            raise RuntimeError(msg)

    def _decompress_zip(
        self,
        raw: bytes,
        content_type: str | None,
        extra: dict[str, Any],
    ) -> tuple[bytes, str | None]:
        """
        Descomprime ZIP em memória e devolve (conteúdo_extraído, content_type_ajustado).

        Comandos em extra/extra_fields:
          - zip_entry_name: nome específico do ficheiro dentro do ZIP
          - zip_entry_ext: extensão preferida (ex.: "csv")

        Caso zip_entry_name não seja fornecido, tenta:
          1) escolher ficheiro com a extensão zip_entry_ext se existir;
          2) caso contrário, o primeiro ficheiro "real" (não diretoria).
        """
        if not raw:
            raise ValueError("empty payload for zip decompression")

        # verificação leve de assinatura ZIP
        if len(raw) < 4 or not raw.startswith(b"PK\x03\x04"):
            raise ValueError("payload does not look like a ZIP file")

        bio = io.BytesIO(raw)
        with zipfile.ZipFile(bio) as zf:
            members = zf.infolist()
            if not members:
                raise ValueError("zip archive is empty")

            # comandos
            entry_name = _get_extra(extra, "zip_entry_name")
            entry_ext_raw = _get_extra(extra, "zip_entry_ext")
            entry_ext: str | None = None
            if isinstance(entry_ext_raw, str) and entry_ext_raw.strip():
                entry_ext = entry_ext_raw.lower().lstrip(".")

            def _is_dir(info: zipfile.ZipInfo) -> bool:
                is_dir_attr = getattr(info, "is_dir", None)
                if callable(is_dir_attr):
                    return is_dir_attr()
                return info.filename.endswith("/")

            chosen: zipfile.ZipInfo | None = None

            # 1) Nome específico (se fornecido)
            if isinstance(entry_name, str) and entry_name.strip():
                wanted = entry_name.strip()
                wanted_lower = wanted.lower()

                # match exato e por basename (case-sensitive)
                for info in members:
                    if _is_dir(info):
                        continue
                    name = info.filename
                    base = name.rsplit("/", 1)[-1]
                    if name == wanted or base == wanted:
                        chosen = info
                        break

                # fallback case-insensitive
                if chosen is None:
                    for info in members:
                        if _is_dir(info):
                            continue
                        name = info.filename
                        base = name.rsplit("/", 1)[-1]
                        if name.lower() == wanted_lower or base.lower() == wanted_lower:
                            chosen = info
                            break

                if chosen is None:
                    raise ValueError(f"zip entry '{entry_name}' not found")

            # 2) Extensão preferida (se não houve nome específico)
            if chosen is None and entry_ext:
                candidates: list[zipfile.ZipInfo] = []
                for info in members:
                    if _is_dir(info):
                        continue
                    base = info.filename.rsplit("/", 1)[-1]
                    if base.lower().endswith("." + entry_ext):
                        candidates.append(info)

                if len(candidates) == 1:
                    chosen = candidates[0]
                elif len(candidates) > 1:
                    candidates.sort(key=lambda i: i.filename)
                    chosen = candidates[-1]

            # 3) Fallback: primeiro ficheiro "real"
            if chosen is None:
                for info in members:
                    if not _is_dir(info):
                        chosen = info
                        break

            if chosen is None:
                raise ValueError("no file entries found inside zip archive")

            data = zf.read(chosen.filename)
            new_ct = content_type
            if not new_ct or new_ct == "application/zip":
                new_ct = _guess_content_type_from_path(chosen.filename)
            return data, new_ct

    @staticmethod
    def _decode_best(raw: bytes, ct: str | None) -> str:
        if not raw:
            return ""
        enc = _charset_from_content_type(ct)
        tried: list[str] = []
        if enc:
            tried.append(enc)
        for codec in tried + ["utf-8", "latin-1"]:
            try:
                return raw.decode(codec, errors="ignore")
            except Exception:
                continue
        return raw.decode("utf-8", errors="ignore")


# --------------- Funções utilitárias (compat) ----------------


async def http_download(
    url: str,
    *,
    headers: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout_s: int = 30,
    auth_kind: str | None = None,
    auth: dict[str, Any] | None = None,
) -> tuple[int, str | None, bytes]:
    """
    Wrapper fino sobre FeedDownloader.download_feed para manter APIs antigas.
    Decide HTTP vs FTP/SFTP em função do kind/url/auth_kind.
    """
    downloader = FeedDownloader(timeout_s=timeout_s)
    try:
        status, ct, raw, _err = await downloader.download_feed(
            kind=None,
            url=url,
            headers=headers,
            params=params,
            auth_kind=auth_kind,
            auth=auth,
            extra=None,
            timeout_s=timeout_s,
        )
    except Exception:
        return 599, None, b""
    return status, ct, raw


def parse_rows_json(raw: bytes, *, root_key: str | None = None) -> list[dict]:
    """
    Extrai linhas (dicts) de JSON:

    - lista direta
    - dict com root explícita (root_key, ex.: "productos" ou "data.items")
    - dict com chaves standard: data|items|results|products|productos|rows|list
    - ou NDJSON (uma linha JSON por linha)
    """
    # 1) JSON tradicional
    try:
        obj = json.loads(raw.decode(errors="ignore"))

        # Se tiver root_key configurado (ex.: "productos" ou "data.items")
        if root_key:
            cur: Any = obj
            for part in str(root_key).split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    cur = None
                    break

            if isinstance(cur, list):
                return [x for x in cur if isinstance(x, dict)]
            # se cairmos num dict, usamos heurística abaixo sobre esse dict
            if isinstance(cur, dict):
                obj = cur

        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]

        if isinstance(obj, dict):
            for key in (
                "data",
                "items",
                "results",
                "products",
                "productos",
                "rows",
                "list",
            ):
                v = obj.get(key)
                if isinstance(v, list):
                    return [x for x in v if isinstance(x, dict)]
            return [obj]
    except Exception:
        pass

    # 2) NDJSON (cada linha um JSON por linha)
    out: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            val = json.loads(line.decode(errors="ignore"))
            if isinstance(val, dict):
                out.append(val)
        except Exception:
            continue
    return out


def parse_rows_csv(
    raw: bytes,
    *,
    delimiter: str = ",",
    max_rows: int | None = None,
) -> list[dict]:
    """
    Converte CSV → lista de dicts (usando 1ª linha como cabeçalho).
    """
    text = FeedDownloader._decode_best(raw, ct="text/csv; charset=utf-8")
    # Remove BOM se existir
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")

    sio = io.StringIO(text)
    reader = csv.DictReader(
        sio,
        delimiter=(delimiter or ","),
        restkey="_extra",
        restval="",
    )

    out: list[dict] = []
    for i, row in enumerate(reader, 1):
        clean: dict[str, Any] = {}
        for k, v in row.items():
            if k is None:
                continue
            key = str(k).strip() or f"col_{len(clean) + 1}"
            if isinstance(v, list):
                v = ",".join("" if x is None else str(x) for x in v)
            clean[key] = "" if v is None else v
        out.append(clean)
        if max_rows and i >= max_rows:
            break
    return out
