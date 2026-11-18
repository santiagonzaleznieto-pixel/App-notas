import os
from datetime import datetime, timedelta
from flask import g, render_template, request, redirect, session, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from nucleo import app, NOMBRES_ROLES, menu_de, registrar, CON_DATOS_DE_EJEMPLO, ZONA_COLOMBIA
from datos import CLAVE_PRUEBA
import base_datos


def modo_pruebas():
    if not CON_DATOS_DE_EJEMPLO:
        return False
    if os.environ.get("MODO_PRUEBAS", "") == "1":
        return True
    return os.environ.get("CLAVE_SECRETA", "") == ""


def accesos_rapidos():
    accesos = []
    if not modo_pruebas():
        return accesos
    roles_vistos = []
    personas = base_datos.consultar("SELECT * FROM usuarios WHERE colegio_id = ? AND activo = 1 ORDER BY id", [g.colegio["id"]])
    for persona in personas:
        roles = base_datos.roles_de(persona["id"])
        if len(roles) > 0 and roles[0] not in roles_vistos:
            roles_vistos.append(roles[0])
            persona["rol_principal"] = NOMBRES_ROLES[roles[0]]
            accesos.append(persona)
    return accesos


def intentos_fallidos_recientes(usuario):
    desde = (datetime.now(ZONA_COLOMBIA) - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M")
    fila = base_datos.consultar_uno(
        "SELECT COUNT(*) AS total FROM registro_accesos WHERE accion = 'Intento fallido de ingreso' AND detalle = ? AND fecha >= ?",
        [usuario, desde],
    )
    return fila["total"]


@app.route("/", methods=["GET", "POST"])
def login():
    if g.yo is not None:
        return redirect("/inicio")

    error = ""
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip().lower()
        clave = request.form.get("clave", "")
        persona = base_datos.buscar_usuario(usuario)
        if usuario == "" or clave == "":
            error = "Escribe tu usuario y tu contraseña."
        elif intentos_fallidos_recientes(usuario) >= 5:
            error = "Hubo demasiados intentos fallidos con este usuario. Espera 15 minutos e inténtalo de nuevo."
        elif persona is None or not check_password_hash(persona["clave"], clave):
            error = "El usuario o la contraseña no son correctos."
            registrar("Intento fallido de ingreso", usuario)
        elif persona["activo"] == 0:
            error = "Tu usuario está desactivado. Habla con la secretaría del colegio."
        else:
            session.clear()
            session["usuario_id"] = persona["id"]
            g.yo = persona
            registrar("Inicio de sesión", "")
            return redirect("/inicio")

    return render_template("login.html", error=error, accesos=accesos_rapidos(), clave_prueba=CLAVE_PRUEBA)


@app.route("/privacidad")
def privacidad():
    rector = None
    rectores = base_datos.usuarios_con_rol(g.colegio["id"], "rector")
    if len(rectores) > 0:
        rector = rectores[0]
    return render_template("privacidad.html", activo="", rector=rector)


@app.route("/sw.js")
def trabajador_sin_conexion():
    respuesta = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
    respuesta.headers["Cache-Control"] = "no-cache"
    return respuesta


@app.route("/sin-conexion")
def sin_conexion():
    return render_template("sin_conexion.html", activo="")


@app.route("/salir")
def salir():
    session.clear()
    return redirect("/")


@app.route("/inicio")
def inicio():
    if g.yo is None:
        return redirect("/")
    nombres = []
    for rol in g.yo["roles"]:
        nombres.append(NOMBRES_ROLES[rol])
    return render_template("panel.html", activo="inicio", opciones=menu_de(g.yo), nombres=nombres)


@app.route("/mi-cuenta", methods=["GET", "POST"])
def mi_cuenta():
    if g.yo is None:
        return redirect("/")

    errores = []
    mensaje = ""
    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "datos":
            correo = request.form.get("correo", "").strip()
            telefono = request.form.get("telefono", "").strip()
            if correo != "" and ("@" not in correo or "." not in correo):
                errores.append("El correo no parece válido.")
            else:
                base_datos.ejecutar("UPDATE usuarios SET correo = ?, telefono = ? WHERE id = ?", [correo, telefono, g.yo["id"]])
                registrar("Actualizó sus datos de contacto", "")
                mensaje = "Datos guardados."
        elif accion == "clave":
            actual = request.form.get("actual", "")
            nueva = request.form.get("nueva", "")
            repetida = request.form.get("repetida", "")
            if not check_password_hash(g.yo["clave"], actual):
                errores.append("La contraseña actual no es correcta.")
            elif len(nueva) < 8:
                errores.append("La contraseña nueva debe tener al menos 8 caracteres.")
            elif nueva != repetida:
                errores.append("Las dos contraseñas nuevas no coinciden.")
            elif nueva == actual:
                errores.append("La contraseña nueva debe ser distinta de la actual.")
            else:
                base_datos.ejecutar(
                    "UPDATE usuarios SET clave = ?, debe_cambiar_clave = 0 WHERE id = ?",
                    [generate_password_hash(nueva), g.yo["id"]],
                )
                registrar("Cambió su contraseña", "")
                mensaje = "Contraseña cambiada. Úsala la próxima vez que entres."
        actualizado = base_datos.buscar_usuario_por_id(g.yo["id"])
        actualizado["roles"] = g.yo["roles"]
        g.yo = actualizado

    return render_template("mi_cuenta.html", activo="cuenta", errores=errores, mensaje=mensaje)
