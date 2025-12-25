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

# Cached "most popular posts" list (rebuilt by cron and on-demand when missing).
POPULAR_CACHE_KEY = "popular_cache:v1"
POPULAR_CACHE_MAX_ENV = "POPULAR_CACHE_MAX"
POPULAR_CACHE_MAX_DEFAULT = 50
POPULAR_REFRESH_SECONDS = 21600  # 6 hours
POPULAR_SITE_ORIGIN_KEY = "popular_site_origin:v1"
POPULAR_SLUG_INDEX_KEY = "popular_slug_index:v1"
POPULAR_SITEMAP_PATH = "/sitemap.xml"
POPULAR_SITEMAP_MAX_URLS = 5000
POPULAR_SLUG_INDEX_MAX = 5000


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


def _site_origin_from_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _normalize_slug(path: str) -> str:
    path = (path or "").strip()
    if not path:
        return ""
    if not path.startswith("/"):
        path = "/" + path
    if path != "/":
        path = path.rstrip("/")
    return path


def _extract_sitemap_locs(xml: str) -> list[str]:
    """
    Extract <loc>...</loc> values from a sitemap XML string.
    This is a lightweight parser by design (no external deps).
    """
    out: list[str] = []
    xml = xml or ""
    start = 0
    while True:
        i = xml.find("<loc>", start)
        if i == -1:
            break
        j = xml.find("</loc>", i + 5)
        if j == -1:
            break
        loc = xml[i + 5:j].strip()
        if loc:
            out.append(loc)
        start = j + 6
    return out


def _slugs_from_sitemap(xml: str) -> list[str]:
    locs = _extract_sitemap_locs(xml)
    slugs: list[str] = []
    seen: set[str] = set()
    for loc in locs:
        try:
            path = urlparse(loc).path
        except Exception:
            continue
        slug = _normalize_slug(path)
        if not slug or not slug.startswith("/"):
            continue
        if slug in seen:
            continue
        seen.add(slug)
        slugs.append(slug)
        if len(slugs) >= POPULAR_SITEMAP_MAX_URLS:
            break
    return slugs


async def _fetch_text(url: str) -> str | None:
    """
    Fetch a URL and return the response body as text.
    Relies on Cloudflare Workers' fetch being available at runtime.
    """
    fetch_fn = globals().get("fetch")
    if not callable(fetch_fn):
        try:
            # Python Workers may also expose fetch via the workers runtime module.
            from workers import fetch as fetch_fn  # type: ignore
        except Exception:
            return None

    try:
        resp = await _maybe_await(fetch_fn(url))
    except Exception:
        return None

    ok = getattr(resp, "ok", None)
    if ok is False:
        return None

    text_fn = getattr(resp, "text", None)
    if not callable(text_fn):
        return None

    try:
        body = await _maybe_await(text_fn())
    except Exception:
        return None

    return body if isinstance(body, str) else None


async def _load_slug_index(kv) -> list[str]:
    raw = None
    try:
        raw = await _kv_get(kv, POPULAR_SLUG_INDEX_KEY)
    except Exception:
        raw = None

    if not raw:
        return []

    try:
        data = json.loads(raw)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    out: list[str] = []
    for item in data:
        if isinstance(item, str):
            slug = _normalize_slug(item)
            if _validate_slug(slug):
                out.append(slug)
    # De-dupe while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for s in out:
        if s in seen:
            continue
        seen.add(s)
        deduped.append(s)
    return deduped


async def _store_slug_index(kv, slugs: list[str]):
    cleaned: list[str] = []
    seen: set[str] = set()
    for s in (slugs or []):
        if not isinstance(s, str):
            continue
        slug = _normalize_slug(s)
        if not _validate_slug(slug):
            continue
        if slug in seen:
            continue
        seen.add(slug)
        cleaned.append(slug)

    try:
        await _kv_put(kv, POPULAR_SLUG_INDEX_KEY, json.dumps(cleaned))
    except Exception:
        return


async def _add_slug_to_index(kv, slug: str):
    slug = _normalize_slug(slug)
    if not _validate_slug(slug):
        return

    current = await _load_slug_index(kv)
    if slug in current:
        return

    current.append(slug)
    if len(current) > POPULAR_SLUG_INDEX_MAX:
        current = current[-POPULAR_SLUG_INDEX_MAX:]

    await _store_slug_index(kv, current)


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

        try:
            maybe = kv.list(**params)  # type: ignore[arg-type]
            resp = await _maybe_await(maybe)
        except TypeError:
            try:
                maybe = kv.list(params)  # type: ignore[arg-type]
                resp = await _maybe_await(maybe)
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
                    else:
                        name_attr = getattr(k, "name", None)
                        if isinstance(name_attr, str):
                            out.append(name_attr)

            list_complete = resp.get("list_complete")
            cursor = resp.get("cursor") if isinstance(resp.get("cursor"), str) else None

            if list_complete is True or not cursor:
                break
            continue

        if isinstance(resp, list):
            for k in resp:
                if isinstance(k, str):
                    out.append(k)
                elif isinstance(k, dict) and isinstance(k.get("name"), str):
                    out.append(k["name"])
                else:
                    name_attr = getattr(k, "name", None)
                    if isinstance(name_attr, str):
                        out.append(name_attr)
            break

        # Attribute-style response
        keys_attr = getattr(resp, "keys", None)
        if isinstance(keys_attr, list):
            for k in keys_attr:
                if isinstance(k, str):
                    out.append(k)
                elif isinstance(k, dict) and isinstance(k.get("name"), str):
                    out.append(k["name"])
                else:
                    name_attr = getattr(k, "name", None)
                    if isinstance(name_attr, str):
                        out.append(name_attr)

            list_complete_attr = getattr(resp, "list_complete", None)
            cursor_attr = getattr(resp, "cursor", None)
            cursor = cursor_attr if isinstance(cursor_attr, str) else None
            if list_complete_attr is True or not cursor:
                break
            continue

        break

    return out


async def _rebuild_popular_cache(env, kv, site_origin: str | None = None) -> dict:
    """
    Build and store a cached popular list.

    Prefer enumerating KV keys via list(); if that is unavailable or returns nothing,
    fall back to a maintained slug index, and finally to reading slugs from sitemap.xml.
    """
    max_items = _parse_int(_get_env_binding(env, POPULAR_CACHE_MAX_ENV), POPULAR_CACHE_MAX_DEFAULT)
    max_items = _clamp_int(max_items, 1, 200)

    source = "kv_list"
    slugs: list[str] = []

    key_names = await _kv_list_keys(kv, KV_KEY_PREFIX)
    if key_names:
        for name in key_names:
            if not isinstance(name, str) or not name.startswith(KV_KEY_PREFIX):
                continue
            slug = _normalize_slug(name[len(KV_KEY_PREFIX):])
            if _validate_slug(slug):
                slugs.append(slug)
    else:
        source = "slug_index"
        slugs = await _load_slug_index(kv)

    if not slugs:
        origin = (site_origin or "").strip()
        if not origin:
            try:
                stored = await _kv_get(kv, POPULAR_SITE_ORIGIN_KEY)
                origin = stored.strip() if isinstance(stored, str) else ""
            except Exception:
                origin = ""

        if origin:
            source = "sitemap"
            sitemap_text = await _fetch_text(f"{origin}{POPULAR_SITEMAP_PATH}")
            slugs = _slugs_from_sitemap(sitemap_text or "")
        else:
            source = "none"

    # De-dupe while preserving order.
    seen_slugs: set[str] = set()
    candidates: list[str] = []
    for s in slugs:
        if s in seen_slugs:
            continue
        seen_slugs.add(s)
        candidates.append(s)

    items: list[dict] = []
    upvoted_slugs: list[str] = []

    for slug in candidates:
        record = await _fetch_post_record(kv, slug)
        count = int(record.get("count", 0) or 0)
        if count <= 0:
            continue

        upvoted_slugs.append(slug)

        title = str(record.get("title", "") or "")
        permalink = str(record.get("permalink", "") or "")
        date_iso = str(record.get("dateISO", "") or "")

        if not permalink:
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

    if upvoted_slugs:
        await _store_slug_index(kv, upvoted_slugs)

    payload = {
        "generated_at": int(time.time()),
        "source": source,
        "scanned_keys": len(candidates),
        "indexed_slugs": len(upvoted_slugs),
        "items": items[:max_items],
    }
    await _kv_put(kv, POPULAR_CACHE_KEY, json.dumps(payload))
    return payload


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
    try:
        await _add_slug_to_index(kv, slug)
    except Exception:
        pass
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

    site_origin = _site_origin_from_url(request.url)
    if site_origin:
        try:
            await _kv_put(kv, POPULAR_SITE_ORIGIN_KEY, site_origin)
        except Exception:
            pass

    cached_raw = await _kv_get(kv, POPULAR_CACHE_KEY)
    payload = None
    if cached_raw:
        try:
            payload = json.loads(cached_raw)
        except Exception:
            payload = None

    now = int(time.time())
    should_rebuild = False

    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        should_rebuild = True
    else:
        generated_at = payload.get("generated_at")
        source = payload.get("source")
        items = payload.get("items")
        if isinstance(items, list) and len(items) == 0:
            # Empty cache: retry at most every 10 minutes.
            if site_origin and (not isinstance(source, str) or source == "none"):
                should_rebuild = True
            elif not isinstance(generated_at, int) or (now - generated_at) >= 600:
                should_rebuild = True

    if should_rebuild:
        payload = await _rebuild_popular_cache(env, kv, site_origin=site_origin or None)

    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    return _json_response({
        "generated_at": payload.get("generated_at", 0),
        "source": payload.get("source", ""),
        "scanned_keys": payload.get("scanned_keys", 0),
        "indexed_slugs": payload.get("indexed_slugs", 0),
        "items": items[:limit],
    }, origin=origin, headers={"cache-control": "public, max-age=600"})


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

    async def scheduled(self, event, env=None, ctx=None):
        """
        Cron-triggered cache maintenance.
        Runs every 10 minutes, but only rebuilds when missing or stale (> 6 hours).
        """
        if env is None:
            env = self.env
        kv_binding = _get_env_binding(env, KV_BINDING_NAME)
        if not kv_binding:
            return

        try:
            cached_raw = await _kv_get(kv_binding, POPULAR_CACHE_KEY)
        except Exception:
            cached_raw = None

        payload = None
        if cached_raw:
            try:
                payload = json.loads(cached_raw)
            except Exception:
                payload = None

        now = int(time.time())
        should_rebuild = False

        if not isinstance(payload, dict):
            should_rebuild = True
        else:
            generated_at = payload.get("generated_at")
            if not isinstance(generated_at, int):
                should_rebuild = True
            elif now - generated_at >= POPULAR_REFRESH_SECONDS:
                should_rebuild = True
            else:
                items = payload.get("items")
                if isinstance(items, list) and len(items) == 0 and (now - generated_at) >= 600:
                    should_rebuild = True

        if not should_rebuild:
            return

        try:
            site_origin = None
            try:
                stored = await _kv_get(kv_binding, POPULAR_SITE_ORIGIN_KEY)
                site_origin = stored if isinstance(stored, str) and stored else None
            except Exception:
                site_origin = None

            await _rebuild_popular_cache(env, kv_binding, site_origin=site_origin)
        except Exception:
            # Avoid failing the scheduled event.
            return
