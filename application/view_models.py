from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


# ─── Dashboard ───

@dataclass
class ResumenPill:
    color: str
    texto: str


@dataclass
class AccionCard:
    color: str
    texto: str
    persona: str


@dataclass
class TimelineEntry:
    hora: str
    dot_class: str
    icono: str
    texto: str


@dataclass
class DashboardStats:
    ingresos_hoy: str = "0"
    activos: int = 0
    total_deportistas: int = 0
    vencidas: int = 0
    mora_acumulada: str = "0"
    tasa_cobro: int = 0


@dataclass
class DashboardViewModel:
    saludo: str
    nombre: str
    ultima_sincronizacion: str = "ahora"
    resumen: list[ResumenPill] = field(default_factory=list)
    acciones: list[AccionCard] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    stats: DashboardStats = field(default_factory=DashboardStats)


# ─── Bandeja ───

@dataclass
class BandejaItem:
    tipo: str
    color: str
    texto: str
    persona: str
    detalle: str
    hace: str


@dataclass
class BandejaGrupo:
    key: str
    titulo: str
    lista: list[BandejaItem]


@dataclass
class BandejaViewModel:
    grupos: list[BandejaGrupo] = field(default_factory=list)
    total: int = 0


# ─── Deportistas ───

@dataclass
class DeportistaRow:
    id: str
    nombre: str
    documento: str
    nivel: Optional[str]
    estado: str
    badge: str
    ultimo_pago: Optional[str]
    telefono: str


@dataclass
class DeportistasViewModel:
    deportistas: list[DeportistaRow] = field(default_factory=list)
    total: int = 0
    activos: int = 0


# ─── Finanzas ───

@dataclass
class PagoRow:
    deportista: str
    concepto: str
    monto: str
    estado: str
    badge: str


@dataclass
class ConceptoRow:
    nombre: str
    monto: str
    activo: bool


@dataclass
class FinanzasDatos:
    ingresos_hoy: str = "0"
    pagos_hoy: int = 0
    ingresos_mes: str = "0"
    pagos_mes: int = 0
    pagadas: int = 0
    total_mensualidades: int = 0
    pendientes: int = 0
    monto_pendiente: str = "0"
    mora_acumulada: str = "0"
    vencidas: int = 0
    tasa_cobro: int = 0
    ultimos_pagos: list[PagoRow] = field(default_factory=list)
    conceptos: list[ConceptoRow] = field(default_factory=list)


@dataclass
class FinanzasViewModel:
    datos: FinanzasDatos = field(default_factory=FinanzasDatos)


# ─── Historial ───

@dataclass
class HistorialEntry:
    hora: str
    color: str
    icono: str
    texto: str
    usuario: Optional[str]
    tipo: str


@dataclass
class HistorialViewModel:
    historial: list[HistorialEntry] = field(default_factory=list)


# ─── Sistema ───

@dataclass
class ServicioStatus:
    online: bool
    detalle: Optional[str] = None


@dataclass
class SistemaViewModel:
    version: str = "2.1.0"
    entorno: str = "Desarrollo"
    python_version: str = ""
    fastapi_version: str = ""
    ultimo_deploy: str = "2026-07-07"
    servidor: dict = field(default_factory=lambda: {
        "plataforma": "Render", "uptime": "—", "version": "2.1.0"
    })
    gemini: dict = field(default_factory=lambda: {
        "online": False, "modelo": "gemini-2.5-flash-lite",
        "fallback": "gemini-2.5-flash", "ultimo_error": None
    })
    supabase: dict = field(default_factory=lambda: {
        "online": False, "proyecto": "boy-secretaria",
        "registros": "—", "ultimo_backup": "—"
    })
    whatsapp: dict = field(default_factory=lambda: {
        "ultimo_mensaje": "—", "mensajes_hoy": 0
    })


# ─── Notificacion ───

@dataclass
class NotificacionItem:
    id: str
    icon: str
    text: str
    time: str
