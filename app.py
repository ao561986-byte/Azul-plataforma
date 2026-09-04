
import os
import sqlite3
import logging
from functools import wraps

from flask import (
Flask,
flash,
redirect,
render_template,
request,
session,
url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

=========================================================

AZUL - CONFIGURACIÓN

=========================================================

app = Flask(name)

app.secret_key = os.environ.get(
"SECRET_KEY",
"azul-clave-secreta-cambiar-en-render"
)

Logs visibles en Render

logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

=========================================================

BASE DE DATOS

=========================================================

BASE_DIR = os.path.dirname(os.path.abspath(file))

database_path = os.environ.get("DATABASE_PATH")

if database_path:
DATABASE = database_path
else:
# En Render usamos /tmp porque es escribible.
# En una instalación local usamos azul.db.
if os.environ.get("RENDER"):
DATABASE = "/tmp/azul.db"
else:
DATABASE = os.path.join(BASE_DIR, "azul.db")

Crear carpeta de la base de datos si corresponde

database_directory = os.path.dirname(DATABASE)

if database_directory:
os.makedirs(database_directory, exist_ok=True)

def get_db():
"""Abre la conexión SQLite."""
connection = sqlite3.connect(DATABASE, timeout=30)
connection.row_factory = sqlite3.Row
connection.execute("PRAGMA foreign_keys = ON")
return connection

def init_db():
"""Crea las tablas necesarias."""
connection = get_db()

try:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            currency TEXT NOT NULL,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
        """
    )

    connection.commit()

    app.logger.info(
        "BASE DE DATOS OK: %s",
        DATABASE
    )

except Exception:
    connection.rollback()
    app.logger.exception(
        "ERROR CREANDO LA BASE DE DATOS"
    )
    raise

finally:
    connection.close()

=========================================================

AUTENTICACIÓN

=========================================================

def login_required(function):
"""Protege páginas que requieren sesión."""

@wraps(function)
def decorated_function(*args, **kwargs):

    if "user_id" not in session:
        return redirect(url_for("login"))

    return function(*args, **kwargs)

return decorated_function

=========================================================

PÁGINA PRINCIPAL

=========================================================

@app.route("/")
def index():

try:

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return render_template("index.html")

except Exception:
    app.logger.exception(
        "ERROR MOSTRANDO INDEX"
    )

    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>AZUL</title>
    </head>
    <body>
        <h1>AZUL</h1>
        <p>La plataforma está funcionando, pero hubo un problema al cargar la página principal.</p>
        <a href="/login">Entrar</a>
    </body>
    </html>
    """, 500

=========================================================

REGISTRO

=========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

if request.method == "GET":

    try:
        return render_template("register.html")

    except Exception:
        app.logger.exception(
            "ERROR MOSTRANDO REGISTER.HTML"
        )

        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>AZUL - Crear cuenta</title>
        </head>
        <body>
            <h1>AZUL</h1>
            <h2>Crear cuenta</h2>

            <form method="POST" action="/register">

                <p>
                    <label>Email</label><br>
                    <input
                        type="email"
                        name="email"
                        required
                    >
                </p>

                <p>
                    <label>Contraseña</label><br>
                    <input
                        type="password"
                        name="password"
                        required
                        minlength="6"
                    >
                </p>

                <button type="submit">
                    Crear cuenta
                </button>

            </form>

            <p>
                <a href="/login">
                    Ya tengo una cuenta
                </a>
            </p>
        </body>
        </html>
        """, 200

# -----------------------------------------------------
# DATOS DEL FORMULARIO
# -----------------------------------------------------

email = request.form.get(
    "email",
    ""
).strip().lower()

password = request.form.get(
    "password",
    ""
)

if not email or not password:

    flash(
        "Completá el email y la contraseña."
    )

    try:
        return render_template(
            "register.html"
        )
    except Exception:
        return redirect(
            url_for("register")
        )

if len(password) < 6:

    flash(
        "La contraseña debe tener al menos 6 caracteres."
    )

    try:
        return render_template(
            "register.html"
        )
    except Exception:
        return redirect(
            url_for("register")
        )

# -----------------------------------------------------
# GUARDAR USUARIO
# -----------------------------------------------------

connection = None

try:

    connection = get_db()

    existing_user = connection.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    if existing_user:

        flash(
            "Ese email ya está registrado."
        )

        return render_template(
            "register.html"
        )

    password_hash = generate_password_hash(
        password
    )

    connection.execute(
        """
        INSERT INTO users
        (
            email,
            password
        )
        VALUES (?, ?)
        """,
        (
            email,
            password_hash
        )
    )

    connection.commit()

    app.logger.info(
        "USUARIO CREADO CORRECTAMENTE: %s",
        email
    )

except sqlite3.IntegrityError as error:

    if connection:
        connection.rollback()

    app.logger.exception(
        "ERROR DE INTEGRIDAD CREANDO USUARIO: %s",
        error
    )

    flash(
        "Ese email ya está registrado."
    )

    try:
        return render_template(
            "register.html"
        )
    except Exception:
        return redirect(
            url_for("register")
        )

except Exception as error:

    if connection:
        connection.rollback()

    app.logger.exception(
        "ERROR REGISTRANDO USUARIO: %s",
        error
    )

    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>AZUL - Error</title>
    </head>
    <body>
        <h1>AZUL</h1>

        <h2>No se pudo crear la cuenta</h2>

        <p>
            Ocurrió un problema al guardar el usuario.
        </p>

        <p>
            El error quedó registrado en los logs de Render.
        </p>

        <p>
            <a href="/register">
                Volver a crear cuenta
            </a>
        </p>
    </body>
    </html>
    """, 500

finally:

    if connection:
        connection.close()

flash(
    "Cuenta creada correctamente. Ahora podés ingresar."
)

return redirect(
    url_for("login")
)

=========================================================

LOGIN

=========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

if request.method == "GET":

    try:
        return render_template(
            "login.html"
        )

    except Exception:

        app.logger.exception(
            "ERROR MOSTRANDO LOGIN.HTML"
        )

        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>AZUL - Entrar</title>
        </head>
        <body>

            <h1>AZUL</h1>

            <h2>Iniciar sesión</h2>

            <form method="POST" action="/login">

                <p>
                    <label>Email</label><br>
                    <input
                        type="email"
                        name="email"
                        required
                    >
                </p>

                <p>
                    <label>Contraseña</label><br>
                    <input
                        type="password"
                        name="password"
                        required
                    >
                </p>

                <button type="submit">
                    Entrar
                </button>

            </form>

            <p>
                <a href="/register">
                    Crear cuenta
                </a>
            </p>

        </body>
        </html>
        """, 200

email = request.form.get(
    "email",
    ""
).strip().lower()

password = request.form.get(
    "password",
    ""
)

connection = None

try:

    connection = get_db()

    user = connection.execute(
        """
        SELECT
            id,
            email,
            password
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

except Exception as error:

    app.logger.exception(
        "ERROR BUSCANDO USUARIO EN LOGIN: %s",
        error
    )

    flash(
        "Error al acceder a AZUL."
    )

    try:
        return render_template(
            "login.html"
        )
    except Exception:
        return redirect(
            url_for("login")
        )

finally:

    if connection:
        connection.close()

if user:

    try:

        password_correct = check_password_hash(
            user["password"],
            password
        )

    except Exception as error:

        app.logger.exception(
            "ERROR VERIFICANDO CONTRASEÑA: %s",
            error
        )

        password_correct = False

else:

    password_correct = False

if password_correct:

    session.clear()

    session["user_id"] = user["id"]
    session["email"] = user["email"]

    app.logger.info(
        "LOGIN CORRECTO: %s",
        email
    )

    return redirect(
        url_for("dashboard")
    )

flash(
    "Email o contraseña incorrectos."
)

try:
    return render_template(
        "login.html"
    )
except Exception:
    return redirect(
        url_for("login")
    )

=========================================================

LOGOUT

=========================================================

@app.route("/logout")
def logout():

session.clear()

return redirect(
    url_for("index")
)

=========================================================

DASHBOARD

=========================================================

@app.route("/dashboard")
@login_required
def dashboard():

connection = None

try:

    connection = get_db()

    products = connection.execute(
        """
        SELECT
            id,
            name,
            quantity,
            unit_price,
            currency
        FROM products
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    return render_template(
        "dashboard.html",
        products=products,
        email=session.get("email")
    )

except Exception as error:

    app.logger.exception(
        "ERROR CARGANDO DASHBOARD: %s",
        error
    )

    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>AZUL</title>
    </head>
    <body>

        <h1>AZUL</h1>

        <p>
            No se pudo cargar el panel.
        </p>

        <p>
            El error quedó registrado en Render.
        </p>

        <p>
            <a href="/logout">
                Volver al inicio
            </a>
        </p>

    </body>
    </html>
    """, 500

finally:

    if connection:
        connection.close()

=========================================================

AGREGAR PRODUCTO

=========================================================

@app.route("/add_product", methods=["POST"])
@login_required
def add_product():

name = request.form.get(
    "name",
    ""
).strip()

quantity_text = request.form.get(
    "quantity",
    ""
).strip()

unit_price_text = request.form.get(
    "unit_price",
    ""
).strip()

currency = request.form.get(
    "currency",
    "USD"
).strip().upper()

if not name:

    flash(
        "Ingresá el nombre del producto."
    )

    return redirect(
        url_for("dashboard")
    )

if not quantity_text:

    flash(
        "Ingresá la cantidad."
    )

    return redirect(
        url_for("dashboard")
    )

if not unit_price_text:

    flash(
        "Ingresá el precio."
    )

    return redirect(
        url_for("dashboard")
    )

try:

    quantity = float(
        quantity_text.replace(",", ".")
    )

    unit_price = float(
        unit_price_text.replace(",", ".")
    )

except ValueError:

    flash(
        "Cantidad o precio inválido."
    )

    return redirect(
        url_for("dashboard")
    )

if quantity <= 0:

    flash(
        "La cantidad debe ser mayor que cero."
    )

    return redirect(
        url_for("dashboard")
    )

if unit_price <= 0:

    flash(
        "El precio debe ser mayor que cero."
    )

    return redirect(
        url_for("dashboard")
    )

allowed_currencies = {
    "USD",
    "UYU",
    "EUR",
    "BRL"
}

if currency not in allowed_currencies:
    currency = "USD"

connection = None

try:

    connection = get_db()

    connection.execute(
        """
        INSERT INTO products
        (
            user_id,
            name,
            quantity,
            unit_price,
            currency
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session["user_id"],
            name,
            quantity,
            unit_price,
            currency
        )
    )

    connection.commit()

    app.logger.info(
        "PRODUCTO GUARDADO: %s",
        name
    )

    flash(
        "Producto guardado correctamente."
    )

except Exception as error:

    if connection:
        connection.rollback()

    app.logger.exception(
        "ERROR GUARDANDO PRODUCTO: %s",
        error
    )

    flash(
        "No se pudo guardar el producto."
    )

finally:

    if connection:
        connection.close()

return redirect(
    url_for("dashboard")
)

=========================================================

ELIMINAR PRODUCTO

=========================================================

@app.route(
"/delete_product/"int:product_id" (int:product_id)",
methods=["POST"]
)
@login_required
def delete_product(product_id):

connection = None

try:

    connection = get_db()

    connection.execute(
        """
        DELETE FROM products
        WHERE id = ?
        AND user_id = ?
        """,
        (
            product_id,
            session["user_id"]
        )
    )

    connection.commit()

    flash(
        "Producto eliminado."
    )

except Exception as error:

    if connection:
        connection.rollback()

    app.logger.exception(
        "ERROR ELIMINANDO PRODUCTO: %s",
        error
    )

    flash(
        "No se pudo eliminar el producto."
    )

finally:

    if connection:
        connection.close()

return redirect(
    url_for("dashboard")
)

=========================================================

HEALTH CHECK

=========================================================

@app.route("/health")
def health():

try:

    connection = get_db()

    connection.execute(
        "SELECT 1"
    ).fetchone()

    connection.close()

    return {
        "status": "ok",
        "app": "AZUL"
    }, 200

except Exception as error:

    app.logger.exception(
        "HEALTH CHECK ERROR: %s",
        error
    )

    return {
        "status": "error",
        "app": "AZUL",
        "message": str(error)
    }, 500

=========================================================

ERROR 404

=========================================================

@app.errorhandler(404)
def page_not_found(error):

app.logger.warning(
    "404: %s",
    request.path
)

return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>AZUL</title>
</head>
<body>

    <h1>AZUL</h1>

    <p>
        Página no encontrada.
    </p>

    <a href="/">
        Volver a AZUL
    </a>

</body>
</html>
""", 404

=========================================================

ERROR 500

=========================================================

@app.errorhandler(500)
def internal_error(error):

app.logger.exception(
    "ERROR 500 EN AZUL: %s",
    error
)

return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>AZUL - Error</title>
</head>
<body>

    <h1>AZUL</h1>

    <h2>Ocurrió un error interno.</h2>

    <p>
        El error completo fue registrado en los logs de Render.
    </p>

    <p>
        <a href="/">
            Volver a AZUL
        </a>
    </p>

</body>
</html>
""", 500

=========================================================

INICIALIZACIÓN

=========================================================

try:

init_db()

except Exception as error:

app.logger.exception(
    "ERROR INICIALIZANDO AZUL: %s",
    error
)

=========================================================

ARRANQUE

=========================================================

if name == "main":

port = int(
    os.environ.get(
        "PORT",
        "5000"
    )
)

app.run(
    host="0.0.0.0",
    port=port,
    debug=False
)
