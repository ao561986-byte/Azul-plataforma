
Escritura
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/salud")
def salud():
    return "Azul Plataforma funcionando correctamente."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
Nombre del archivo: Aplicacion.py
Ubicación: directamente dentro de Azul-plataforma, no dentro de templates.
La estructura Azul-plataforma/
├── app.py
├── requirements.txt
├── Procfile
└── templates/
    └── index.html
