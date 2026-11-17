from flask import g, render_template, request, redirect, session
from werkzeug.security import check_password_hash, generate_password_hash
from nucleo import app, NOMBRES_ROLES, menu_de, registrar
from datos import CLAVE_PRUEBA
import base_datos


def accesos_rapidos():
    accesos = []
    roles_vistos = []
    personas = base_datos.consultar("SELECT * FROM usuarios WHERE colegio_id = ? AND activo = 1 ORDER BY id", [g.colegio["id"]])
    for persona in personas:
        roles = base_datos.roles_de(persona["id"])
        if len(roles) > 0 and roles[0] not in roles_vistos:
            roles_vistos.append(roles[0])
            persona["rol_principal"] = NOMBRES_ROLES[roles[0]]
            accesos.append(persona)
    return accesos


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
