import os
import sqlite3
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


app = Flask(__name__)

# ---------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "azul-clave-secreta-cambiar-en-render"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# En Render /tmp es escribible.
# Si existe DATABASE_URL, se usa esa ruta.
DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(BASE_DIR, "azul.db")
)


# ---------------------------------------------------------
# BASE DE DATOS
# ---------------------------------------------------------

def get_db():
    """Abre SQLite."""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    """Crea las tablas necesarias."""
    connection = get_db()

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
    connection.close()


# ---------------------------------------------------------
# AUTENTICACIÓN
# ---------------------------------------------------------

def login_required(function):
    """Protege las páginas que requieren sesión."""

    @wraps(function)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return decorated_function


# ---------------------------------------------------------
# INICIO
# ---------------------------------------------------------

@app.route("/")
def index():
    """Página principal."""

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return render_template("index.html")


# ---------------------------------------------------------
# REGISTRO
# ---------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    """Registro de usuarios."""

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Completá el email y la contraseña.")
            return render_template("register.html")

        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.")
            return render_template("register.html")

        connection = get_db()

        try:
            existing_user = connection.execute(
                "SELECT id FROM users WHERE email = ?",
                (email,),
            ).fetchone()

            if existing_user:
                flash("Ese email ya está registrado.")
                return render_template("register.html")

            password_hash = generate_password_hash(password)

            connection.execute(
                """
                INSERT INTO users (email, password)
                VALUES (?, ?)
                """,
                (email, password_hash),
            )

            connection.commit()

        except sqlite3.Error as error:
            connection.rollback()
            app.logger.exception(
                "Error creando usuario: %s",
                error
            )
            flash("No se pudo crear la cuenta.")

            return render_template("register.html")

        finally:
            connection.close()

        flash("Cuenta creada correctamente. Ahora podés ingresar.")

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    """Inicio de sesión."""

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db()

        try:
            user = connection.execute(
                """
                SELECT id, email, password
                FROM users
                WHERE email = ?
                """,
                (email,),
            ).fetchone()

        except sqlite3.Error as error:
            app.logger.exception(
                "Error buscando usuario: %s",
                error
            )
            flash("Error al acceder a AZUL.")
            return render_template("login.html")

        finally:
            connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):
            session.clear()

            session["user_id"] = user["id"]
            session["email"] = user["email"]

            return redirect(url_for("dashboard"))

        flash("Email o contraseña incorrectos.")

    return render_template("login.html")


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

@app.route("/logout")
def logout():
    """Cierra la sesión."""

    session.clear()

    return redirect(url_for("index"))


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    """Panel del usuario."""

    connection = get_db()

    try:
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
            (session["user_id"],),
        ).fetchall()

    except sqlite3.Error as error:
        app.logger.exception(
            "Error cargando productos: %s",
            error
        )
        products = []
        flash("No se pudieron cargar los productos.")

    finally:
        connection.close()

    return render_template(
        "dashboard.html",
        products=products,
        email=session.get("email"),
    )


# ---------------------------------------------------------
# AGREGAR PRODUCTO
# ---------------------------------------------------------

@app.route("/add_product", methods=["POST"])
@login_required
def add_product():
    """Guarda un producto."""

    name = request.form.get("name", "").strip()

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

    if not name or not quantity_text or not unit_price_text:
        flash("Completá todos los campos del producto.")
        return redirect(url_for("dashboard"))

    try:
        quantity = float(
            quantity_text.replace(",", ".")
        )

        unit_price = float(
            unit_price_text.replace(",", ".")
        )

    except ValueError:
        flash("Cantidad o precio inválido.")
        return redirect(url_for("dashboard"))

    if quantity <= 0:
        flash("La cantidad debe ser mayor que cero.")
        return redirect(url_for("dashboard"))

    if unit_price <= 0:
        flash("El precio debe ser mayor que cero.")
        return redirect(url_for("dashboard"))

    allowed_currencies = {
        "USD",
        "UYU",
        "EUR",
        "BRL",
    }

    if currency not in allowed_currencies:
        currency = "USD"

    connection = get_db()

    try:
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
                currency,
            ),
        )

        connection.commit()

    except sqlite3.Error as error:
        connection.rollback()

        app.logger.exception(
            "Error guardando producto: %s",
            error
        )

        flash("No se pudo guardar el producto.")

        return redirect(url_for("dashboard"))

    finally:
        connection.close()

    flash("Producto guardado correctamente.")

    return redirect(url_for("dashboard"))


# ---------------------------------------------------------
# ELIMINAR PRODUCTO
# ---------------------------------------------------------

@app.route(
    "/delete_product/<int:product_id>",
    methods=["POST"]
)
@login_required
def delete_product(product_id):
    """Elimina un producto del usuario."""

    connection = get_db()

    try:
        connection.execute(
            """
            DELETE FROM products
            WHERE id = ?
            AND user_id = ?
            """,
            (
                product_id,
                session["user_id"],
            ),
        )

        connection.commit()

    except sqlite3.Error as error:
        connection.rollback()

        app.logger.exception(
            "Error eliminando producto: %s",
            error
        )

        flash("No se pudo eliminar el producto.")

        return redirect(url_for("dashboard"))

    finally:
        connection.close()

    flash("Producto eliminado.")

    return redirect(url_for("dashboard"))


# ---------------------------------------------------------
# ERRORES
# ---------------------------------------------------------

@app.errorhandler(404)
def page_not_found(error):
    """Página inexistente."""

    return (
        """
        <h1>AZUL</h1>
        <p>Página no encontrada.</p>
        <a href="/">Volver a AZUL</a>
        """,
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    """
    Error interno.

    Se registra el error completo en los logs de Render
    para poder identificar el problema real.
    """

    app.logger.exception(
        "ERROR 500 EN AZUL: %s",
        error
    )

    return (
        """
        <h1>AZUL</h1>
        <p>Ocurrió un error interno.</p>
        <p>Revisá los logs de Render para ver el detalle.</p>
        """,
        500,
    )


# ---------------------------------------------------------
# INICIALIZACIÓN
# ---------------------------------------------------------

try:
    init_db()
except Exception as error:
    app.logger.exception(
        "ERROR INICIALIZANDO LA BASE DE DATOS: %s",
        error
    )


# ---------------------------------------------------------
# ARRANQUE
# ---------------------------------------------------------

if __name__ == "__main__":

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
