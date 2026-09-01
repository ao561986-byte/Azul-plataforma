from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/salud")
def salud():
    return jsonify({
        "success": True,
        "message": "AZUL funciona correctamente."
    })


@app.route("/registro", methods=["POST"])
def registro():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "No se recibieron datos."
        }), 400

    email = str(data.get("email", "")).strip()
    password = str(data.get("password", "")).strip()

    if not email or not password:
        return jsonify({
            "success": False,
            "error": "Completá el email y la contraseña."
        }), 400

    if len(password) < 6:
        return jsonify({
            "success": False,
            "error": "La contraseña debe tener al menos 6 caracteres."
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

    email = str(data.get("email", "")).strip()
    password = str(data.get("password", "")).strip()

    if not email or not password:
        return jsonify({
            "success": False,
            "error": "Completá el email y la contraseña."
        }), 400

    return jsonify({
        "success": True,
        "message": "Ingreso correcto.",
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
        "data": data
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

