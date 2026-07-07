from datetime import datetime, timedelta
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

router = APIRouter(prefix="/admin", tags=["admin"])

templates = Jinja2Templates(directory="templates")

# ──────────────────────────────────────────────
# Datos simulados (sin conexion a Supabase)
# ──────────────────────────────────────────────

MOCK_SOLICITUDES = [
    {"id": "1", "nombre": "Laura Martínez", "documento": "1234567890", "telefono": "3001112233",
     "fecha_nacimiento": "2015-03-12", "experiencia": "No", "nivel": None,
     "estado": "Pendiente evaluación", "estado_raw": "pendiente_evaluacion",
     "badge": "warning", "fecha": "2026-07-06", "fecha_creacion": "2026-07-06 10:30",
     "responsable_nombre": "Ana Martínez", "responsable_documento": "987654321"},
    {"id": "2", "nombre": "Carlos Pérez", "documento": "0987654321", "telefono": "3004445566",
     "fecha_nacimiento": "2014-07-20", "experiencia": "Sí", "nivel": "Intermedio",
     "estado": "Evaluado", "estado_raw": "evaluado",
     "badge": "info", "fecha": "2026-07-05", "fecha_creacion": "2026-07-05 14:15",
     "responsable_nombre": None, "responsable_documento": None},
    {"id": "3", "nombre": "Sofía Ramírez", "documento": "1122334455", "telefono": "3007778899",
     "fecha_nacimiento": "2016-01-05", "experiencia": "No sabe", "nivel": None,
     "estado": "Pendiente evaluación", "estado_raw": "pendiente_evaluacion",
     "badge": "warning", "fecha": "2026-07-04", "fecha_creacion": "2026-07-04 09:00",
     "responsable_nombre": "Pedro Ramírez", "responsable_documento": "556677889"},
    {"id": "4", "nombre": "Mateo López", "documento": "5544332211", "telefono": "3002223344",
     "fecha_nacimiento": "2013-11-15", "experiencia": "Sí", "nivel": "Avanzado",
     "estado": "Pendiente matrícula", "estado_raw": "pendiente_matricula",
     "badge": "primary", "fecha": "2026-07-03", "fecha_creacion": "2026-07-03 16:45",
     "responsable_nombre": None, "responsable_documento": None},
    {"id": "5", "nombre": "Valentina Gómez", "documento": "9988776655", "telefono": "3008889900",
     "fecha_nacimiento": "2015-09-28", "experiencia": "No", "nivel": "Iniciación",
     "estado": "Completado", "estado_raw": "completado",
     "badge": "success", "fecha": "2026-07-01", "fecha_creacion": "2026-06-28 11:00",
     "responsable_nombre": "Luis Gómez", "responsable_documento": "1122334455"},
]

MOCK_TAREAS = [
    {"id": "1", "tipo": "Evaluación pendiente", "badge": "primary", "persona": "Laura Martínez",
     "descripcion": "Evaluar solicitud de ingreso", "fecha": "2026-07-06",
     "prioridad": "Alta", "priority_class": "high", "estado": "pendiente"},
    {"id": "2", "tipo": "Evaluación pendiente", "badge": "primary", "persona": "Sofía Ramírez",
     "descripcion": "Evaluar solicitud de ingreso", "fecha": "2026-07-04",
     "prioridad": "Alta", "priority_class": "high", "estado": "pendiente"},
    {"id": "3", "tipo": "Comprobante por revisar", "badge": "warning", "persona": "Mateo López",
     "descripcion": "Revisar comprobante de matrícula", "fecha": "2026-07-03",
     "prioridad": "Media", "priority_class": "medium", "estado": "pendiente"},
    {"id": "4", "tipo": "Activación pendiente", "badge": "info", "persona": "Valentina Gómez",
     "descripcion": "Activar deportista tras pago de matrícula", "fecha": "2026-07-01",
     "prioridad": "Media", "priority_class": "medium", "estado": "pendiente"},
    {"id": "5", "tipo": "Mensualidad vencida", "badge": "danger", "persona": "Carlos Pérez",
     "descripcion": "Mensualidad de junio sin pagar", "fecha": "2026-06-30",
     "prioridad": "Baja", "priority_class": "low", "estado": "pendiente"},
]

MOCK_PAGOS = [
    {"id": "1", "deportista": "Mateo López", "documento": "5544332211",
     "concepto": "Matrícula", "monto": 50000, "metodo": "Nequi",
     "estado": "Pendiente", "badge": "warning",
     "fecha": "2026-07-03", "comprobante": "comp_001.jpg"},
    {"id": "2", "deportista": "Valentina Gómez", "documento": "9988776655",
     "concepto": "Matrícula", "monto": 50000, "metodo": "Efectivo",
     "estado": "Aprobado", "badge": "success",
     "fecha": "2026-06-30", "comprobante": "comp_002.jpg"},
    {"id": "3", "deportista": "Carlos Pérez", "documento": "0987654321",
     "concepto": "Mensualidad", "monto": 30000, "metodo": "Transferencia",
     "estado": "En revisión", "badge": "info",
     "fecha": "2026-07-05", "comprobante": "comp_003.jpg"},
    {"id": "4", "deportista": "Laura Martínez", "documento": "1234567890",
     "concepto": "Matrícula", "monto": 50000, "metodo": "Nequi",
     "estado": "Rechazado", "badge": "danger",
     "fecha": "2026-07-04", "comprobante": "comp_004.jpg"},
    {"id": "5", "deportista": "Sofía Ramírez", "documento": "1122334455",
     "concepto": "Matrícula", "monto": 25000, "metodo": "Efectivo",
     "estado": "Parcial", "badge": "warning",
     "fecha": "2026-07-04", "comprobante": None},
]

MOCK_DEPORTISTAS = [
    {"id": "1", "nombre": "Valentina Gómez", "documento": "9988776655",
     "categoria": "Infantil", "nivel": "Iniciación",
     "estado": "Activo", "badge": "success",
     "ultimo_pago": "2026-07-01", "telefono": "3008889900"},
    {"id": "2", "nombre": "Carlos Pérez", "documento": "0987654321",
     "categoria": "Juvenil", "nivel": "Intermedio",
     "estado": "Inactivo", "badge": "danger",
     "ultimo_pago": "2026-05-15", "telefono": "3004445566"},
    {"id": "3", "nombre": "Sofía Ramírez", "documento": "1122334455",
     "categoria": "Infantil", "nivel": None,
     "estado": "Inactivo", "badge": "danger",
     "ultimo_pago": None, "telefono": "3007778899"},
]

MOCK_CONCEPTOS = [
    {"id": "1", "nombre": "Mensualidad", "monto": 30000,
     "precios_por_nivel": {"iniciacion": 25000, "intermedio": 30000, "avanzado": 35000},
     "recurrente": True, "automatico": True, "aplica_mora": True, "activo": True},
    {"id": "2", "nombre": "Matrícula", "monto": 50000,
     "precios_por_nivel": None,
     "recurrente": False, "automatico": False, "aplica_mora": False, "activo": True},
    {"id": "3", "nombre": "Uniforme", "monto": 80000,
     "precios_por_nivel": None,
     "recurrente": False, "automatico": False, "aplica_mora": False, "activo": True},
    {"id": "4", "nombre": "Evento", "monto": 20000,
     "precios_por_nivel": None,
     "recurrente": False, "automatico": False, "aplica_mora": False, "activo": True},
    {"id": "5", "nombre": "Licra", "monto": 15000,
     "precios_por_nivel": None,
     "recurrente": False, "automatico": False, "aplica_mora": False, "activo": False},
]

MOCK_CONFIG = {
    "llave_breb": "3101234567",
    "monto_matricula": 50000,
    "recargo_mora": 5000,
    "dias_recordatorio": 3,
    "tolerancia_pago": 5,
}

# ──────────────────────────────────────────────
# Rutas
# ──────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    hoy = datetime.now()
    datos = {
        "fecha": hoy.strftime("%d %B %Y").capitalize(),
        "solicitudes_pendientes": 3,
        "comprobantes_pendientes": 2,
        "pagos_hoy": 1,
        "monto_hoy": 30000,
        "deportistas_activos": 1,
        "deportistas_inactivos": 2,
        "mensualidades_vencidas": 1,
        "tareas_pendientes": 5,
        "total_deportistas": 3,
        "ultimas_solicitudes": [
            {"nombre": s["nombre"], "estado": s["estado"], "badge": s["badge"], "fecha": s["fecha"]}
            for s in MOCK_SOLICITUDES[:3]
        ],
        "proximas_tareas": [
            {"tipo": t["tipo"], "persona": t["persona"],
             "prioridad": t["prioridad"], "priority_class": t["priority_class"]}
            for t in MOCK_TAREAS[:3]
        ],
    }
    return templates.TemplateResponse(
        request, "admin/dashboard.html", {"datos": datos}
    )


@router.get("/solicitudes", response_class=HTMLResponse)
async def solicitudes(request: Request):
    return templates.TemplateResponse(
        request, "admin/solicitudes.html", {"solicitudes": MOCK_SOLICITUDES}
    )


@router.get("/tareas", response_class=HTMLResponse)
async def tareas(request: Request):
    stats = {
        "evaluacion": 2,
        "comprobantes": 1,
        "activaciones": 1,
        "vencidas": 1,
    }
    return templates.TemplateResponse(
        request, "admin/tareas.html", {"tareas": MOCK_TAREAS, "stats": stats}
    )


@router.get("/pagos", response_class=HTMLResponse)
async def pagos(request: Request):
    return templates.TemplateResponse(
        request, "admin/pagos.html", {"pagos": MOCK_PAGOS}
    )


@router.get("/deportistas", response_class=HTMLResponse)
async def deportistas(request: Request):
    return templates.TemplateResponse(
        request, "admin/deportistas.html", {"deportistas": MOCK_DEPORTISTAS}
    )


@router.get("/conceptos", response_class=HTMLResponse)
async def conceptos(request: Request):
    return templates.TemplateResponse(
        request, "admin/conceptos.html", {"conceptos": MOCK_CONCEPTOS}
    )


@router.get("/configuracion", response_class=HTMLResponse)
async def configuracion(request: Request):
    return templates.TemplateResponse(
        request, "admin/configuracion.html", {"config": MOCK_CONFIG}
    )
