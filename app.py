
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/salud")
def salud():
    return "Azul Plataforma funcionando correctamente."


@app.route("/products", methods=["POST"])
def products():
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "No se recibieron datos"
        }), 400

    return jsonify({
        "success": True,
        "message": "Producto recibido correctamente",
        "product": data
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

