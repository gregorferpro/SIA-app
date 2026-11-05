import logging
import re

from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from auditoria.utils import registrar_bitacora

from .contexto import construir_contexto
from .servicios import (
    AsistenteError,
    AsistenteNoDisponible,
    AsistenteTiempoAgotado,
    consultar_ollama,
)


logger = logging.getLogger(__name__)

MAXIMO_CARACTERES_MENSAJE = 1000
MAXIMO_MENSAJES_HISTORIAL = 6
MAXIMO_CARACTERES_HISTORIAL = 1500

MENSAJE_NO_DISPONIBLE = (
    "El asistente no está disponible en este momento. "
    "Intente nuevamente en unos minutos o contacte a la UTIC."
)
MENSAJE_TIEMPO_AGOTADO = (
    "El asistente está tardando demasiado en responder. "
    "Intente con una pregunta más corta o vuelva a intentarlo."
)
MENSAJE_ERROR_MOTOR = (
    "El asistente no pudo generar una respuesta. "
    "Intente nuevamente más tarde."
)
MENSAJE_CODIGO_INVENTADO = (
    "No encontré ese trámite entre los datos a los que su perfil "
    "tiene acceso. Revise el estado de sus trámites desde su panel en SIA."
)

# El último tramo exige un dígito para no confundir el formato
# genérico que explica el modelo ("CMP-2026-NNNN") con un código real.
PATRON_CODIGO_TRAMITE = re.compile(r"\b(?:SOP|MTO|CMP)-[A-Z0-9]+-[A-Z0-9]*\d[A-Z0-9]*\b")


class AsistenteThrottle(UserRateThrottle):
    # Cada consulta ocupa la GPU del anfitrión varios segundos.
    rate = "20/min"


def _historial_valido(historial):
    """Conserva solo los últimos turnos bien formados."""

    if not isinstance(historial, list):
        return []

    mensajes = []
    for turno in historial[-MAXIMO_MENSAJES_HISTORIAL:]:
        if not isinstance(turno, dict):
            continue

        rol = turno.get("rol")
        contenido = turno.get("contenido")

        if rol not in ("usuario", "asistente") or not isinstance(contenido, str):
            continue

        contenido = contenido.strip()[:MAXIMO_CARACTERES_HISTORIAL]
        if contenido:
            mensajes.append({
                "role": "user" if rol == "usuario" else "assistant",
                "content": contenido,
            })

    return mensajes


@api_view(["POST"])
@throttle_classes([AsistenteThrottle])
def chat(request):

    mensaje = request.data.get("mensaje")

    if not isinstance(mensaje, str) or not mensaje.strip():
        return Response(
            {"ok": False, "detalle": "Escriba o dicte una pregunta."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    mensaje = mensaje.strip()

    if len(mensaje) > MAXIMO_CARACTERES_MENSAJE:
        return Response(
            {
                "ok": False,
                "detalle": (
                    "La pregunta es demasiado larga "
                    f"(máximo {MAXIMO_CARACTERES_MENSAJE} caracteres)."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # El contexto va dentro del último mensaje del usuario y no
    # como mensaje "system": Ollama descarta el SYSTEM del
    # Modelfile cuando la petición trae su propio mensaje system.
    contexto = construir_contexto(request.user)
    mensajes = _historial_valido(request.data.get("historial"))
    mensajes.append({
        "role": "user",
        "content": (
            "CONTEXTO OPERATIVO (datos reales del sistema, "
            "no los menciones si no son relevantes):\n"
            f"{contexto}\n\n"
            f"PREGUNTA DEL USUARIO:\n{mensaje}"
        ),
    })

    try:
        resultado = consultar_ollama(mensajes)

    except AsistenteTiempoAgotado as error:
        logger.warning("Ollama agotó el tiempo de espera: %s", error)
        return Response(
            {"ok": False, "detalle": MENSAJE_TIEMPO_AGOTADO},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )

    except AsistenteNoDisponible as error:
        logger.error("Ollama no disponible: %s", error)
        registrar_bitacora(
            request,
            accion="ASISTENTE_NO_DISPONIBLE",
            modulo="ASISTENTE",
            detalle=str(error)[:500],
            nivel="ERROR",
        )
        return Response(
            {"ok": False, "detalle": MENSAJE_NO_DISPONIBLE},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    except AsistenteError as error:
        logger.error("Ollama devolvió un error: %s", error)
        return Response(
            {"ok": False, "detalle": MENSAJE_ERROR_MOTOR},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # El modelo puede inventar códigos de trámite; ninguno que no
    # venga del contexto del propio usuario llega a la pantalla.
    respuesta = resultado["texto"]
    inventados = (
        set(PATRON_CODIGO_TRAMITE.findall(respuesta))
        - set(PATRON_CODIGO_TRAMITE.findall(contexto))
        - set(PATRON_CODIGO_TRAMITE.findall(mensaje))
    )
    if inventados:
        logger.warning("Respuesta con códigos fuera del contexto: %s", sorted(inventados))
        respuesta = MENSAJE_CODIGO_INVENTADO

    return Response({
        "ok": True,
        "respuesta": respuesta,
        "modelo": resultado["modelo"],
        "duracion_ms": resultado["duracion_ms"],
    })
