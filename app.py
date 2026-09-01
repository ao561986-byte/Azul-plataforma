
import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Base de datos
DATABASE = os.environ.get("DATABASE_PATH", "azul.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL DEFAULT 0,
            cost REAL DEFAULT 0,
            quantity INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# Crear la base de datos al iniciar
init_db()


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/salud")
def salud():
    return jsonify({
        "ok": True,
        "mensaje": "AZUL está funcionando correctamente"
    })


@app.route("/registro", methods=["POST"])
@app.route("/register", methods=["POST"])
def registro():
    try:
        datos = request.get_json(silent=True)

        if not datos:
            return jsonify({
                "ok": False,
                "mensaje": "No se recibieron datos."
            }), 400

        email = str(datos.get("email", "")).strip().lower()
        password = str(datos.get("password", ""))

        if not email or not password:
            return jsonify({
                "ok": False,
                "mensaje": "Completá email y contraseña."
            }), 400

        if len(password) < 6:
            return jsonify({
                "ok": False,
                "mensaje": "La contraseña debe tener al menos 6 caracteres."
            }), 400

        conn = get_db()

        usuario_existente = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if usuario_existente:
            conn.close()
            return jsonify({
                "ok": False,
                "mensaje": "Ese email ya está registrado."
            }), 409

        password_hash = generate_password_hash(password)

        conn.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, password_hash)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "ok": True,
            "mensaje": "Cuenta creada correctamente. Ahora podés ingresar."
        }), 201

    except Exception as e:
        print("ERROR REGISTRO:", e)

        return jsonify({
            "ok": False,
            "mensaje": "Error interno al crear la cuenta."
        }), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        datos = request.get_json(silent=True)

        if not datos:
            return jsonify({
                "ok": False,
                "mensaje": "No se recibieron datos."
            }), 400

        email = str(datos.get("email", "")).strip().lower()
        password = str(datos.get("password", ""))

        if not email or not password:
            return jsonify({
                "ok": False,
                "mensaje": "Completá email y contraseña."
            }), 400

        conn = get_db()

        usuario = conn.execute(
            "SELECT id, email, password FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if not usuario:
            return jsonify({
                "ok": False,
                "mensaje": "Email o contraseña incorrectos."
            }), 401

        if not check_password_hash(usuario["password"], password):
            return jsonify({
                "ok": False,
                "mensaje": "Email o contraseña incorrectos."
            }), 401

        return jsonify({
            "ok": True,
            "mensaje": "Ingreso correcto.",
            "usuario": {
                "id": usuario["id"],
                "email": usuario["email"]
            }
        })

    except Exception as e:
        print("ERROR LOGIN:", e)

        return jsonify({
            "ok": False,
            "mensaje": "Error interno al iniciar sesión."
        }), 500


@app.route("/products", methods=["GET"])
def obtener_productos():
    try:
        user_id = request.args.get("user_id", type=int)

        if not user_id:
            return jsonify({
                "ok": False,
                "mensaje": "Falta user_id."
            }), 400

        conn = get_db()

        productos = conn.execute(
            """
            SELECT id, name, price, cost, quantity
            FROM products
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

        conn.close()

        return jsonify({
            "ok": True,
            "productos": [dict(producto) for producto in productos]
        })

    except Exception as e:
        print("ERROR PRODUCTS:", e)

        return jsonify({
            "ok": False,
            "mensaje": "No se pudieron cargar los productos."
        }), 500


@app.route("/products", methods=["POST"])
def crear_producto():
    try:
        datos = request.get_json(silent=True)

        if not datos:
            return jsonify({
                "ok": False,
                "mensaje": "No se recibieron datos."
            }), 400

        user_id = datos.get("user_id")
        name = str(datos.get("name", "")).strip()
        price = float(datos.get("price", 0))
        cost = float(datos.get("cost", 0))
        quantity = int(datos.get("quantity", 0))

        if not user_id or not name:
            return jsonify({
                "ok": False,
                "mensaje": "Faltan datos del producto."
            }), 400

        conn = get_db()

        cursor = conn.execute(
            """
            INSERT INTO products
            (user_id, name, price, cost, quantity)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name, price, cost, quantity)
        )

        conn.commit()

        producto_id = cursor.lastrowid

        conn.close()

        return jsonify({
            "ok": True,
            "mensaje": "Producto guardado correctamente.",
            "producto_id": producto_id
        }), 201

    except Exception as e:
        print("ERROR CREAR PRODUCTO:", e)

        return jsonify({
            "ok": False,
            "mensaje": "No se pudo guardar el producto."
        }), 500


@app.errorhandler(404)
def pagina_no_encontrada(error):
    return jsonify({
        "ok": False,
        "mensaje": "Ruta no encontrada."
    }), 404


@app.errorhandler(500)
def error_servidor(error):
    return jsonify({
        "ok": False,
        "mensaje": "Error del servidor."
    }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
