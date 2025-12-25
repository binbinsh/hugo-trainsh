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
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


async def _write_count(kv, slug: str, count: int):
    await kv.put(_kv_key(slug), str(count))


async def _handle_get(request, kv, origin: str | None, secret: str):
    slug = _extract_slug_from_query(request.url)
    if not _validate_slug(slug):
        return _error_response("slug must start with '/' and not be empty", origin=origin)

    cookie_value = _get_cookie_value(request, slug)
    upvoted = bool(cookie_value and _is_cookie_valid(slug, secret, cookie_value))
    count = await _fetch_count(kv, slug)
    return _json_response({
        "slug": slug,
        "upvote_count": count,
        "upvoted": upvoted,
    }, origin=origin)


async def _handle_post(request, kv, origin: str | None, secret: str):
    slug = await _read_post_slug(request)
    if not slug:
        slug = _extract_slug_from_query(request.url)
    if not _validate_slug(slug):
        return _error_response("slug must start with '/' and not be empty", origin=origin)

    cookie_value = _get_cookie_value(request, slug)
    if cookie_value and _is_cookie_valid(slug, secret, cookie_value):
        count = await _fetch_count(kv, slug)
        return _json_response({
            "slug": slug,
            "upvote_count": count,
            "upvoted": True,
        }, origin=origin)

    count = await _fetch_count(kv, slug)
    count += 1
    await _write_count(kv, slug, count)
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
