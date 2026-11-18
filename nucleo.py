import os
from datetime import datetime, timedelta, timezone
from flask import Flask, g, session, redirect, request, render_template
import base_datos
import semilla

app = Flask(__name__)
app.secret_key = os.environ.get("CLAVE_SECRETA", "solo-para-pruebas-en-mi-computador")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
if os.environ.get("CLAVE_SECRETA", "") != "":
    app.config["SESSION_COOKIE_SECURE"] = True

CON_DATOS_DE_EJEMPLO = os.environ.get("DATOS_DE_EJEMPLO", "1") == "1"

base_datos.crear_tablas(base_datos.TABLAS)
SEMBRAR = CON_DATOS_DE_EJEMPLO and base_datos.reclamar_siembra(1)
if SEMBRAR and base_datos.tabla_vacia("colegios"):
    semilla.sembrar()

COLEGIO_PILOTO = int(os.environ.get("COLEGIO_PORTADA", "1"))

NOMBRES_ROLES = {
    "administrador": "Administración",
    "rector": "Rectoría",
    "coordinador": "Coordinación",
    "docente": "Docente",
    "director": "Director de grupo",
    "secretaria": "Secretaría académica",
    "orientador": "Orientación escolar",
    "tesoreria": "Tesorería",
    "bibliotecario": "Biblioteca",
    "enfermeria": "Enfermería",
    "porteria": "Portería",
    "estudiante": "Estudiante",
    "acudiente": "Acudiente",
}

DIRECTIVOS = ["administrador", "rector", "coordinador"]
VEN_TODOS_LOS_ESTUDIANTES = ["administrador", "rector", "coordinador", "secretaria", "orientador"]

MENU = []


def agregar_menu(clave, titulo, ruta, roles, descripcion):
    MENU.append({"clave": clave, "titulo": titulo, "ruta": ruta, "roles": roles, "descripcion": descripcion})


def tiene_rol(yo, rol):
    return yo is not None and rol in yo["roles"]


def tiene_alguno(yo, roles):
    if yo is None:
        return False
    for rol in roles:
        if rol in yo["roles"]:
            return True
    return False


def menu_de(yo):
    opciones = []
    for opcion in MENU:
        if tiene_alguno(yo, opcion["roles"]):
            opciones.append(opcion)
    return opciones


ZONA_COLOMBIA = timezone(timedelta(hours=-5))


def hoy():
    return datetime.now(ZONA_COLOMBIA).date().isoformat()


def ahora():
    return datetime.now(ZONA_COLOMBIA).strftime("%Y-%m-%d %H:%M")


def cargar_usuario(usuario_id):
    persona = base_datos.buscar_usuario_por_id(usuario_id)
    if persona is None or persona["activo"] == 0:
        return None
    persona["roles"] = base_datos.roles_de(persona["id"])
    colegio = base_datos.buscar_colegio(persona["colegio_id"])
    if len(base_datos.grupos_dirigidos(persona["id"], colegio["anio"])) > 0:
        persona["roles"].append("director")
    return persona


def registrar(accion, detalle):
    usuario_id = None
    if g.yo is not None:
        usuario_id = g.yo["id"]
    base_datos.registrar(g.colegio["id"], usuario_id, ahora(), accion, detalle)


def desempeno(nota):
    colegio = g.colegio
    if nota is None:
        return "Pendiente"
    elif nota >= colegio["limite_superior"]:
        return "Superior"
    elif nota >= colegio["limite_alto"]:
        return "Alto"
    elif nota >= colegio["limite_basico"]:
        return "Básico"
    else:
        return "Bajo"


NIVELES_DESEMPENO = ["Superior", "Alto", "Básico", "Bajo"]


def desempeno_definitivo(valor, manual):
    if manual in NIVELES_DESEMPENO:
        return manual
    return desempeno(valor)


def fecha_valida(texto):
    if len(texto) != 10 or texto[4] != "-" or texto[7] != "-":
        return False
    for posicion in range(10):
        if posicion != 4 and posicion != 7 and texto[posicion] not in "0123456789":
            return False
    mes = int(texto[5:7])
    dia = int(texto[8:10])
    return mes >= 1 and mes <= 12 and dia >= 1 and dia <= 31


def promedio(lista):
    suma = 0
    cantidad = 0
    for nota in lista:
        if nota is not None:
            suma = suma + nota
            cantidad = cantidad + 1
    if cantidad == 0:
        return None
    return round(suma / cantidad, 1)


def nota_final(lista, periodos):
    suma = 0
    pesos = 0
    for i in range(len(lista)):
        if lista[i] is not None:
            suma = suma + lista[i] * periodos[i]["porcentaje"]
            pesos = pesos + periodos[i]["porcentaje"]
    if pesos == 0:
        return None
    return round(suma / pesos, 1)


def grupo_del_estudiante(estudiante_id):
    matricula = base_datos.matricula_activa(estudiante_id, g.colegio["anio"])
    if matricula is None:
        return None
    return base_datos.buscar_grupo(matricula["grupo_id"])


def dicta_en_grupo(yo, grupo_id):
    if not tiene_rol(yo, "docente"):
        return False
    for asignacion in base_datos.asignaciones_del_grupo(grupo_id):
        if asignacion["docente_id"] == yo["id"]:
            return True
    return False


def puede_ver_grupo(yo, grupo):
    if yo is None or grupo is None or grupo["colegio_id"] != yo["colegio_id"]:
        return False
    if tiene_alguno(yo, VEN_TODOS_LOS_ESTUDIANTES):
        return True
    return grupo["director_id"] == yo["id"]


def puede_ver_estudiante(yo, estudiante):
    if yo is None or estudiante is None or estudiante["colegio_id"] != yo["colegio_id"]:
        return False
    if tiene_alguno(yo, VEN_TODOS_LOS_ESTUDIANTES):
        return True
    if yo["id"] == estudiante["id"]:
        return True
    if tiene_rol(yo, "acudiente"):
        for hijo in base_datos.estudiantes_a_cargo(yo["id"]):
            if hijo["id"] == estudiante["id"]:
                return True
    grupo = grupo_del_estudiante(estudiante["id"])
    if grupo is not None and grupo["director_id"] == yo["id"]:
        return True
    return False


def puede_anotar_estudiante(yo, estudiante):
    if puede_ver_estudiante(yo, estudiante) and tiene_alguno(yo, ["coordinador", "rector", "orientador", "director"]):
        return True
    if yo is None or estudiante is None or estudiante["colegio_id"] != yo["colegio_id"]:
        return False
    grupo = grupo_del_estudiante(estudiante["id"])
    return grupo is not None and dicta_en_grupo(yo, grupo["id"])


def estudiante_del_colegio(estudiante_id):
    persona = base_datos.buscar_usuario_por_id(estudiante_id)
    if persona is None or persona["colegio_id"] != g.colegio["id"]:
        return None
    if "estudiante" not in base_datos.roles_de(persona["id"]):
        return None
    return persona


def numero(texto, minimo, maximo):
    limpio = texto.strip().replace(",", ".")
    if limpio == "":
        return None
    puntos = 0
    for letra in limpio:
        if letra == ".":
            puntos = puntos + 1
        elif letra not in "0123456789":
            return None
    if puntos > 1 or limpio == ".":
        return None
    valor = float(limpio)
    if valor < minimo or valor > maximo:
        return None
    return valor


def dominio_de(direccion):
    if direccion.startswith("https://"):
        direccion = direccion[8:]
    elif direccion.startswith("http://"):
        direccion = direccion[7:]
    barra = direccion.find("/")
    if barra != -1:
        direccion = direccion[:barra]
    return direccion.lower()


def viene_de_otro_sitio():
    origen = request.headers.get("Origin", "")
    if origen == "":
        origen = request.headers.get("Referer", "")
    if origen == "":
        return False
    return dominio_de(origen) != request.host.lower()


@app.before_request
def cargar_sesion():
    if request.method == "POST" and viene_de_otro_sitio():
        return "Solicitud rechazada: el formulario no viene de esta plataforma.", 403
    g.yo = None
    if "usuario_id" in session:
        g.yo = cargar_usuario(session["usuario_id"])
        if g.yo is None:
            session.clear()
    if g.yo is None:
        g.colegio = base_datos.buscar_colegio(COLEGIO_PILOTO)
    else:
        g.colegio = base_datos.buscar_colegio(g.yo["colegio_id"])
    if g.colegio is None:
        return "Todavía no hay ningún colegio creado. Ejecuta: py crear_colegio.py", 503
    libres = ["/mi-cuenta", "/salir", "/sw.js", "/sin-conexion", "/privacidad"]
    if g.yo is not None and g.yo["debe_cambiar_clave"] == 1:
        if request.path not in libres and not request.path.startswith("/static/"):
            return redirect("/mi-cuenta")
    return None


@app.after_request
def cabeceras_de_seguridad(respuesta):
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "SAMEORIGIN"
    respuesta.headers["Referrer-Policy"] = "same-origin"
    return respuesta


@app.context_processor
def datos_para_plantillas():
    return {
        "yo": g.yo,
        "colegio": g.colegio,
        "menu": menu_de(g.yo),
        "nombres_roles": NOMBRES_ROLES,
        "desempeno": desempeno,
        "aviso_demo": os.environ.get("AVISO_DEMO", ""),
    }


@app.errorhandler(404)
def no_encontrada(error):
    return render_template("no_encontrada.html", activo=""), 404
