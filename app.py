import os
import sqlite3

from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# =========================================================
# CONFIGURACIÓN
# =========================================================

DATABASE = os.environ.get("DATABASE_PATH", "azul.db")


# =========================================================
# BASE DE DATOS
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            cost REAL NOT NULL DEFAULT 0,
            quantity INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# Crear base de datos al iniciar
try:
    init_db()
    print("BASE DE DATOS: OK")
except Exception as e:
    print("ERROR BASE DE DATOS:", repr(e))


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

@app.route("/")
def inicio():
    return render_template("index.html")


# =========================================================
# SALUD DEL SERVIDOR
# =========================================================

@app.route("/salud", methods=["GET"])
def salud():
    conn = None

    try:
        conn = get_db()
        conn.execute("SELECT 1").fetchone()

        return jsonify({
            "ok": True,
            "mensaje": "AZUL está funcionando correctamente"
        })

    except Exception as e:
        print("ERROR SALUD:", repr(e))

        return jsonify({
            "ok": False,
            "mensaje": "La base de datos no está disponible."
        }), 500

    finally:
        if conn:
            conn.close()


# =========================================================
# OBTENER DATOS
# =========================================================

def obtener_datos():
    """
    Acepta JSON y formularios tradicionales.
    """

    datos = request.get_json(silent=True)

    if datos:
        return datos

    return request.form.to_dict()


# =========================================================
# REGISTRO
# =========================================================

@app.route("/registro", methods=["POST"])
@app.route("/register", methods=["POST"])
def registro():

    conn = None

    try:
        datos = obtener_datos()

        print("DATOS REGISTRO:", datos)

        if not datos:
            return jsonify({
                "ok": False,
                "mensaje": "No se recibieron datos."
            }), 400

        email = str(
            datos.get("email", "")
        ).strip().lower()

        password = str(
            datos.get("password", "")
        )

        if not email or not password:
            return jsonify({
                "ok": False,
                "mensaje": "Completá email y contraseña."
            }), 400

        if "@" not in email:
            return jsonify({
                "ok": False,
                "mensaje": "Ingresá un email válido."
            }), 400

        if len(password) < 6:
            return jsonify({
                "ok": False,
                "mensaje": "La contraseña debe tener al menos 6 caracteres."
            }), 400

        conn = get_db()

        usuario_existente = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if usuario_existente:
            return jsonify({
                "ok": False,
                "mensaje": "Ese email ya está registrado."
            }), 409

        password_hash = generate_password_hash(password)

        conn.execute(
            """
            INSERT INTO users (email, password)
            VALUES (?, ?)
            """,
            (email, password_hash)
        )

        conn.commit()

        print("USUARIO CREADO:", email)

        return jsonify({
            "ok": True,
            "mensaje": "Cuenta creada correctamente. Ahora podés ingresar."
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "ok": False,
            "mensaje": "Ese email ya está registrado."
        }), 409

    except Exception as e:
        print("ERROR REGISTRO:", repr(e))

        return jsonify({
            "ok": False,
            "mensaje": "Error interno al crear la cuenta."
        }), 500

    finally:
        if conn:
            conn.close()


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["POST"])
def login():

    conn = None

    try:
        datos = obtener_datos()

        print("DATOS LOGIN:", datos)

        if not datos:
            return jsonify({
                "ok": False,
                "mensaje": "No se recibieron datos."
            }), 400

        email = str(
            datos.get("email", "")
        ).strip().lower()

        password = str(
            datos.get("password", "")
        )

        if not email or not password:
            return jsonify({
                "ok": False,
                "mensaje": "Completá email y contraseña."
            }), 400

        conn = get_db()

        usuario = conn.execute(
            """
            SELECT id, email, password
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if not usuario:
            return jsonify({
                "ok": False,
                "mensaje": "Email o contraseña incorrectos."
            }), 401

        if not check_password_hash(
            usuario["password"],
            password
        ):
            return jsonify({
                "ok": False,
                "mensaje": "Email o contraseña incorrectos."
            }), 401

        print("LOGIN CORRECTO:", email)

        return jsonify({
            "ok": True,
            "mensaje": "Ingreso correcto.",
            "user_id": usuario["id"],
            "email": usuario["email"]
        })

    except Exception as e:
        print("ERROR LOGIN:", repr(e))

        return jsonify({
            "ok": False,
            "mensaje": "Error interno al iniciar sesión."
        }), 500

    finally:
        if conn:
            conn.close()


# =========================================================
# PRODUCTOS - LISTAR
# =========================================================

@app.route("/products", methods=["GET"])
def obtener_productos():

    conn = None

    try:
        user_id = request.args.get(
            "user_id",
            type=int
        )

        if not user_id:
            return jsonify({
                "ok": False,
                "mensaje": "Falta el usuario."
            }), 400

        conn = get_db()

        productos = conn.execute(
            """
            SELECT
                id,
                user_id,
                name,
                price,
                cost,
                quantity
            FROM products
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

        return jsonify({
            "ok": True,
            "productos": [
                dict(producto)
                for producto in productos
            ]
        })

    except Exception as e:
        print("ERROR PRODUCTS:", repr(e))

        return jsonify({
            "ok": False,
            "mensaje": "No se pudieron cargar los productos."
        }), 500

    finally:
        if conn:
            conn.close()


# =========================================================
# PRODUCTOS - CREAR
# =========================================================

@app.route("/products", methods=["POST"])
def crear_producto():

    conn = None

    try:
        datos = obtener_datos()

        if not datos:
            return jsonify({
                "ok": False,
                "mensaje": "No se recibieron datos."
            }), 400

        try:
            user_id = int(datos.get("user_id"))
            price = float(datos.get("price", 0))
            cost = float(datos.get("cost", 0))
            quantity = int(datos.get("quantity", 0))

        except (ValueError, TypeError):
            return jsonify({
                "ok": False,
                "mensaje": "Los datos del producto no son válidos."
            }), 400

        name = str(
            datos.get("name", "")
        ).strip()

        if not user_id:
            return jsonify({
                "ok": False,
                "mensaje": "Falta el usuario."
            }), 400

        if not name:
            return jsonify({
                "ok": False,
                "mensaje": "Ingresá el nombre del producto."
            }), 400

        if price < 0 or cost < 0 or quantity < 0:
            return jsonify({
                "ok": False,
                "mensaje": "Los valores no pueden ser negativos."
            }), 400

        conn = get_db()

        cursor = conn.execute(
            """
            INSERT INTO products (
                user_id,
                name,
                price,
                cost,
                quantity
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name,
                price,
                cost,
                quantity
            )
        )

        conn.commit()

        producto_id = cursor.lastrowid

        print("PRODUCTO CREADO:", producto_id)

        return jsonify({
            "ok": True,
            "mensaje": "Producto guardado correctamente.",
            "producto_id": producto_id
        }), 201

    except Exception as e:
        print("ERROR CREAR PRODUCTO:", repr(e))

        return jsonify({
            "ok": False,
            "mensaje": "No se pudo guardar el producto."
        }), 500

    finally:
        if conn:
            conn.close()


# =========================================================
# ERRORES
# =========================================================

@app.errorhandler(404)
def pagina_no_encontrada(error):
    return jsonify({
        "ok": False,
        "mensaje": "Ruta no encontrada."
    }), 404


@app.errorhandler(405)
def metodo_no_permitido(error):
    return jsonify({
        "ok": False,
        "mensaje": "Método no permitido."
    }), 405


@app.errorhandler(500)
def error_servidor(error):
    return jsonify({
        "ok": False,
        "mensaje": "Error del servidor."
    }), 500


# =========================================================
# INICIAR SERVIDOR
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
