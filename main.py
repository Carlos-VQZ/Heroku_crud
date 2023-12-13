import fastapi
import sqlite3
import hashlib
import uuid  # Módulo para generar UUIDs
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import HTTPException, Depends
from datetime import datetime, timedelta


# Crea la base de datos
conn = sqlite3.connect("contactos.db")

app = fastapi.FastAPI()

# Token
security = HTTPBearer()
security_basic = HTTPBasic()


class Contacto(BaseModel):
    email: str
    nombre: str
    telefono: str

# Origins
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:5000",
    "https://herokufrontend23-2e5ad8e49cc5.herokuapp.com"
]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/register/")
def register(credentials: HTTPBasicCredentials = Depends(security_basic)):
    if not credentials.username or not credentials.password:
        raise HTTPException(status_code=401, detail="Acceso denegado: Credenciales faltantes")

    username = credentials.username
    password = credentials.password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    with sqlite3.connect("contactos.db") as conn:
        c = conn.cursor()
        c.execute('SELECT username FROM usuarios WHERE username=?', (username,))
        existing_user = c.fetchone()

        if existing_user:
            return {"error": "El usuario ya existe"}

        c.execute(
            'INSERT INTO usuarios (username, password) VALUES (?, ?)',
            (username, hashed_password)
        )
        conn.commit()

    return {"status": "Usuario registrado con éxito"}

@app.get("/login")
def login(credentials: HTTPBearer = Depends(security)):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Acceso denegado: Token faltante")

    token = credentials.credentials

    current_timestamp = datetime.utcnow().timestamp()

    with sqlite3.connect("contactos.db") as conn:
        c = conn.cursor()
        c.execute('SELECT username, expiration_timestamp FROM usuarios WHERE token=?', (token,))
        user_data = c.fetchone()

        if user_data and current_timestamp < user_data[1]:  # Verificar si el token está dentro del tiempo de expiración
            return {"mensaje": "Acceso permitido"}
        else:
            raise HTTPException(status_code=401, detail="Acceso denegado: Token inválido o expirado")

@app.get("/token/")
def generate_token(credentials: HTTPBasicCredentials = Depends(security_basic)):
    if not credentials.username or not credentials.password:
        raise HTTPException(status_code=401, detail="Acceso denegado: Credenciales faltantes")

    username = credentials.username
    password = credentials.password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    with sqlite3.connect("contactos.db") as conn:
        c = conn.cursor()
        c.execute('SELECT username, password FROM usuarios WHERE username=?', (username,))
        user = c.fetchone()

        if user and user[1] == hashed_password:
            timestamp = conn.execute('SELECT strftime("%s", "now")').fetchone()[0]
            token = hashlib.sha256((username + str(uuid.uuid4())).encode()).hexdigest()
            expiration_time = timedelta(minutes=120)  # Cambiar la duración a 1 minuto
            expiration_timestamp = (datetime.utcnow() + expiration_time).timestamp()
            c.execute(
                'UPDATE usuarios SET token=?, timestamp=?, expiration_timestamp=? WHERE username=?',
                (token, timestamp, expiration_timestamp, username)
            )
            conn.commit()
            
            response_data = {
                "token": token
            }
            return JSONResponse(content=response_data)
        else:
            raise HTTPException(status_code=401, detail="Acceso denegado: Credenciales inválidas")


@app.post("/contactos")
async def crear_contacto(contacto: Contacto, token: str = Depends(login)):
    """Crea un nuevo contacto."""
    # TODO Inserta el contacto en la base de datos y responde con un mensaje
    c = conn.cursor()
    c.execute('INSERT INTO contactos (email, nombre, telefono) VALUES (?, ?, ?)',
              (contacto.email, contacto.nombre, contacto.telefono))
    conn.commit()
    return contacto

@app.get("/contactos")
async def obtener_contactos(token: str = Depends(login)):
    """Obtiene todos los contactos."""
    # TODO Consulta todos los contactos de la base de datos y los envia en un JSON
    c = conn.cursor()
    c.execute('SELECT * FROM contactos;')
    response = []
    for row in c:
        contacto = {"email":row[0],"nombre":row[1], "telefono":row[2]}
        response.append(contacto)
    return response

@app.get("/contactos/{email}")
async def obtener_contacto(email: str, token: str = Depends(login)):
    """Obtiene un contacto por su email."""
    # Consulta el contacto por su email
    c = conn.cursor()
    c.execute('SELECT * FROM contactos WHERE email = ?', (email,))
    contacto = None
    for row in c:
        contacto = {"email":row[0],"nombre":row[1],"telefono":row[2]}
    return contacto

@app.put("/contactos/{email}")
async def actualizar_contacto(email: str, contacto: Contacto, token: str = Depends(login)):
    """Actualiza un contacto."""
    # TODO Actualiza el contacto en la base de datos
    c = conn.cursor()
    c.execute('UPDATE contactos SET nombre = ?, telefono = ? WHERE email = ?',
              (contacto.nombre, contacto.telefono, email))
    conn.commit()
    return contacto

@app.delete("/contactos/{email}")
async def eliminar_contacto(email: str, token: str = Depends(login)):
    """Elimina un contacto."""
    # TODO Elimina el contacto de la base de datos
    c = conn.cursor()
    c.execute('DELETE FROM contactos WHERE email = ?', (email,))
    conn.commit()
    return {"mensaje":"Contacto eliminado"}


