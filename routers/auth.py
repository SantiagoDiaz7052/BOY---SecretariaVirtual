import logging
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from application.usuario_admin_service import UsuarioAdminService
from domain.usuario_admin import RolUsuario

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")

auth_service = UsuarioAdminService()


def usuario_autenticado(request: Request) -> bool:
    return "usuario" in request.session


def usuario_actual(request: Request) -> str:
    return request.session.get("usuario", "")


def rol_actual(request: Request) -> str:
    return request.session.get("rol", RolUsuario.SOLO_LECTURA.value)


def puede_editar(request: Request) -> bool:
    return rol_actual(request) in (RolUsuario.ADMINISTRADOR.value, RolUsuario.SECRETARIA.value)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    if usuario_autenticado(request):
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"error": error}
    )


@router.post("/login")
async def login_post(request: Request,
                     username: str = Form(...),
                     password: str = Form(...),
                     recordarme: str = Form("")):
    user = auth_service.autenticar(username, password)
    if not user:
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Usuario o contraseña incorrectos"},
            status_code=401,
        )
    if not user.activo:
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Usuario desactivado. Contacta al administrador."},
            status_code=403,
        )
    request.session["usuario"] = user.usuario
    request.session["nombre"] = user.nombre
    request.session["rol"] = user.rol
    request.session["club_id"] = user.club_id or "default"
    request.session["recordarme"] = (recordarme == "on")

    return RedirectResponse(url="/admin", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
