
from flask import Flask, request, jsonify, render_template, session, redirect
import sqlite3, os, hashlib, secrets
from functools import wraps

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(APP_DIR, "azul.db")
app = Flask(__name__)
app.secret_key = os.environ.get("AZUL_SECRET_KEY", secrets.token_hex(32))

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      quantity_kg REAL NOT NULL,
      cost_usd REAL NOT NULL,
      target_usd REAL NOT NULL,
      countries TEXT DEFAULT '',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS analyses(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      product_id INTEGER NOT NULL,
      result_json TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(product_id) REFERENCES products(id)
    );
    """)
    c.commit(); c.close()

def hashpw(p):
    return hashlib.sha256(p.encode()).hexdigest()

def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if "user_id" not in session:
            return jsonify({"error":"No autenticado"}), 401
        return fn(*a, **kw)
    return wrapper

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/register")
def register():
    data=request.get_json(force=True)
    name=(data.get("name") or "").strip()
    email=(data.get("email") or "").strip().lower()
    password=data.get("password") or ""
    if not name or not email or len(password)<6:
        return jsonify({"error":"Nombre, email y contraseña de al menos 6 caracteres son obligatorios"}),400
    c=db()
    try:
        cur=c.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",(name,email,hashpw(password)))
        c.commit(); uid=cur.lastrowid
    except sqlite3.IntegrityError:
        c.close(); return jsonify({"error":"Ese email ya está registrado"}),409
    c.close(); session["user_id"]=uid; session["name"]=name
    return jsonify({"ok":True,"name":name})

@app.post("/api/login")
def login():
    data=request.get_json(force=True)
    c=db(); u=c.execute("SELECT * FROM users WHERE email=? AND password_hash=?",
                        ((data.get("email") or "").lower(),hashpw(data.get("password") or ""))).fetchone(); c.close()
    if not u: return jsonify({"error":"Email o contraseña incorrectos"}),401
    session["user_id"]=u["id"]; session["name"]=u["name"]
    return jsonify({"ok":True,"name":u["name"]})

@app.post("/api/logout")
def logout():
    session.clear(); return jsonify({"ok":True})

@app.get("/api/me")
def me():
    if "user_id" not in session: return jsonify({"authenticated":False})
    return jsonify({"authenticated":True,"name":session.get("name")})

@app.get("/api/products")
@login_required
def products():
    c=db(); rows=c.execute("SELECT * FROM products WHERE user_id=? ORDER BY id DESC",(session["user_id"],)).fetchall(); c.close()
    return jsonify([dict(r) for r in rows])

@app.post("/api/products")
@login_required
def add_product():
    d=request.get_json(force=True)
    try:
        name=(d.get("name") or "").strip(); qty=float(d.get("quantity_kg",0)); cost=float(d.get("cost_usd",0)); target=float(d.get("target_usd",0))
    except Exception: return jsonify({"error":"Datos numéricos inválidos"}),400
    if not name or qty<=0 or cost<0 or target<=0: return jsonify({"error":"Completá correctamente los datos"}),400
    c=db(); cur=c.execute("INSERT INTO products(user_id,name,quantity_kg,cost_usd,target_usd,countries) VALUES(?,?,?,?,?,?)",
                          (session["user_id"],name,qty,cost,target,d.get("countries",""))); c.commit()
    p=dict(c.execute("SELECT * FROM products WHERE id=?",(cur.lastrowid,)).fetchone()); c.close()
    return jsonify(p)

@app.delete("/api/products/<int:pid>")
@login_required
def delete_product(pid):
    c=db(); c.execute("DELETE FROM products WHERE id=? AND user_id=?",(pid,session["user_id"])); c.commit(); c.close()
    return jsonify({"ok":True})

@app.post("/api/analyze/<int:pid>")
@login_required
def analyze(pid):
    c=db(); p=c.execute("SELECT * FROM products WHERE id=? AND user_id=?",(pid,session["user_id"])).fetchone()
    if not p: c.close(); return jsonify({"error":"Producto no encontrado"}),404
    p=dict(p)
    revenue=p["quantity_kg"]*p["target_usd"]; production=p["quantity_kg"]*p["cost_usd"]
    margin=(revenue-production)/revenue*100 if revenue else 0
    # Motor inicial demostrativo. En producción se reemplaza por APIs/datos comerciales verificables.
    markets=[
      {"country":"Brasil","code":"BR","score":92,"reason":"Mercado regional y logística terrestre/marítima favorable."},
      {"country":"Chile","code":"CL","score":84,"reason":"Mercado regional con buena accesibilidad comercial."},
      {"country":"Estados Unidos","code":"US","score":78,"reason":"Mercado grande, sujeto a requisitos específicos del producto."}
    ]
    result={"product":p["name"],"quantity_kg":p["quantity_kg"],"revenue_usd":round(revenue,2),
            "production_usd":round(production,2),"gross_margin_pct":round(margin,1),"markets":markets,
            "disclaimer":"Estimación inicial. Antes de operar deben validarse aranceles, requisitos sanitarios, logística y compradores con fuentes actualizadas."}
    import json
    c.execute("INSERT INTO analyses(product_id,result_json) VALUES(?,?)",(pid,json.dumps(result,ensure_ascii=False)))
    c.commit(); c.close()
    return jsonify(result)

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
