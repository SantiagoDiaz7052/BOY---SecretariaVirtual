from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from routers.whatsapp import router as whatsapp_router
from routers.admin import router as admin_router
from routers.auth import router as auth_router

app = FastAPI(title="BOY - Secretaria Virtual")

# Sesión firmada con cookie — max_age 7 días (Recordarme se indica en session["recordarme"])
app.add_middleware(
    SessionMiddleware,
    secret_key="d3f089a2c14b7e6f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1",
    max_age=7 * 24 * 3600,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(whatsapp_router)
app.include_router(admin_router)
app.include_router(auth_router)

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    import datetime
    return templates.TemplateResponse(
        request, "landing.html", {"year": datetime.datetime.now().year}
    )


@app.get("/health")
def health_check():
    """Endpoint para monitoreo de Render / uptime."""
    return {"status": "ok", "mensaje": "Bot de patinaje activo"}


## Ejecutar local:
##   uvicorn main:app --reload
##   o dar doble click en start-panel.bat
##
## Exponer con ngrok:
##   ngrok http 8000