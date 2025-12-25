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

# Cached "most popular posts" list (rebuilt by cron).
POPULAR_CACHE_KEY = "popular_cache:v1"
POPULAR_CACHE_MAX_ENV = "POPULAR_CACHE_MAX"
POPULAR_CACHE_MAX_DEFAULT = 50


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


async def _read_post_slug(request) -> str:
    content_type = (request.headers.get("Content-Type", "") or "").split(";", 1)[0].strip().lower()

    if "application/json" in content_type:
        try:
            payload_text = await request.text()
            data = json.loads(payload_text)
        except Exception:
            return ""
        value = data.get("slug", "")
        return value if isinstance(value, str) else ""

    if content_type in ("application/x-www-form-urlencoded", "multipart/form-data"):
        try:
            form_data = await request.formData()
            value = form_data.get("slug") if form_data else None
            if isinstance(value, str) and value:
                return value
        except Exception:
            pass
        try:
            body = await request.text()
            parsed = parse_qs(body)
            return parsed.get("slug", [""])[0]
        except Exception:
            return ""

    return ""


def _extract_origin(request) -> str | None:
    return request.headers.get("Origin")


def _get_cookie_value(request, slug: str) -> str | None:
    cookies = _parse_cookies(request.headers.get("Cookie"))
    return cookies.get(_cookie_name(slug))


def _kv_key(slug: str) -> str:
    return f"{KV_KEY_PREFIX}{slug}"


def _clamp_int(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, value))


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


def _date_key(date_iso: str) -> int:
    date_iso = (date_iso or "").strip()
    if len(date_iso) != 10:
        return 0
    if date_iso[4] != "-" or date_iso[7] != "-":
        return 0
    y, m, d = date_iso[0:4], date_iso[5:7], date_iso[8:10]
    if not (y.isdigit() and m.isdigit() and d.isdigit()):
        return 0
    return (int(y) * 10000) + (int(m) * 100) + int(d)


def _default_post_record(count: int = 0) -> dict:
    return {
        "count": int(count),
        "title": "",
        "permalink": "",
        "dateISO": "",
        "updated_at": 0,
    }


def _parse_post_record(raw: str | None) -> dict:
    if not raw:
        return _default_post_record(0)

    # Legacy format: plain integer.
    as_int = _parse_int(raw, default=-1)
    if as_int >= 0 and str(as_int) == raw.strip():
        return _default_post_record(as_int)

    try:
        data = json.loads(raw)
    except Exception:
        return _default_post_record(0)

    if not isinstance(data, dict):
        return _default_post_record(0)

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
    return out


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


async def _resolve_cookie_secret(env, kv):
    """
    Resolve cookie secret from environment variables; fallback to KV if needed.
    """
    secret = _get_env_binding(env, COOKIE_SECRET_ENV)
    if isinstance(secret, str) and secret:
        return secret

    # Fallback to KV (plain text). Avoids deploy failures if secret missing in env.
    try:
        stored = await kv.get("cookie_secret")
        if stored:
            return stored
    except Exception:
        pass

    # Generate and persist a new secret if nothing found.
    try:
        generated = secrets.token_hex(64)
        await kv.put("cookie_secret", generated)
        return generated
    except Exception:
        return ""


async def _fetch_count(kv, slug: str) -> int:
    raw = await kv.get(_kv_key(slug))
    record = _parse_post_record(raw)
    return int(record.get("count", 0) or 0)


async def _fetch_post_record(kv, slug: str) -> dict:
    raw = await kv.get(_kv_key(slug))
    return _parse_post_record(raw)


async def _write_post_record(kv, slug: str, record: dict):
    record = dict(record or {})
    record["count"] = int(record.get("count", 0) or 0)
    record["title"] = _sanitize_text(str(record.get("title", "") or ""), 256)
    record["permalink"] = _sanitize_permalink(str(record.get("permalink", "") or ""))
    record["dateISO"] = _sanitize_date_iso(str(record.get("dateISO", "") or ""))
    record["updated_at"] = int(record.get("updated_at", 0) or 0)
    await kv.put(_kv_key(slug), json.dumps(record))


async def _kv_list_keys(kv, prefix: str, limit: int = 1000) -> list[str]:
    """
    Best-effort KV list() wrapper. Returns key names (strings).
    """
    out: list[str] = []
    cursor = None

    if not hasattr(kv, "list"):
        return out

    while True:
        resp = None
        params = {"prefix": prefix, "limit": int(limit)}
        if cursor:
            params["cursor"] = cursor

        # KV bindings differ slightly across runtimes; try kwargs then dict.
        try:
            resp = await kv.list(**params)  # type: ignore[arg-type]
        except TypeError:
            try:
                resp = await kv.list(params)  # type: ignore[arg-type]
            except Exception:
                break
        except Exception:
            break

        if resp is None:
            break

        # JS-style: { keys: [{ name }], list_complete: bool, cursor: str }
        if isinstance(resp, dict):
            keys = resp.get("keys")
            if isinstance(keys, list):
                for k in keys:
                    if isinstance(k, str):
                        out.append(k)
                    elif isinstance(k, dict) and isinstance(k.get("name"), str):
                        out.append(k["name"])

            list_complete = resp.get("list_complete")
            cursor = resp.get("cursor") if isinstance(resp.get("cursor"), str) else None

            if list_complete is True or not cursor:
                break
            continue

        # Some runtimes may return a plain list of names.
        if isinstance(resp, list):
            for k in resp:
                if isinstance(k, str):
                    out.append(k)
                elif isinstance(k, dict) and isinstance(k.get("name"), str):
                    out.append(k["name"])
            break

        break

    return out


async def _rebuild_popular_cache(env, kv) -> dict:
    """
    Build and store a cached popular list from KV counters.
    """
    max_items = _parse_int(_get_env_binding(env, POPULAR_CACHE_MAX_ENV), POPULAR_CACHE_MAX_DEFAULT)
    max_items = _clamp_int(max_items, 1, 200)

    key_names = await _kv_list_keys(kv, KV_KEY_PREFIX)
    items: list[dict] = []

    for name in key_names:
        if not isinstance(name, str) or not name.startswith(KV_KEY_PREFIX):
            continue
        slug = name[len(KV_KEY_PREFIX):]
        if not _validate_slug(slug):
            continue
        record = await _fetch_post_record(kv, slug)
        count = int(record.get("count", 0) or 0)
        title = str(record.get("title", "") or "")
        permalink = str(record.get("permalink", "") or "")
        date_iso = str(record.get("dateISO", "") or "")

        if not permalink:
            # Best-effort fallback; many Hugo sites use trailing slash.
            permalink = f"{slug}/" if slug != "/" else "/"
        if not title:
            title = slug

        items.append({
            "slug": slug,
            "title": title,
            "permalink": permalink,
            "dateISO": date_iso,
            "upvote_count": count,
        })

    items.sort(
        key=lambda it: (
            (it.get("upvote_count", 0) or 0),
            _date_key(str(it.get("dateISO", "") or "")),
        ),
        reverse=True,
    )
    items = items[:max_items]

    payload = {
        "generated_at": int(time.time()),
        "items": items,
    }
    await kv.put(POPULAR_CACHE_KEY, json.dumps(payload))
    return payload


async def _handle_get(request, kv, origin: str | None, secret: str):
    slug = _extract_slug_from_query(request.url)
    if not _validate_slug(slug):
        return _error_response("slug must start with '/' and not be empty", origin=origin)

    cookie_value = _get_cookie_value(request, slug)
    upvoted = bool(cookie_value and _is_cookie_valid(slug, secret, cookie_value))
    record = await _fetch_post_record(kv, slug)

    # Optional metadata backfill (best-effort, write only if it changes).
    title = _extract_query_first(request.url, "title")
    permalink = _extract_query_first(request.url, "permalink")
    date_iso = _extract_query_first(request.url, "dateISO")
    record, changed = _merge_meta_into_record(record, title, permalink, date_iso)

    count = int(record.get("count", 0) or 0)
    # Avoid creating KV entries for never-upvoted posts; only persist metadata once a counter exists.
    if changed and count > 0:
        await _write_post_record(kv, slug, record)
    return _json_response({
        "slug": slug,
        "upvote_count": count,
        "upvoted": upvoted,
    }, origin=origin)


async def _handle_post(request, kv, origin: str | None, secret: str):
    payload: dict = {}
    try:
        content_type = (request.headers.get("Content-Type", "") or "").split(";", 1)[0].strip().lower()
        if "application/json" in content_type:
            data = json.loads(await request.text())
            if isinstance(data, dict):
                payload = data
        elif content_type in ("application/x-www-form-urlencoded", "multipart/form-data"):
            try:
                form_data = await request.formData()
                if form_data:
                    payload = {k: form_data.get(k) for k in ("slug", "title", "permalink", "dateISO")}
            except Exception:
                body = await request.text()
                parsed = parse_qs(body)
                payload = {k: parsed.get(k, [""])[0] for k in ("slug", "title", "permalink", "dateISO")}
    except Exception:
        payload = {}

    slug = payload.get("slug", "")
    if not isinstance(slug, str) or not slug:
        slug = _extract_slug_from_query(request.url)
    if not _validate_slug(slug):
        return _error_response("slug must start with '/' and not be empty", origin=origin)

    title = payload.get("title", "")
    permalink = payload.get("permalink", "")
    date_iso = payload.get("dateISO", "")

    cookie_value = _get_cookie_value(request, slug)
    if cookie_value and _is_cookie_valid(slug, secret, cookie_value):
        record = await _fetch_post_record(kv, slug)
        record, changed = _merge_meta_into_record(record, str(title or ""), str(permalink or ""), str(date_iso or ""))
        if changed:
            await _write_post_record(kv, slug, record)
        count = int(record.get("count", 0) or 0)
        return _json_response({
            "slug": slug,
            "upvote_count": count,
            "upvoted": True,
        }, origin=origin)

    record = await _fetch_post_record(kv, slug)
    record["count"] = int(record.get("count", 0) or 0) + 1
    record, _ = _merge_meta_into_record(record, str(title or ""), str(permalink or ""), str(date_iso or ""))
    await _write_post_record(kv, slug, record)
    count = int(record.get("count", 0) or 0)
    cookie_header = _build_cookie(slug, secret)
    return _json_response({
        "slug": slug,
        "upvote_count": count,
        "upvoted": True,
    }, origin=origin, set_cookie=cookie_header)


async def _handle_popular(request, env, kv, origin: str | None):
    raw_limit = _extract_query_first(request.url, "limit")
    limit = _parse_int(raw_limit, default=5)
    limit = _clamp_int(limit, 1, 50)

    cached_raw = await kv.get(POPULAR_CACHE_KEY)
    payload = None
    if cached_raw:
        try:
            payload = json.loads(cached_raw)
        except Exception:
            payload = None

    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        # Best-effort on-demand rebuild for first load / missing cron.
        payload = await _rebuild_popular_cache(env, kv)

    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    return _json_response({
        "generated_at": payload.get("generated_at", 0),
        "items": items[:limit],
    }, origin=origin, headers={"cache-control": "public, max-age=60"})


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

        if path == "/api/popular" and method == "GET":
            return await _handle_popular(request, env, kv_binding, origin)

        # Fallback to static assets (demo site).
        assets = _get_env_binding(env, "ASSETS")
        if assets:
            return await assets.fetch(request)

        return _error_response("Not found", status=404, origin=origin)

    async def scheduled(self, event):
        """
        Cron-triggered refresh of the popular cache.
        """
        env = self.env
        kv_binding = _get_env_binding(env, KV_BINDING_NAME)
        if not kv_binding:
            return
        try:
            await _rebuild_popular_cache(env, kv_binding)
        except Exception:
            # Avoid failing the scheduled event.
            return
