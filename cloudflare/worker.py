import json
import time
import hmac
import hashlib
import secrets
from urllib.parse import urlparse, parse_qs
from workers import WorkerEntrypoint, Response

MAX_AGE_SECONDS = 15552000  # 180 days
KV_KEY_PREFIX = "post:"
COOKIE_PREFIX = "upvote_"
COOKIE_SECRET_ENV = "UPVOTE_COOKIE_SECRET"
KV_BINDING_NAME = "UPVOTES"


def _hash_slug(slug: str) -> str:
    return hashlib.sha1(slug.encode("utf-8")).hexdigest()


def _cookie_name(slug: str) -> str:
    return f"{COOKIE_PREFIX}{_hash_slug(slug)}"


def _sign_cookie(slug: str, timestamp: str, secret: str) -> str:
    payload = f"{slug}|{timestamp}".encode("utf-8")
    secret_bytes = secret.encode("utf-8")
    return hmac.new(secret_bytes, payload, hashlib.sha256).hexdigest()


def _build_cookie(slug: str, secret: str) -> str:
    timestamp = str(int(time.time()))
    signature = _sign_cookie(slug, timestamp, secret)
    value = f"{slug}|{timestamp}|{signature}"
    parts = [
        f"{_cookie_name(slug)}={value}",
        f"Max-Age={MAX_AGE_SECONDS}",
        "Path=/",
        "HttpOnly",
        "Secure",
        "SameSite=Lax",
    ]
    return "; ".join(parts)


def _parse_cookies(header_value: str | None) -> dict[str, str]:
    cookies: dict[str, str] = {}
    if not header_value:
        return cookies
    for item in header_value.split(";"):
        if "=" not in item:
            continue
        name, value = item.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


def _is_cookie_valid(slug: str, secret: str, cookie_value: str) -> bool:
    segments = cookie_value.split("|")
    if len(segments) != 3:
        return False
    cookie_slug, timestamp_str, provided_sig = segments
    if cookie_slug != slug or not timestamp_str.isdigit():
        return False
    timestamp = int(timestamp_str)
    if int(time.time()) - timestamp > MAX_AGE_SECONDS:
        return False
    expected_sig = _sign_cookie(slug, timestamp_str, secret)
    return hmac.compare_digest(expected_sig, provided_sig)


def _build_cors_headers(origin: str | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Headers"] = "Content-Type"
        headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        headers["Vary"] = "Origin"
    return headers


def _json_response(payload: dict, status: int = 200, headers: dict | None = None,
                   origin: str | None = None, set_cookie: str | None = None):
    base_headers = {"content-type": "application/json; charset=utf-8"}
    base_headers.update(_build_cors_headers(origin))
    if headers:
        base_headers.update(headers)
    if set_cookie:
        base_headers["Set-Cookie"] = set_cookie
    body = json.dumps(payload)
    return Response(body, status=status, headers=base_headers)


def _error_response(message: str, status: int = 400, origin: str | None = None):
    return _json_response({"error": message}, status=status, origin=origin)


def _extract_slug_from_query(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get("slug", [""])[0]


def _validate_slug(slug: str) -> bool:
    return bool(slug) and slug.startswith("/")


async def _read_upvote_payload(request) -> dict:
    """
    Read a best-effort payload for /api/upvote.
    Supports JSON and (urlencoded/multipart) forms.
    """
    content_type = (request.headers.get("Content-Type", "") or "").split(";", 1)[0].strip().lower()

    if "application/json" in content_type:
        try:
            data = json.loads(await request.text())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    if content_type in ("application/x-www-form-urlencoded", "multipart/form-data"):
        try:
            form_data = await request.formData()
            if form_data:
                return {k: form_data.get(k) for k in ("slug", "title", "permalink", "dateISO")}
        except Exception:
            pass
        try:
            body = await request.text()
            parsed = parse_qs(body)
            return {k: parsed.get(k, [""])[0] for k in ("slug", "title", "permalink", "dateISO")}
        except Exception:
            return {}

    return {}


def _extract_origin(request) -> str | None:
    return request.headers.get("Origin")


def _get_cookie_value(request, slug: str) -> str | None:
    cookies = _parse_cookies(request.headers.get("Cookie"))
    return cookies.get(_cookie_name(slug))


def _kv_key(slug: str) -> str:
    return f"{KV_KEY_PREFIX}{slug}"


def _parse_int(value: str | None, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _extract_query_first(url: str, key: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get(key, [""])[0]


def _sanitize_text(value: str, max_len: int) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    return value[:max_len]


def _sanitize_permalink(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    # Accept relative permalinks only; avoid storing arbitrary external URLs.
    if not value.startswith("/"):
        return ""
    return value[:2048]


def _sanitize_date_iso(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    # Keep it simple: YYYY-MM-DD
    if len(value) != 10:
        return ""
    if value[4] != "-" or value[7] != "-":
        return ""
    y, m, d = value[0:4], value[5:7], value[8:10]
    if not (y.isdigit() and m.isdigit() and d.isdigit()):
        return ""
    return value


def _default_post_record(count: int = 0) -> dict:
    return {
        "count": int(count),
        "title": "",
        "permalink": "",
        "dateISO": "",
        "updated_at": 0,
    }


def _parse_post_record(raw: str | None) -> tuple[dict, bool]:
    """
    Returns (record, needs_migration).
    """
    if not raw:
        return _default_post_record(0), False

    raw = str(raw).strip()
    if not raw:
        return _default_post_record(0), False

    # Primary: JSON record.
    try:
        data = json.loads(raw)
    except Exception:
        data = None

    if isinstance(data, dict):
        count = data.get("count")
        if not isinstance(count, int):
            count = _parse_int(str(count) if count is not None else None, default=0)

        out = _default_post_record(count)
        if isinstance(data.get("title"), str):
            out["title"] = _sanitize_text(data.get("title", ""), 256)
        if isinstance(data.get("permalink"), str):
            out["permalink"] = _sanitize_permalink(data.get("permalink", ""))
        if isinstance(data.get("dateISO"), str):
            out["dateISO"] = _sanitize_date_iso(data.get("dateISO", ""))
        if isinstance(data.get("updated_at"), int):
            out["updated_at"] = int(data.get("updated_at", 0))
        return out, False

    # Migration path: legacy integer.
    count = _parse_int(raw, default=0)
    return _default_post_record(count), True


def _merge_meta_into_record(record: dict, title: str, permalink: str, date_iso: str) -> tuple[dict, bool]:
    """
    Merge optional meta fields into a record. Returns (record, changed).
    """
    changed = False
    title = _sanitize_text(title, 256)
    permalink = _sanitize_permalink(permalink)
    date_iso = _sanitize_date_iso(date_iso)

    if title and record.get("title") != title:
        record["title"] = title
        changed = True
    if permalink and record.get("permalink") != permalink:
        record["permalink"] = permalink
        changed = True
    if date_iso and record.get("dateISO") != date_iso:
        record["dateISO"] = date_iso
        changed = True

    if changed:
        record["updated_at"] = int(time.time())

    return record, changed


def _get_env_binding(env, name: str):
    try:
        return getattr(env, name)
    except AttributeError:
        pass
    try:
        return env[name]
    except Exception:
        return None


async def _maybe_await(value):
    return await value if hasattr(value, "__await__") else value


async def _kv_get(kv, key: str):
    return await _maybe_await(kv.get(key))


async def _kv_put(kv, key: str, value: str):
    return await _maybe_await(kv.put(key, value))


async def _resolve_cookie_secret(env, kv):
    """
    Resolve cookie secret from environment variables; fallback to KV if needed.
    """
    secret = _get_env_binding(env, COOKIE_SECRET_ENV)
    if isinstance(secret, str) and secret:
        return secret

    # Fallback to KV (plain text). Avoids deploy failures if secret missing in env.
    try:
        stored = await _kv_get(kv, "cookie_secret")
        if stored:
            return stored
    except Exception:
        pass

    # Generate and persist a new secret if nothing found.
    try:
        generated = secrets.token_hex(64)
        await _kv_put(kv, "cookie_secret", generated)
        return generated
    except Exception:
        return ""


async def _fetch_count(kv, slug: str) -> int:
    record = await _fetch_post_record(kv, slug)
    return int(record.get("count", 0) or 0)


async def _fetch_post_record(kv, slug: str) -> dict:
    raw = await _kv_get(kv, _kv_key(slug))
    record, needs_migration = _parse_post_record(raw)
    if needs_migration:
        # One-time migration: persist in the new JSON format.
        record["updated_at"] = int(time.time())
        try:
            await _kv_put(kv, _kv_key(slug), json.dumps(record))
        except Exception:
            pass
    return record


async def _write_post_record(kv, slug: str, record: dict):
    record = dict(record or {})
    record["count"] = int(record.get("count", 0) or 0)
    record["title"] = _sanitize_text(str(record.get("title", "") or ""), 256)
    record["permalink"] = _sanitize_permalink(str(record.get("permalink", "") or ""))
    record["dateISO"] = _sanitize_date_iso(str(record.get("dateISO", "") or ""))
    record["updated_at"] = int(record.get("updated_at", 0) or 0)
    await _kv_put(kv, _kv_key(slug), json.dumps(record))


async def _handle_get(request, kv, origin: str | None, secret: str):
    slug = _extract_slug_from_query(request.url)
    if not _validate_slug(slug):
        return _error_response("slug must start with '/' and not be empty", origin=origin)

    cookie_value = _get_cookie_value(request, slug)
    upvoted = bool(cookie_value and _is_cookie_valid(slug, secret, cookie_value))
    record = await _fetch_post_record(kv, slug)

    # Optional metadata backfill (best-effort). Do not create KV entries for never-upvoted posts.
    title = _extract_query_first(request.url, "title")
    permalink = _extract_query_first(request.url, "permalink")
    date_iso = _extract_query_first(request.url, "dateISO")
    record, changed = _merge_meta_into_record(record, title, permalink, date_iso)

    count = int(record.get("count", 0) or 0)
    if changed and count > 0:
        try:
            await _write_post_record(kv, slug, record)
        except Exception:
            pass
    return _json_response({
        "slug": slug,
        "upvote_count": count,
        "upvoted": upvoted,
    }, origin=origin)


async def _handle_post(request, kv, origin: str | None, secret: str):
    payload = await _read_upvote_payload(request)
    slug = payload.get("slug", "") if isinstance(payload, dict) else ""
    if not isinstance(slug, str) or not slug:
        slug = _extract_slug_from_query(request.url)
    if not _validate_slug(slug):
        return _error_response("slug must start with '/' and not be empty", origin=origin)

    title = payload.get("title", "") if isinstance(payload, dict) else ""
    permalink = payload.get("permalink", "") if isinstance(payload, dict) else ""
    date_iso = payload.get("dateISO", "") if isinstance(payload, dict) else ""

    cookie_value = _get_cookie_value(request, slug)
    if cookie_value and _is_cookie_valid(slug, secret, cookie_value):
        record = await _fetch_post_record(kv, slug)
        record, changed = _merge_meta_into_record(record, str(title or ""), str(permalink or ""), str(date_iso or ""))
        count = int(record.get("count", 0) or 0)
        if changed and count > 0:
            try:
                await _write_post_record(kv, slug, record)
            except Exception:
                pass
        return _json_response({
            "slug": slug,
            "upvote_count": count,
            "upvoted": True,
        }, origin=origin)

    record = await _fetch_post_record(kv, slug)
    record["count"] = int(record.get("count", 0) or 0) + 1
    record, _ = _merge_meta_into_record(record, str(title or ""), str(permalink or ""), str(date_iso or ""))
    try:
        await _write_post_record(kv, slug, record)
    except Exception:
        pass
    count = int(record.get("count", 0) or 0)
    cookie_header = _build_cookie(slug, secret)
    return _json_response({
        "slug": slug,
        "upvote_count": count,
        "upvoted": True,
    }, origin=origin, set_cookie=cookie_header)


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        env = self.env
        origin = _extract_origin(request)
        method = request.method.upper()

        if method == "OPTIONS":
            headers = _build_cors_headers(origin)
            headers.setdefault("content-length", "0")
            return Response("", status=204, headers=headers)

        kv_binding = _get_env_binding(env, KV_BINDING_NAME)
        if not kv_binding:
            return _error_response("Server misconfiguration", status=500, origin=origin)
        secret = await _resolve_cookie_secret(env, kv_binding)
        if not secret:
            return _error_response("Server misconfiguration", status=500, origin=origin)

        path = urlparse(request.url).path

        if path == "/api/upvote-info" and method == "GET":
            return await _handle_get(request, kv_binding, origin, secret)

        if path == "/api/upvote" and method == "POST":
            return await _handle_post(request, kv_binding, origin, secret)

        # Fallback to static assets (demo site).
        assets = _get_env_binding(env, "ASSETS")
        if assets:
            return await assets.fetch(request)

        return _error_response("Not found", status=404, origin=origin)
