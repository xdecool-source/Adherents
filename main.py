import os
import tempfile

from datetime import date
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, Response, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from starlette.middleware.sessions import SessionMiddleware

from werkzeug.security import check_password_hash
from fftt_api import appel
from parser import parse_liste, filtre_saison, trier_points
from excel import export_excel

# ENVIRONNEMENT

load_dotenv()

# FASTAPI

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        "FLASK_SECRET_KEY",
        "change-me-in-railway"
    )
)
templates = Jinja2Templates(
    directory="templates"
)

print("")
print(" 🟢 Gestion : Export Adhérents de Spid : Startup")
print("")

# IDENTIFIANTS

APP_USER = os.getenv("APP_USER","")
APP_PASSWORD_HASH = os.getenv("APP_PASSWORD_HASH","")

# AUTHENTIFICATION

def authenticated(request: Request):
    return request.session.get("authenticated") is True

# PAGE UNIQUE

@app.get("/", response_class=HTMLResponse)

async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "authenticated": authenticated(request),
            "user": request.session.get("user", ""),
            "error": None,
        }
    )

@app.post("/login")

async def login(
    request: Request,
    username: str = Form(""),
    password: str = Form("")
):
    if (
        username == APP_USER
        and APP_PASSWORD_HASH
        and check_password_hash(
            APP_PASSWORD_HASH,
            password
        )
    ):
        request.session["authenticated"] = True
        request.session["user"] = username
        return {
            "success": True,
            "user": username
        }
    return {
        "success": False,
        "error": "Identifiant ou mot de passe incorrect."
    }

@app.get("/status")

async def status(request: Request):
    if authenticated(request):
        return {
            "authenticated": True,
            "user": request.session.get("user", "")
        }
    return {
        "authenticated": False,
        "user": ""
    }

# EXPORT EXCEL

@app.post("/export")

async def export(request: Request):
    if not authenticated(request):
        return JSONResponse(
            {
                "error": "Non authentifié"
            },
            status_code=401
        )
    club = os.getenv("FFTT_CLUB","11660007")
    xml = appel("xml_licence_b.php", club=club)
    joueurs = trier_points(filtre_saison( parse_liste(xml)))
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx",
        delete=False
    ) as tmp:
        temp_path = tmp.name
        
    try:
        export_excel(
            joueurs,
            temp_path
        )
        with open(
            temp_path,
            "rb"
        ) as f:
            data = f.read()
            
    finally:
        try:
            
            os.remove(temp_path)
        except OSError:
            pass
    today = date.today().strftime(
        "%Y-%m-%d"
    )
    filename = (
        f"licencies_{club}_{today}.xlsx"
    )
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        }
    )

# DÉCONNEXION SANS CHANGEMENT DE PAGE

@app.post("/logout")

async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(
        url="/",
        status_code=303
    )

# HEALTH

@app.get("/health")

async def health():
    return {
        "status": "OK"
    }