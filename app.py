
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/salud")
def salud():
    return jsonify({
        "success": True,
        "message": "Azul Plataforma funcionando correctamente."
    })


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "No se recibieron datos."
        }), 400

    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({
            "success": False,
            "error": "Email y contraseña son obligatorios."
        }), 400

    return jsonify({
        "success": True,
        "message": "Cuenta creada correctamente.",
        "email": email
    })


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "No se recibieron datos."
        }), 400

    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({
            "success": False,
            "error": "Email y contraseña son obligatorios."
        }), 400

    return jsonify({
        "success": True,
        "message": "Inicio de sesión correcto.",
        "email": email
    })


@app.route("/products", methods=["POST"])
def products():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "No se recibieron datos."
        }), 400

    return jsonify({
        "success": True,
        "message": "Producto recibido correctamente.",
        "product": data
    })


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
