"""Share pages: a public progression's link with Open Graph tags, so WhatsApp, Telegram or Facebook
show its name and chords. The web is a static site and cannot set these per progression, so the
link points here and the page sends the visitor on to the web's explorer."""

from html import escape

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.repositories import Repository, get_repository

router = APIRouter()

PAGE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ChordWeaver">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{target}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="noindex">
<link rel="canonical" href="{target}">
<meta http-equiv="refresh" content="0; url={target}">
</head>
<body>
<p><a href="{target}">Abrir {title} en ChordWeaver</a></p>
<script>location.replace({target_js});</script>
</body>
</html>"""


@router.get("/p/{progression_id}", response_class=HTMLResponse, include_in_schema=False)
async def share_page(progression_id: str, repository: Repository = Depends(get_repository)):
    web = settings.web_url.rstrip("/")
    progression = await repository.get_progression(progression_id)
    if not progression or not progression.is_public:
        target = f"{web}/explorer/"
        title, description = "ChordWeaver", "Esta progresión no existe o ya no es pública."
        status_code = 404
    else:
        target = f"{web}/explorer/?p={progression.id}"
        title = f"{progression.name} · ChordWeaver"
        key = f" en {progression.tonality}" if progression.tonality else ""
        description = f"{' – '.join(progression.chords)}{key}. Escúchala y descubre por qué funciona."
        status_code = 200
    html = PAGE.format(
        title=escape(title),
        description=escape(description),
        target=escape(target),
        target_js=escape(repr(target)),
        image=escape(f"{web}/opengraph-image.png"),
    )
    return HTMLResponse(html, status_code=status_code)
