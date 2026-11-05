from compras.models import SolicitudCompra
from mantenimiento.models import RequerimientoMantenimiento
from soporte.models import Ticket
from usuarios.models import Rol, obtener_codigos_rol_efectivos


# ==========================================================
# CONTEXTO OPERATIVO PARA EL ASISTENTE
# ==========================================================
#
# Se arma en cada consulta con datos reales del usuario: sus
# roles, sus trámites abiertos y lo que tiene pendiente en su
# bandeja. Solo se incluyen trámites que el propio usuario ya
# puede ver en su panel, para no filtrar información de otros.
#
# ==========================================================

MAXIMO_POR_LISTA = 5

COMPRAS_TERMINALES = ("CERRADO_ARCHIVADO", "RECHAZADO", "ANULADO")

# Estados de Compras que esperan una acción de cada rol.
BANDEJA_COMPRAS = {
    "DAF": ("CREADO_PENDIENTE_DAF", "EVALUADO_PENDIENTE_CERTIFICACION"),
    "ADMIN": ("VERIFICADO_PENDIENTE_AUTORIZACION",),
    "DIRECTOR": ("VERIFICADO_PENDIENTE_AUTORIZACION",),
    "TESORERIA": ("APROBADO_PARA_DESEMBOLSO",),
    "ENCARGADO_COMPRAS_ALMACEN": ("FONDOS_DESEMBOLSADOS", "COMPRA_REGISTRADA"),
}


def _tickets_abiertos():
    return (
        Ticket.objects
        .filter(activo=True, estado__es_terminal=False)
        .select_related("estado")
        .order_by("-creado_en")
    )


def _mantenimientos_abiertos():
    return (
        RequerimientoMantenimiento.objects
        .filter(activo=True, estado__es_terminal=False)
        .select_related("estado")
        .order_by("-creado_en")
    )


def _compras_abiertas():
    return (
        SolicitudCompra.objects
        .filter(activo=True)
        .exclude(estado__in=COMPRAS_TERMINALES)
        .order_by("-creado_en")
    )


def _seccion(titulo, consulta, describir):
    total = consulta.count()

    if not total:
        return f"{titulo}: 0 (no tiene ninguno)."

    lineas = [f"{titulo}: {total}."]
    for registro in consulta[:MAXIMO_POR_LISTA]:
        lineas.append(f"  - {describir(registro)}")

    if total > MAXIMO_POR_LISTA:
        lineas.append(f"  (y {total - MAXIMO_POR_LISTA} más)")

    return "\n".join(lineas)


def _ticket(t):
    prioridad = f", prioridad {t.prioridad}" if t.prioridad else ""
    return f"{t.codigo} «{t.titulo}» - estado {t.estado.codigo} ({t.estado.nombre}){prioridad}"


def _mantenimiento(m):
    return f"{m.codigo} «{m.titulo}» - estado {m.estado.codigo} ({m.estado.nombre})"


def _compra(c):
    return f"{c.codigo} «{c.titulo}» - estado {c.estado} ({c.get_estado_display()})"


def construir_contexto(usuario):
    """Devuelve el texto del CONTEXTO OPERATIVO del usuario."""

    codigos = obtener_codigos_rol_efectivos(usuario)
    nombres_rol = dict(
        Rol.objects
        .filter(codigo__in=codigos)
        .values_list("codigo", "nombre")
    )
    roles = ", ".join(
        f"{nombres_rol.get(codigo, codigo)} ({codigo})"
        for codigo in sorted(codigos)
    ) or "sin rol asignado"

    mis_tickets = _tickets_abiertos().filter(solicitante=usuario)
    mis_mantenimientos = _mantenimientos_abiertos().filter(solicitante=usuario)
    mis_compras = _compras_abiertas().filter(solicitante=usuario)

    secciones = [
        f"Usuario: {usuario.nombre_completo or usuario.email}",
        f"Roles: {roles}",
        _seccion("Mis tickets de Soporte Técnico abiertos", mis_tickets, _ticket),
        _seccion("Mis requerimientos de Mantenimiento abiertos", mis_mantenimientos, _mantenimiento),
        _seccion("Mis solicitudes de Compra abiertas", mis_compras, _compra),
    ]

    # El modelo pequeño a veces ignora un "0" suelto y afirma que el
    # usuario sí tiene trámites; un resumen explícito lo evita.
    if not (mis_tickets.exists() or mis_mantenimientos.exists() or mis_compras.exists()):
        secciones.append(
            "Resumen: este usuario NO tiene ningún ticket, requerimiento "
            "ni solicitud de compra abierto a su nombre."
        )

    bandejas = []

    def agregar_bandeja(titulo, consulta, describir):
        bandejas.append(titulo)
        secciones.append(_seccion(titulo, consulta, describir))

    if "JEFE_UTIC" in codigos:
        agregar_bandeja(
            "Tickets por validar o clasificar (bandeja del Jefe UTIC)",
            _tickets_abiertos().filter(estado__codigo__in=("NUEVO", "EN_ANALISIS")),
            _ticket,
        )

    if "ESPECIALISTA" in codigos:
        agregar_bandeja(
            "Tickets asignados a mí (bandeja del Técnico de Soporte Técnico)",
            _tickets_abiertos().filter(tecnico_asignado=usuario),
            _ticket,
        )

    if "SERVICIOS_GENERALES" in codigos:
        agregar_bandeja(
            "Requerimientos por validar o derivar (bandeja del Jefe Mantenimiento)",
            _mantenimientos_abiertos().filter(estado__codigo__in=("RECIBIDO", "VALIDADO")),
            _mantenimiento,
        )

    if "AUXILIAR_SERVICIOS_GENERALES" in codigos:
        agregar_bandeja(
            "Mantenimientos asignados a mí (bandeja del Técnico de Mantenimiento)",
            _mantenimientos_abiertos().filter(auxiliar_asignado=usuario),
            _mantenimiento,
        )

    for codigo in sorted(codigos):
        if codigo in BANDEJA_COMPRAS:
            agregar_bandeja(
                f"Solicitudes de Compra que esperan mi acción (bandeja de {nombres_rol.get(codigo, codigo)})",
                _compras_abiertas().filter(estado__in=BANDEJA_COMPRAS[codigo]),
                _compra,
            )

    secciones.append(
        "Alcance de este perfil: solo puede conocer sus propios trámites y "
        + (
            "estas bandejas: " + "; ".join(bandejas) + "."
            if bandejas else "no tiene bandejas de atención."
        )
        + " No tiene acceso a trámites de otros usuarios ni a las "
        "bandejas de otros roles. Si pregunta por ellos, responda que su "
        "perfil no tiene acceso a esa información."
    )

    return "\n".join(secciones)
