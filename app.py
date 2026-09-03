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

# En Render conviene configurar SECRET_KEY como variable de entorno.
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "azul-clave-temporal-cambiar-en-render",
)

DATABASE = os.environ.get("DATABASE_PATH", "azul.db")


def get_db():
    """Conecta con la base de datos."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea las tablas si todavía no existen."""
    conn = get_db()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            quantity REAL DEFAULT 0,
            unit_price REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()
    conn.close()


def login_required(view):
    """Protege las páginas que requieren sesión."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("index"))

        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    """Página principal."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return render_template("index.html")


@app.route("/registro", methods=["POST"])
def registro():
    """Registra un usuario nuevo."""
    data = request.get_json(silent=True) or request.form

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or "@" not in email:
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

    conn = get_db()

    try:
        conn.execute(
            """
            INSERT INTO users (email, password_hash)
            VALUES (?, ?)
            """,
            (
                email,
                generate_password_hash(password),
            ),
        )

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()

        return jsonify(
            {
                "ok": False,
                "mensaje": "Ese email ya está registrado.",
            }
        ), 409

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

    user = conn.execute(
        """
        SELECT id, email, password_hash
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    conn.close()

    if user is None:
        return jsonify(
            {
                "ok": False,
                "mensaje": "Email o contraseña incorrectos.",
            }
        ), 401

    if not check_password_hash(user["password_hash"], password):
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
            "redirect": url_for("dashboard"),
        }
    )


@app.route("/dashboard")
@login_required
def dashboard():
    """Panel principal del usuario."""
    conn = get_db()

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
    """Guarda un producto del usuario."""
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

    currency = (
        str(data.get("currency", "USD"))
        .strip()
        .upper()[:5]
        or "USD"
    )

    conn = get_db()

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
    conn.close()

    return jsonify(
        {
            "ok": True,
            "mensaje": "Producto guardado correctamente.",
        }
    )


@app.route("/logout")
def logout():
    """Cierra la sesión."""
    session.clear()

    return redirect(url_for("index"))


@app.route("/health")
def health():
    """Comprobación para Render."""
    return jsonify(
        {
            "ok": True,
            "app": "AZUL",
        }
    )


@app.errorhandler(404)
def not_found(_error):
    return jsonify(
        {
            "ok": False,
            "mensaje": "Ruta no encontrada.",
        }
    ), 404


@app.errorhandler(500)
def server_error(_error):
    return jsonify(
        {
            "ok": False,
            "mensaje": "Error interno del servidor.",
        }
    ), 500


# Crear la base de datos al iniciar.
init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
                )
