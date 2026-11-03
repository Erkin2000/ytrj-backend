"""Адреса, на которые бэкенд отправляет браузер (редиректы после входа)."""

from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit


def append_query(target: str, params: list[tuple[str, str]]) -> str:
    """Добавляет params к target, сохраняя его собственные query-параметры и fragment."""
    parts = urlsplit(target)
    query = parse_qsl(parts.query, keep_blank_values=True) + params
    return urlunsplit(parts._replace(query=urlencode(query)))


def normalize_redirect_target(value: str, name: str) -> str:
    """Проверяет адрес редиректа из настроек: абсолютный http(s) URL или путь от корня.

    Пустое значение или относительный путь без "/" дали бы Location вида "?code=...",
    и браузер вернулся бы на тот же эндпоинт; "//host" и "javascript:" — чужой адрес.
    """
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme:
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValueError(f"{name}: нужен http(s) URL или путь от корня, получено {value!r}")
        if not parts.path:
            value = parts._replace(path="/").geturl()
    elif not value.startswith("/") or value.startswith("//"):
        raise ValueError(f"{name}: путь должен начинаться с одного '/', получено {value!r}")
    if urlsplit(value).path.rstrip("/").endswith("/redirect/from-backend"):
        raise ValueError(f"{name} не может указывать на сам /redirect/from-backend")
    return value


def origin_of(url: str, base: str = "") -> str:
    """scheme://host[:port] адреса; относительный путь разрешается от base.
    Пустая строка, если origin определить нельзя."""
    parts = urlsplit(urljoin(base, url))
    if not parts.scheme or not parts.netloc:
        return ""
    return f"{parts.scheme}://{parts.netloc}".lower()
