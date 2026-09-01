

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
Ahora hacé esto en GitHub
Entrá a tu repositorio Azul-plataforma.
Abrí app.py.
Tocá el lápiz ✏️ Edit.
Borrá todo lo que aparece.
Pegá el código de arriba.
Tocá Commit changes.
Esperá que GitHub guarde el cambio.
Render debería detectar el nuevo commit y comenzar otro deploy automáticamente.
Después entrá a:
https://azul-plataforma-real-v3.onrender.com
y probá nuevamente el inicio de sesión/producto.
Importante: esta 
