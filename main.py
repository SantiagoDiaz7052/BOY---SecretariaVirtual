from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers.whatsapp import router as whatsapp_router
from routers.admin import router as admin_router

app = FastAPI(title="Chatbot Secretaria - Patinaje")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(whatsapp_router)
app.include_router(admin_router)

@app.get("/")
def health_check():
    return {"status": "ok", "mensaje": "Bot de patinaje activo"}


## ejecutar server
##  uvicorn main:app --reload

## ngrok http 8000
