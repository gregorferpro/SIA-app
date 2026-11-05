import json
import socket
import urllib.error
import urllib.request

from django.conf import settings


# ==========================================================
# CONECTOR HTTP CON OLLAMA
# ==========================================================
#
# Ollama corre en el equipo anfitrión, fuera de sia-app.
# Se usa urllib de la biblioteca estándar para no añadir una
# dependencia solo por esta llamada.
#
# ==========================================================


class AsistenteError(Exception):
    """Fallo al consultar el motor de IA."""


class AsistenteNoDisponible(AsistenteError):
    """Ollama no responde: apagado, IP equivocada o red caída."""


class AsistenteTiempoAgotado(AsistenteError):
    """Ollama tardó más que OLLAMA_TIMEOUT en responder."""


class AsistenteRespuestaInvalida(AsistenteError):
    """Ollama respondió, pero con un error o un JSON inesperado."""


def consultar_ollama(mensajes):
    """Envía la conversación a /api/chat y devuelve el texto
    generado. `mensajes` es una lista de dicts con `role`
    ("user" o "assistant") y `content`."""

    url = settings.OLLAMA_URL.rstrip("/") + "/api/chat"

    cuerpo = json.dumps({
        "model": settings.OLLAMA_MODELO,
        "messages": mensajes,
        "stream": False,
    }).encode("utf-8")

    peticion = urllib.request.Request(
        url,
        data=cuerpo,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            peticion,
            timeout=settings.OLLAMA_TIMEOUT,
        ) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        raise AsistenteRespuestaInvalida(
            f"Ollama respondió HTTP {error.code}: "
            f"{error.read().decode('utf-8', 'replace')[:300]}"
        ) from error

    except (TimeoutError, socket.timeout) as error:
        raise AsistenteTiempoAgotado(str(error)) from error

    except urllib.error.URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            raise AsistenteTiempoAgotado(str(error)) from error
        raise AsistenteNoDisponible(str(error.reason)) from error

    except (ConnectionError, OSError) as error:
        raise AsistenteNoDisponible(str(error)) from error

    except ValueError as error:
        raise AsistenteRespuestaInvalida(
            "Ollama devolvió un JSON inválido."
        ) from error

    texto = (datos.get("message") or {}).get("content", "")

    if not isinstance(texto, str) or not texto.strip():
        raise AsistenteRespuestaInvalida(
            "Ollama devolvió una respuesta vacía."
        )

    return {
        "texto": texto.strip(),
        "modelo": datos.get("model", settings.OLLAMA_MODELO),
        "duracion_ms": int(datos.get("total_duration", 0) / 1_000_000),
    }
