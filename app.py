import os
import sqlite3
from functools import wraps

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

# En Render, configurá SECRET_KEY como variable de entorno.
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "azul-clave-temporal-cambiar-en-render",
)

# SQLite. Si DATABASE_PATH no existe, usa azul.db en la carpeta del proyecto.
DATABASE = os.environ.get("DATABASE_PATH", "azul.db")


def get_db():
    """Abre una conexión a SQLite con soporte para diccionarios."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Crea las tablas necesarias al iniciar la aplicación."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                unit_price REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'USD',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

        conn.commit()
    finally:
        conn.close()


def login_required(view):
    """Protege las rutas que requieren usuario autenticado."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    """Página de inicio, login y registro."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return render_template("index.html", dashboard=False)


@app.route("/registro", methods=["POST"])
def registro():
    """Crea una cuenta nueva."""
    data = request.get_json(silent=True) or request.form

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(
            {
                "ok": False,
                "mensaje": "Ingresá un email válido.",
            }
        ), 400

    if len(password) < 6:
        return jsonify(
            {
                "ok": False,
                "mensaje": "La contraseña debe tener al menos 6 caracteres.",
            }
        ), 400

    password_hash = generate_password_hash(password)
    conn = get_db()

    try:
        conn.execute(
            """
            INSERT INTO users (email, password_hash)
            VALUES (?, ?)
            """,
            (email, password_hash),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify(
            {
                "ok": False,
                "mensaje": "Ese email ya está registrado.",
            }
        ), 409
    finally:
        conn.close()

    return jsonify(
        {
            "ok": True,
            "mensaje": "Cuenta creada correctamente. Ahora podés ingresar.",
        }
    )


@app.route("/login", methods=["POST"])
def login():
    """Inicia sesión."""
    data = request.get_json(silent=True) or request.form

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify(
            {
                "ok": False,
                "mensaje": "Completá email y contraseña.",
            }
        ), 400

    conn = get_db()

    try:
        user = conn.execute(
            """
            SELECT id, email, password_hash
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()
    finally:
        conn.close()

    if user is None or not check_password_hash(
        user["password_hash"], password
    ):
        return jsonify(
            {
                "ok": False,
                "mensaje": "Email o contraseña incorrectos.",
            }
        ), 401

    session.clear()
    session["user_id"] = user["id"]
    session["email"] = user["email"]

    return jsonify(
        {
            "ok": True,
            "mensaje": "Sesión iniciada correctamente.",
            "redirect": url_for("dashboard"),
        }
    )


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    """Muestra el panel y solamente los productos del usuario."""
    conn = get_db()

    try:
        products = conn.execute(
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
            (session["user_id"],),
        ).fetchall()
    finally:
        conn.close()

    return render_template(
        "index.html",
        dashboard=True,
        email=session.get("email", ""),
        products=products,
    )


@app.route("/productos", methods=["POST"])
@login_required
def add_product():
    """Guarda un producto perteneciente al usuario conectado."""
    data = request.get_json(silent=True) or request.form

    name = str(data.get("name", "")).strip()

    if not name:
        return jsonify(
            {
                "ok": False,
                "mensaje": "Ingresá el nombre del producto.",
            }
        ), 400

    try:
        quantity = float(data.get("quantity", 0) or 0)
        unit_price = float(data.get("unit_price", 0) or 0)
    except (TypeError, ValueError):
        return jsonify(
            {
                "ok": False,
                "mensaje": "Cantidad o precio inválido.",
            }
        ), 400

    if quantity < 0 or unit_price < 0:
        return jsonify(
            {
                "ok": False,
                "mensaje": "La cantidad y el precio no pueden ser negativos.",
            }
        ), 400

    currency = (
        str(data.get("currency", "USD")).strip().upper()[:5] or "USD"
    )

    conn = get_db()

    try:
        conn.execute(
            """
            INSERT INTO products (
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
                currency,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify(
        {
            "ok": True,
            "mensaje": "Producto guardado correctamente.",
        }
    )


@app.route("/logout", methods=["GET"])
def logout():
    """Cierra la sesión."""
    session.clear()
    return redirect(url_for("index"))


@app.route("/health", methods=["GET"])
def health():
    """Comprobación de funcionamiento para Render."""
    return jsonify(
        {
            "ok": True,
            "app": "AZUL",
            "status": "online",
        }
    )


@app.errorhandler(404)
def not_found(_error):
    """Respuesta para rutas inexistentes."""
    return jsonify(
        {
            "ok": False,
            "mensaje": "Ruta no encontrada.",
        }
    ), 404


@app.errorhandler(500)
def server_error(_error):
    """Respuesta para errores internos."""
    return jsonify(
        {
            "ok": False,
            "mensaje": "Error interno del servidor.",
        }
    ), 500


# Inicializa la base de datos dentro del contexto de Flask.
with app.app_context():
    init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )

