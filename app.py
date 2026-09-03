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
app.secret_key = os.environ.get("SECRET_KEY", "azul-clave-secreta")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "azul.db")


def get_db():
    """Abre la base de datos SQLite."""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Crea las tablas necesarias si no existen."""
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
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    connection.commit()
    connection.close()


def login_required(function):
    """Protege las páginas que requieren usuario."""
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    """Página principal."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Registro de nuevos usuarios."""
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

        existing_user = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if existing_user:
            connection.close()
            flash("Ese email ya está registrado.")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        connection.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, password_hash),
        )

        connection.commit()
        connection.close()

        flash("Cuenta creada correctamente. Ahora podés ingresar.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Inicio de sesión."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["email"] = user["email"]

            return redirect(url_for("dashboard"))

        flash("Email o contraseña incorrectos.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Cierra la sesión."""
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    """Panel principal del usuario."""
    connection = get_db()

    products = connection.execute(
        """
        SELECT id, name, quantity, unit_price, currency
        FROM products
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],),
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        products=products,
        email=session.get("email"),
    )


@app.route("/add_product", methods=["POST"])
@login_required
def add_product():
    """Guarda un nuevo producto."""
    name = request.form.get("name", "").strip()
    quantity_text = request.form.get("quantity", "").strip()
    unit_price_text = request.form.get("unit_price", "").strip()
    currency = request.form.get("currency", "USD").strip().upper()

    if not name or not quantity_text or not unit_price_text:
        flash("Completá todos los campos del producto.")
        return redirect(url_for("dashboard"))

    try:
        quantity = float(quantity_text.replace(",", "."))
        unit_price = float(unit_price_text.replace(",", "."))
    except ValueError:
        flash("Cantidad o precio inválido.")
        return redirect(url_for("dashboard"))

    if quantity <= 0 or unit_price <= 0:
        flash("La cantidad y el precio deben ser mayores que cero.")
        return redirect(url_for("dashboard"))

    if currency not in ("USD", "UYU", "EUR", "BRL"):
        currency = "USD"

    connection = get_db()

    connection.execute(
        """
        INSERT INTO products
        (user_id, name, quantity, unit_price, currency)
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
    connection.close()

    flash("Producto guardado correctamente.")
    return redirect(url_for("dashboard"))


@app.route("/delete_product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    """Elimina un producto perteneciente al usuario."""
    connection = get_db()

    connection.execute(
        """
        DELETE FROM products
        WHERE id = ? AND user_id = ?
        """,
        (product_id, session["user_id"]),
    )

    connection.commit()
    connection.close()

    flash("Producto eliminado.")
    return redirect(url_for("dashboard"))


@app.errorhandler(404)
def page_not_found(error):
    """Página no encontrada."""
    return "Página no encontrada.", 404


@app.errorhandler(500)
def internal_error(error):
    """Error interno."""
    return "Error interno de AZUL.", 500


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

