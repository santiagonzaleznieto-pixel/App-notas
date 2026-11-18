import secrets
from datetime import date, timedelta
from flask import g, render_template, request, redirect
from werkzeug.security import generate_password_hash
from nucleo import app, agregar_menu, tiene_rol, tiene_alguno, numero, registrar, hoy, estudiante_del_colegio, NOMBRES_ROLES
import base_datos

TOTAL = ["administrador"]
ACADEMICO = ["administrador", "coordinador"]
MATRICULA = ["administrador", "secretaria"]
VEN_ADMINISTRACION = ["administrador", "coordinador", "secretaria"]
VEN_REGISTRO = ["administrador", "rector"]
ROLES_DIRECTIVOS = ["administrador", "rector", "coordinador"]
ROLES_ASIGNABLES = ["administrador", "rector", "coordinador", "docente", "secretaria", "orientador", "tesoreria",
                    "bibliotecario", "enfermeria", "porteria", "estudiante", "acudiente"]
JORNADAS = ["Mañana", "Tarde", "Única", "Nocturna", "Fin de semana"]
PARENTESCOS = ["Madre", "Padre", "Abuela", "Abuelo", "Tía", "Tío", "Hermana", "Hermano", "Otro"]
ESTADOS_USUARIO = ["todos", "activos", "inactivos"]

DIGITOS = "0123456789"
LETRAS_USUARIO = "abcdefghijklmnopqrstuvwxyz0123456789"
LETRAS_DOCUMENTO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
LETRAS_TELEFONO = "0123456789 +-()"
LETRAS_CLAVE = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TILDES = {
    "á": "a", "à": "a", "ä": "a", "â": "a",
    "é": "e", "è": "e", "ë": "e", "ê": "e",
    "í": "i", "ì": "i", "ï": "i", "î": "i",
    "ó": "o", "ò": "o", "ö": "o", "ô": "o",
    "ú": "u", "ù": "u", "ü": "u", "û": "u",
    "ñ": "n", "ç": "c",
}
DIAS_DEL_MES = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MAXIMO_LINEAS = 200
MAXIMO_PERIODOS = 8

ESCALA = [
    {"campo": "nota_minima", "titulo": "Nota mínima"},
    {"campo": "limite_basico", "titulo": "Desde Básico"},
    {"campo": "limite_alto", "titulo": "Desde Alto"},
    {"campo": "limite_superior", "titulo": "Desde Superior"},
    {"campo": "nota_maxima", "titulo": "Nota máxima"},
]

SECCIONES = [
    {"titulo": "Datos del colegio", "ruta": "/admin/colegio", "roles": TOTAL,
     "descripcion": "Nombre, código DANE, lema y escala de valoración."},
    {"titulo": "Sedes", "ruta": "/admin/sedes", "roles": TOTAL,
     "descripcion": "Sedes del colegio y la jornada de cada una."},
    {"titulo": "Períodos", "ruta": "/admin/periodos", "roles": ACADEMICO,
     "descripcion": "Fechas, porcentajes y qué períodos están abiertos para calificar."},
    {"titulo": "Materias", "ruta": "/admin/materias", "roles": ACADEMICO,
     "descripcion": "Materias del plan de estudios con su nombre corto y su área."},
    {"titulo": "Grupos", "ruta": "/admin/grupos", "roles": VEN_ADMINISTRACION,
     "descripcion": "Directores, docentes por materia y estudiantes matriculados."},
    {"titulo": "Usuarios", "ruta": "/admin/usuarios", "roles": MATRICULA,
     "descripcion": "Buscar personas, cambiar sus datos, roles y contraseñas."},
    {"titulo": "Nuevo usuario", "ruta": "/admin/usuarios/nuevo", "roles": MATRICULA,
     "descripcion": "Crear una persona con su usuario y su clave temporal."},
    {"titulo": "Cargue masivo", "ruta": "/admin/cargue", "roles": MATRICULA,
     "descripcion": "Crear y matricular muchos estudiantes pegando una lista."},
    {"titulo": "Registro de actividad", "ruta": "/admin/registro", "roles": VEN_REGISTRO,
     "descripcion": "Quién hizo qué y cuándo en la plataforma."},
]

agregar_menu("admin", "Administración", "/admin", ["administrador", "coordinador", "secretaria"],
             "Usuarios, grupos, matrículas, materias, períodos y datos del colegio.")


def solo_digitos(texto):
    if texto == "":
        return False
    for letra in texto:
        if letra not in DIGITOS:
            return False
    return True


def entero(texto):
    limpio = texto.strip()
    if len(limpio) > 9 or not solo_digitos(limpio):
        return None
    return int(limpio)


def buscar_por_id(lista, texto_id):
    buscado = entero(texto_id)
    for elemento in lista:
        if elemento["id"] == buscado:
            return elemento
    return None


def texto_numero(valor):
    if valor == int(valor):
        return str(int(valor))
    return str(valor)


def cantidad(total, singular, plural):
    if total == 1:
        return "1 " + singular
    return str(total) + " " + plural


def limpiar_espacios(texto):
    return " ".join(texto.split())


def quitar_tildes(texto):
    resultado = ""
    for letra in texto.lower():
        if letra in TILDES:
            resultado = resultado + TILDES[letra]
        else:
            resultado = resultado + letra
    return resultado


def solo_letras(texto):
    resultado = ""
    for letra in quitar_tildes(texto):
        if letra in LETRAS_USUARIO:
            resultado = resultado + letra
    return resultado


def clave_grupo(texto):
    return quitar_tildes(texto).replace(" ", "")


def palabras_del_nombre(nombre):
    palabras = []
    for palabra in nombre.split():
        limpia = solo_letras(palabra)
        if limpia != "":
            palabras.append(limpia)
    return palabras


def generar_usuario(nombre):
    palabras = palabras_del_nombre(nombre)
    if len(palabras) >= 4:
        base = palabras[0] + "." + palabras[2]
    elif len(palabras) >= 2:
        base = palabras[0] + "." + palabras[len(palabras) - 1]
    elif len(palabras) == 1:
        base = palabras[0]
    else:
        base = "usuario"
    usuario = base
    contador = 2
    while base_datos.buscar_usuario(usuario) is not None:
        usuario = base + str(contador)
        contador = contador + 1
    return usuario


def clave_temporal():
    clave = ""
    for i in range(8):
        clave = clave + secrets.choice(LETRAS_CLAVE)
    return clave


def fecha_valida(texto):
    if len(texto) != 10 or texto[4] != "-" or texto[7] != "-":
        return False
    if not solo_digitos(texto[0:4]) or not solo_digitos(texto[5:7]) or not solo_digitos(texto[8:10]):
        return False
    anio = int(texto[0:4])
    mes = int(texto[5:7])
    dia = int(texto[8:10])
    if anio < 2000 or anio > 2100 or mes < 1 or mes > 12:
        return False
    maximo = DIAS_DEL_MES[mes - 1]
    bisiesto = anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)
    if mes == 2 and not bisiesto:
        maximo = 28
    return dia >= 1 and dia <= maximo


def limpiar_documento(texto):
    resultado = ""
    for letra in texto.strip().upper():
        if letra != "." and letra != " " and letra != ",":
            resultado = resultado + letra
    return resultado


def documento_valido(documento):
    if len(documento) < 4 or len(documento) > 20:
        return False
    for letra in documento:
        if letra not in LETRAS_DOCUMENTO:
            return False
    return True


def correo_valido(correo):
    if correo == "":
        return True
    return "@" in correo and "." in correo and " " not in correo and len(correo) <= 120


def telefono_valido(telefono):
    if len(telefono) > 20:
        return False
    for letra in telefono:
        if letra not in LETRAS_TELEFONO:
            return False
    return True


def contar_por(sql, valores):
    conteo = {}
    for fila in base_datos.consultar(sql, valores):
        conteo[fila["clave"]] = fila["total"]
    return conteo


def suma_porcentajes(periodos):
    suma = 0
    for periodo in periodos:
        suma = suma + periodo["porcentaje"]
    return round(suma, 2)


def usuario_del_colegio(usuario_id):
    persona = base_datos.buscar_usuario_por_id(usuario_id)
    if persona is None or persona["colegio_id"] != g.colegio["id"]:
        return None
    persona["roles"] = base_datos.roles_de(persona["id"])
    return persona


def puede_gestionar(persona):
    if tiene_rol(g.yo, "administrador"):
        return True
    for rol in ROLES_DIRECTIVOS:
        if rol in persona["roles"]:
            return False
    return True


def administradores_activos_sin(usuario_id):
    total = 0
    for persona in base_datos.usuarios_con_rol(g.colegio["id"], "administrador"):
        if persona["id"] != usuario_id:
            total = total + 1
    return total


def documento_repetido(documento, sin_contar):
    otro = base_datos.consultar_uno(
        "SELECT id FROM usuarios WHERE colegio_id = ? AND documento = ? AND id != ?",
        [g.colegio["id"], documento, sin_contar],
    )
    return otro is not None


def documentos_del_colegio():
    documentos = []
    for fila in base_datos.consultar("SELECT documento FROM usuarios WHERE colegio_id = ? AND documento != ''", [g.colegio["id"]]):
        documentos.append(fila["documento"])
    return documentos


def estudiantes_sin_matricula():
    return base_datos.consultar(
        "SELECT usuarios.* FROM usuarios JOIN roles_usuario ON roles_usuario.usuario_id = usuarios.id "
        "WHERE usuarios.colegio_id = ? AND roles_usuario.rol = 'estudiante' AND usuarios.activo = 1 "
        "AND usuarios.id NOT IN (SELECT estudiante_id FROM matriculas WHERE colegio_id = ? AND anio = ? AND estado = 'activa') "
        "ORDER BY usuarios.nombre",
        [g.colegio["id"], g.colegio["id"], g.colegio["anio"]],
    )


def matricular(estudiante_id, grupo_id):
    base_datos.ejecutar(
        "INSERT INTO matriculas (colegio_id, anio, estudiante_id, grupo_id, estado, fecha_matricula) VALUES (?, ?, ?, ?, 'activa', ?)",
        [g.colegio["id"], g.colegio["anio"], estudiante_id, grupo_id, hoy()],
    )


def crear_usuario(datos, roles):
    usuario = generar_usuario(datos["nombre"])
    clave = clave_temporal()
    nuevo_id = base_datos.ejecutar(
        "INSERT INTO usuarios (colegio_id, usuario, clave, nombre, documento, correo, telefono, activo, debe_cambiar_clave) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)",
        [g.colegio["id"], usuario, generate_password_hash(clave), datos["nombre"], datos["documento"],
         datos["correo"], datos["telefono"]],
    )
    for rol in roles:
        base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [nuevo_id, rol])
    return {"id": nuevo_id, "usuario": usuario, "clave": clave, "nombre": datos["nombre"],
            "documento": datos["documento"], "grupo": ""}


def datos_del_formulario():
    return {
        "nombre": limpiar_espacios(request.form.get("nombre", "")),
        "documento": limpiar_documento(request.form.get("documento", "")),
        "correo": request.form.get("correo", "").strip().lower(),
        "telefono": request.form.get("telefono", "").strip(),
    }


def roles_del_formulario():
    marcados = request.form.getlist("roles")
    roles = []
    for rol in ROLES_ASIGNABLES:
        if rol in marcados:
            roles.append(rol)
    return roles


def opciones_de_roles():
    opciones = []
    for rol in ROLES_ASIGNABLES:
        permitido = True
        if rol in ROLES_DIRECTIVOS and not tiene_rol(g.yo, "administrador"):
            permitido = False
        opciones.append({"rol": rol, "nombre": NOMBRES_ROLES[rol], "permitido": permitido})
    return opciones


def errores_de_persona(datos, roles, persona_id):
    errores = []
    if len(palabras_del_nombre(datos["nombre"])) < 2:
        errores.append("Escribe el nombre completo: al menos un nombre y un apellido.")
    elif len(datos["nombre"]) > 100:
        errores.append("El nombre es demasiado largo (máximo 100 letras).")
    if datos["documento"] == "":
        errores.append("Escribe el número de documento.")
    elif not documento_valido(datos["documento"]):
        errores.append("El documento solo puede tener letras y números, entre 4 y 20.")
    elif documento_repetido(datos["documento"], persona_id):
        errores.append("Ya hay otra persona del colegio con el documento " + datos["documento"] + ".")
    if not correo_valido(datos["correo"]):
        errores.append("El correo no parece válido.")
    if not telefono_valido(datos["telefono"]):
        errores.append("El teléfono solo puede tener números, espacios, +, - y paréntesis.")
    if len(roles) == 0:
        errores.append("Marca al menos un rol.")
    if not tiene_rol(g.yo, "administrador"):
        for rol in roles:
            if rol in ROLES_DIRECTIVOS:
                errores.append("Solo la administración puede dar el rol " + NOMBRES_ROLES[rol] + ".")
    return errores


def errores_de_roles(persona, roles):
    errores = []
    anteriores = persona["roles"]
    anio = g.colegio["anio"]
    if "administrador" in anteriores and "administrador" not in roles:
        if persona["id"] == g.yo["id"]:
            errores.append("No puedes quitarte a ti mismo el rol de administración.")
        elif persona["activo"] == 1 and administradores_activos_sin(persona["id"]) == 0:
            errores.append("El colegio debe tener al menos un administrador activo.")
    if "estudiante" in anteriores and "estudiante" not in roles:
        if base_datos.matricula_activa(persona["id"], anio) is not None:
            errores.append("Tiene matrícula activa: retíralo del grupo antes de quitarle el rol de estudiante.")
    if "acudiente" in anteriores and "acudiente" not in roles:
        if len(base_datos.estudiantes_a_cargo(persona["id"])) > 0:
            errores.append("Tiene estudiantes a cargo: quítalos antes de quitarle el rol de acudiente.")
    if "docente" in anteriores and "docente" not in roles:
        clases = base_datos.asignaciones_del_docente(persona["id"], anio)
        dirigidos = base_datos.grupos_dirigidos(persona["id"], anio)
        if len(clases) > 0 or len(dirigidos) > 0:
            errores.append("Tiene materias o un grupo a cargo este año: cámbialos en Grupos antes de quitarle el rol de docente.")
    return errores


def errores_nombre_grupo(nombre, grupos, grupo_id):
    if nombre == "" or len(nombre) > 20:
        return ["Escribe el nombre del grupo, por ejemplo 6-A (máximo 20 letras)."]
    for otro in grupos:
        if otro["id"] != grupo_id and clave_grupo(otro["nombre"]) == clave_grupo(nombre):
            return ["Ya existe el grupo " + otro["nombre"] + " en " + str(g.colegio["anio"]) + "."]
    return []


@app.route("/admin")
def admin_tablero():
    if not tiene_alguno(g.yo, VEN_ADMINISTRACION):
        return redirect("/inicio")
    colegio_id = g.colegio["id"]
    anio = g.colegio["anio"]
    grupos = base_datos.grupos_del_colegio(colegio_id, anio)
    matriculados = base_datos.consultar_uno(
        "SELECT COUNT(*) AS total FROM matriculas WHERE colegio_id = ? AND anio = ? AND estado = 'activa'",
        [colegio_id, anio],
    )
    inactivos = base_datos.consultar_uno("SELECT COUNT(*) AS total FROM usuarios WHERE colegio_id = ? AND activo = 0", [colegio_id])
    cifras = {
        "matriculados": matriculados["total"],
        "docentes": len(base_datos.usuarios_con_rol(colegio_id, "docente")),
        "grupos": len(grupos),
        "inactivos": inactivos["total"],
    }

    secciones = []
    for seccion in SECCIONES:
        if tiene_alguno(g.yo, seccion["roles"]):
            secciones.append(seccion)

    pendientes = []
    if tiene_alguno(g.yo, ACADEMICO):
        suma = suma_porcentajes(base_datos.periodos_del_anio(colegio_id, anio))
        if suma != 100:
            pendientes.append({"texto": "Los porcentajes de los períodos suman " + texto_numero(suma) + " % y deben sumar 100 %.",
                               "ruta": "/admin/periodos"})
        sin_director = 0
        for grupo in grupos:
            if grupo["director_id"] is None:
                sin_director = sin_director + 1
        if sin_director > 0:
            pendientes.append({"texto": cantidad(sin_director, "grupo", "grupos") + " sin director de grupo.", "ruta": "/admin/grupos"})
    if tiene_alguno(g.yo, MATRICULA):
        sin_matricula = len(estudiantes_sin_matricula())
        if sin_matricula > 0:
            pendientes.append({"texto": cantidad(sin_matricula, "estudiante activo", "estudiantes activos") + " sin matrícula en "
                               + str(anio) + ". Se matriculan desde la página de cada grupo.", "ruta": "/admin/grupos"})

    return render_template("admin_tablero.html", activo="admin", cifras=cifras, secciones=secciones, pendientes=pendientes)


@app.route("/admin/colegio", methods=["GET", "POST"])
def admin_colegio():
    if not tiene_alguno(g.yo, TOTAL):
        return redirect("/inicio")

    errores = []
    mensaje = ""
    valores = g.colegio
    if request.method == "POST":
        valores = {}
        for campo in ["nombre", "nombre_corto", "municipio", "departamento", "codigo_dane", "lema"]:
            valores[campo] = limpiar_espacios(request.form.get(campo, ""))
        for parte in ESCALA:
            valores[parte["campo"]] = request.form.get(parte["campo"], "").strip()

        if valores["nombre"] == "" or valores["nombre_corto"] == "" or valores["municipio"] == "" or valores["departamento"] == "":
            errores.append("El nombre, el nombre corto, el municipio y el departamento son obligatorios.")
        if len(valores["nombre"]) > 150 or len(valores["nombre_corto"]) > 60 or len(valores["lema"]) > 200:
            errores.append("Algún texto es demasiado largo: nombre hasta 150 letras, nombre corto hasta 60 y lema hasta 200.")
        if len(valores["municipio"]) > 80 or len(valores["departamento"]) > 80:
            errores.append("El municipio y el departamento pueden tener hasta 80 letras.")
        if valores["codigo_dane"] != "" and (len(valores["codigo_dane"]) != 12 or not solo_digitos(valores["codigo_dane"])):
            errores.append("El código DANE debe tener 12 dígitos.")

        escala = {}
        completa = True
        for parte in ESCALA:
            escala[parte["campo"]] = numero(valores[parte["campo"]], 0, 100)
            if escala[parte["campo"]] is None:
                errores.append(parte["titulo"] + ": escribe un número entre 0 y 100.")
                completa = False
        if completa:
            if not (escala["nota_minima"] < escala["limite_basico"] and escala["limite_basico"] < escala["limite_alto"]
                    and escala["limite_alto"] < escala["limite_superior"] and escala["limite_superior"] <= escala["nota_maxima"]):
                errores.append("La escala debe cumplir: nota mínima < Básico < Alto < Superior ≤ nota máxima.")

        if len(errores) == 0:
            base_datos.ejecutar(
                "UPDATE colegios SET nombre = ?, nombre_corto = ?, municipio = ?, departamento = ?, codigo_dane = ?, lema = ?, "
                "nota_minima = ?, nota_maxima = ?, limite_basico = ?, limite_alto = ?, limite_superior = ? WHERE id = ?",
                [valores["nombre"], valores["nombre_corto"], valores["municipio"], valores["departamento"],
                 valores["codigo_dane"], valores["lema"], escala["nota_minima"], escala["nota_maxima"],
                 escala["limite_basico"], escala["limite_alto"], escala["limite_superior"], g.colegio["id"]],
            )
            registrar("Editó los datos del colegio", valores["nombre_corto"] + ", escala de " + texto_numero(escala["nota_minima"])
                      + " a " + texto_numero(escala["nota_maxima"]))
            g.colegio = base_datos.buscar_colegio(g.colegio["id"])
            valores = g.colegio
            mensaje = "Datos del colegio guardados."

    return render_template("admin_colegio.html", activo="admin", valores=valores, escala=ESCALA, errores=errores, mensaje=mensaje)


@app.route("/admin/sedes", methods=["GET", "POST"])
def admin_sedes():
    if not tiene_alguno(g.yo, TOTAL):
        return redirect("/inicio")

    colegio_id = g.colegio["id"]
    errores = []
    mensaje = ""
    nueva = {"nombre": "", "jornada": JORNADAS[0]}
    if request.method == "POST":
        accion = request.form.get("accion", "")
        sedes = base_datos.sedes_del_colegio(colegio_id)
        nombre = limpiar_espacios(request.form.get("nombre", ""))
        jornada = request.form.get("jornada", "")
        sede = None
        if accion == "crear":
            nueva = {"nombre": nombre, "jornada": jornada}
        elif accion == "editar":
            sede = buscar_por_id(sedes, request.form.get("sede_id", ""))
            if sede is None:
                errores.append("Esa sede no existe en el colegio.")
        else:
            errores.append("Acción no válida.")
        if nombre == "" or len(nombre) > 80:
            errores.append("Escribe el nombre de la sede (máximo 80 letras).")
        if jornada not in JORNADAS:
            errores.append("Elige una jornada de la lista.")
        if len(errores) == 0:
            for otra in sedes:
                if quitar_tildes(otra["nombre"]) == quitar_tildes(nombre) and otra["jornada"] == jornada:
                    if sede is None or otra["id"] != sede["id"]:
                        errores.append("Ya existe la sede " + nombre + " en jornada " + jornada + ".")
        if len(errores) == 0 and accion == "crear":
            base_datos.ejecutar("INSERT INTO sedes (colegio_id, nombre, jornada) VALUES (?, ?, ?)", [colegio_id, nombre, jornada])
            registrar("Creó una sede", nombre + " (" + jornada + ")")
            mensaje = "Sede " + nombre + " creada."
            nueva = {"nombre": "", "jornada": JORNADAS[0]}
        elif len(errores) == 0 and accion == "editar":
            base_datos.ejecutar("UPDATE sedes SET nombre = ?, jornada = ? WHERE id = ? AND colegio_id = ?",
                                [nombre, jornada, sede["id"], colegio_id])
            registrar("Editó una sede", sede["nombre"] + " → " + nombre + " (" + jornada + ")")
            mensaje = "Sede " + nombre + " guardada."

    sedes = base_datos.sedes_del_colegio(colegio_id)
    grupos_por_sede = contar_por(
        "SELECT sede_id AS clave, COUNT(*) AS total FROM grupos WHERE colegio_id = ? AND anio = ? GROUP BY sede_id",
        [colegio_id, g.colegio["anio"]],
    )
    for sede in sedes:
        sede["grupos"] = grupos_por_sede.get(sede["id"], 0)

    return render_template("admin_sedes.html", activo="admin", sedes=sedes, jornadas=JORNADAS, nueva=nueva,
                           errores=errores, mensaje=mensaje)


def filas_de_periodos(periodos):
    filas = []
    for periodo in periodos:
        filas.append({
            "id": periodo["id"],
            "numero": periodo["numero"],
            "nombre": periodo["nombre"],
            "fecha_inicio": periodo["fecha_inicio"],
            "fecha_fin": periodo["fecha_fin"],
            "porcentaje": texto_numero(periodo["porcentaje"]),
            "abierto": periodo["abierto"] == 1,
        })
    return filas


def errores_de_periodos(filas):
    errores = []
    suma = 0
    fin_anterior = ""
    for fila in filas:
        titulo = "Período " + str(fila["numero"])
        porcentaje = numero(fila["porcentaje"], 0, 100)
        if fila["nombre"] == "" or len(fila["nombre"]) > 60:
            errores.append(titulo + ": escribe el nombre (máximo 60 letras).")
        if not fecha_valida(fila["fecha_inicio"]) or not fecha_valida(fila["fecha_fin"]):
            errores.append(titulo + ": escribe fechas válidas (año-mes-día).")
        elif fila["fecha_inicio"] > fila["fecha_fin"]:
            errores.append(titulo + ": la fecha de inicio no puede ser después de la fecha final.")
        elif fin_anterior != "" and fila["fecha_inicio"] <= fin_anterior:
            errores.append(titulo + ": debe empezar después de que termine el período anterior.")
        if fecha_valida(fila["fecha_fin"]):
            fin_anterior = fila["fecha_fin"]
        if porcentaje is None or porcentaje == 0:
            errores.append(titulo + ": el porcentaje debe ser un número mayor que 0 y hasta 100.")
        else:
            suma = suma + porcentaje
    if len(errores) == 0 and round(suma, 2) != 100:
        errores.append("Los porcentajes suman " + texto_numero(round(suma, 2)) + " %; deben sumar 100 %.")
    return errores


@app.route("/admin/periodos", methods=["GET", "POST"])
def admin_periodos():
    if not tiene_alguno(g.yo, ACADEMICO):
        return redirect("/inicio")

    colegio_id = g.colegio["id"]
    anio = g.colegio["anio"]
    periodos = base_datos.periodos_del_anio(colegio_id, anio)
    filas = filas_de_periodos(periodos)
    errores = []
    mensaje = ""
    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "guardar":
            filas = []
            for periodo in periodos:
                clave = str(periodo["id"])
                filas.append({
                    "id": periodo["id"],
                    "numero": periodo["numero"],
                    "nombre": limpiar_espacios(request.form.get("nombre-" + clave, "")),
                    "fecha_inicio": request.form.get("inicio-" + clave, "").strip(),
                    "fecha_fin": request.form.get("fin-" + clave, "").strip(),
                    "porcentaje": request.form.get("porcentaje-" + clave, "").strip(),
                    "abierto": ("abierto-" + clave) in request.form,
                })
            errores = errores_de_periodos(filas)
            if len(errores) == 0:
                abiertos = []
                for fila in filas:
                    abierto = 0
                    if fila["abierto"]:
                        abierto = 1
                        abiertos.append(str(fila["numero"]))
                    base_datos.ejecutar(
                        "UPDATE periodos SET nombre = ?, fecha_inicio = ?, fecha_fin = ?, porcentaje = ?, abierto = ? "
                        "WHERE id = ? AND colegio_id = ?",
                        [fila["nombre"], fila["fecha_inicio"], fila["fecha_fin"], numero(fila["porcentaje"], 0, 100),
                         abierto, fila["id"], colegio_id],
                    )
                if len(abiertos) == 0:
                    abiertos.append("ninguno")
                registrar("Guardó los períodos", str(anio) + ", abiertos: " + ", ".join(abiertos))
                mensaje = "Períodos guardados."
        elif accion == "agregar":
            if len(periodos) >= MAXIMO_PERIODOS:
                errores.append("El año puede tener hasta " + str(MAXIMO_PERIODOS) + " períodos.")
            else:
                nuevo_numero = 1
                inicio = hoy()
                if len(periodos) > 0:
                    ultimo = periodos[len(periodos) - 1]
                    nuevo_numero = ultimo["numero"] + 1
                    if fecha_valida(ultimo["fecha_fin"]):
                        inicio = (date.fromisoformat(ultimo["fecha_fin"]) + timedelta(days=1)).isoformat()
                nombre = "Período " + str(nuevo_numero)
                base_datos.ejecutar(
                    "INSERT INTO periodos (colegio_id, anio, numero, nombre, fecha_inicio, fecha_fin, porcentaje, abierto) "
                    "VALUES (?, ?, ?, ?, ?, ?, 0, 0)",
                    [colegio_id, anio, nuevo_numero, nombre, inicio, inicio],
                )
                registrar("Agregó un período", nombre + " de " + str(anio))
                mensaje = "Se agregó el " + nombre.lower() + " con 0 %. Ajusta sus fechas y los porcentajes para que sumen 100 %."
        elif accion == "quitar":
            if len(periodos) <= 1:
                errores.append("El año debe tener al menos un período.")
            else:
                ultimo = periodos[len(periodos) - 1]
                nota = base_datos.consultar_uno(
                    "SELECT id FROM notas WHERE colegio_id = ? AND anio = ? AND periodo = ? AND valor IS NOT NULL LIMIT 1",
                    [colegio_id, anio, ultimo["numero"]],
                )
                if nota is not None:
                    errores.append("No se puede quitar el " + ultimo["nombre"].lower() + ": ya tiene notas registradas.")
                else:
                    base_datos.ejecutar("DELETE FROM notas WHERE colegio_id = ? AND anio = ? AND periodo = ? AND valor IS NULL",
                                        [colegio_id, anio, ultimo["numero"]])
                    base_datos.ejecutar("DELETE FROM periodos WHERE id = ? AND colegio_id = ?", [ultimo["id"], colegio_id])
                    registrar("Quitó un período", ultimo["nombre"] + " de " + str(anio))
                    mensaje = "Se quitó el " + ultimo["nombre"].lower() + ". Revisa que los porcentajes sumen 100 %."
        else:
            errores.append("Acción no válida.")
        periodos = base_datos.periodos_del_anio(colegio_id, anio)
        if len(errores) == 0 or accion != "guardar":
            filas = filas_de_periodos(periodos)

    return render_template("admin_periodos.html", activo="admin", filas=filas, errores=errores, mensaje=mensaje,
                           suma=texto_numero(suma_porcentajes(periodos)))


@app.route("/admin/materias", methods=["GET", "POST"])
def admin_materias():
    if not tiene_alguno(g.yo, ACADEMICO):
        return redirect("/inicio")

    colegio_id = g.colegio["id"]
    errores = []
    mensaje = ""
    nueva = {"nombre": "", "corto": "", "area": ""}
    if request.method == "POST":
        accion = request.form.get("accion", "")
        materias = base_datos.materias_del_colegio(colegio_id)
        datos = {
            "nombre": limpiar_espacios(request.form.get("nombre", "")),
            "corto": limpiar_espacios(request.form.get("corto", "")),
            "area": limpiar_espacios(request.form.get("area", "")),
        }
        materia = None
        if accion == "crear":
            nueva = datos
        elif accion == "editar":
            materia = buscar_por_id(materias, request.form.get("materia_id", ""))
            if materia is None:
                errores.append("Esa materia no existe en el colegio.")
        else:
            errores.append("Acción no válida.")
        if datos["nombre"] == "" or len(datos["nombre"]) > 80:
            errores.append("Escribe el nombre de la materia (máximo 80 letras).")
        if datos["corto"] == "" or len(datos["corto"]) > 8:
            errores.append("Escribe el nombre corto (máximo 8 letras); se usa en las tablas de notas.")
        if len(datos["area"]) > 60:
            errores.append("El área puede tener hasta 60 letras.")
        if len(errores) == 0:
            for otra in materias:
                if quitar_tildes(otra["nombre"]) == quitar_tildes(datos["nombre"]):
                    if materia is None or otra["id"] != materia["id"]:
                        errores.append("Ya existe la materia " + otra["nombre"] + ".")
        if len(errores) == 0 and accion == "crear":
            base_datos.ejecutar("INSERT INTO materias (colegio_id, nombre, corto, area) VALUES (?, ?, ?, ?)",
                                [colegio_id, datos["nombre"], datos["corto"], datos["area"]])
            registrar("Creó una materia", datos["nombre"])
            mensaje = "Materia " + datos["nombre"] + " creada. Asígnala a los grupos desde Grupos."
            nueva = {"nombre": "", "corto": "", "area": ""}
        elif len(errores) == 0 and accion == "editar":
            base_datos.ejecutar("UPDATE materias SET nombre = ?, corto = ?, area = ? WHERE id = ? AND colegio_id = ?",
                                [datos["nombre"], datos["corto"], datos["area"], materia["id"], colegio_id])
            registrar("Editó una materia", materia["nombre"] + " → " + datos["nombre"])
            mensaje = "Materia " + datos["nombre"] + " guardada."

    materias = base_datos.materias_del_colegio(colegio_id)
    grupos_por_materia = contar_por(
        "SELECT asignaciones.materia_id AS clave, COUNT(*) AS total FROM asignaciones JOIN grupos ON grupos.id = asignaciones.grupo_id "
        "WHERE asignaciones.colegio_id = ? AND grupos.anio = ? GROUP BY asignaciones.materia_id",
        [colegio_id, g.colegio["anio"]],
    )
    for materia in materias:
        materia["grupos"] = grupos_por_materia.get(materia["id"], 0)

    return render_template("admin_materias.html", activo="admin", materias=materias, nueva=nueva, errores=errores, mensaje=mensaje)


@app.route("/admin/grupos", methods=["GET", "POST"])
def admin_grupos():
    if not tiene_alguno(g.yo, VEN_ADMINISTRACION):
        return redirect("/inicio")

    colegio_id = g.colegio["id"]
    anio = g.colegio["anio"]
    academico = tiene_alguno(g.yo, ACADEMICO)
    grados = base_datos.grados_del_colegio(colegio_id)
    sedes = base_datos.sedes_del_colegio(colegio_id)
    docentes = base_datos.usuarios_con_rol(colegio_id, "docente")
    errores = []
    mensaje = ""
    nuevo = {"grado_id": "", "sede_id": "", "nombre": "", "director_id": ""}
    if request.method == "POST":
        if not academico:
            return redirect("/inicio")
        nuevo = {
            "grado_id": request.form.get("grado_id", ""),
            "sede_id": request.form.get("sede_id", ""),
            "nombre": limpiar_espacios(request.form.get("nombre", "")),
            "director_id": request.form.get("director_id", ""),
        }
        grado = buscar_por_id(grados, nuevo["grado_id"])
        sede = buscar_por_id(sedes, nuevo["sede_id"])
        director = None
        if grado is None:
            errores.append("Elige un grado de la lista.")
        if sede is None:
            errores.append("Elige una sede del colegio.")
        errores = errores + errores_nombre_grupo(nuevo["nombre"], base_datos.grupos_del_colegio(colegio_id, anio), 0)
        if nuevo["director_id"] != "":
            director = buscar_por_id(docentes, nuevo["director_id"])
            if director is None:
                errores.append("El director de grupo debe ser un docente activo del colegio.")
        if len(errores) == 0:
            director_id = None
            if director is not None:
                director_id = director["id"]
            base_datos.ejecutar(
                "INSERT INTO grupos (colegio_id, anio, grado_id, sede_id, nombre, director_id) VALUES (?, ?, ?, ?, ?, ?)",
                [colegio_id, anio, grado["id"], sede["id"], nuevo["nombre"], director_id],
            )
            registrar("Creó un grupo", nuevo["nombre"] + " (" + grado["nombre"] + ", " + str(anio) + ")")
            mensaje = "Grupo " + nuevo["nombre"] + " creado. Ábrelo para asignar materias y matricular estudiantes."
            nuevo = {"grado_id": "", "sede_id": "", "nombre": "", "director_id": ""}

    grupos = base_datos.grupos_del_colegio(colegio_id, anio)
    estudiantes_por_grupo = contar_por(
        "SELECT grupo_id AS clave, COUNT(*) AS total FROM matriculas WHERE colegio_id = ? AND anio = ? AND estado = 'activa' "
        "GROUP BY grupo_id",
        [colegio_id, anio],
    )
    materias_por_grupo = contar_por(
        "SELECT asignaciones.grupo_id AS clave, COUNT(*) AS total FROM asignaciones JOIN grupos ON grupos.id = asignaciones.grupo_id "
        "WHERE asignaciones.colegio_id = ? AND grupos.anio = ? GROUP BY asignaciones.grupo_id",
        [colegio_id, anio],
    )
    for grupo in grupos:
        grupo["estudiantes"] = estudiantes_por_grupo.get(grupo["id"], 0)
        grupo["materias"] = materias_por_grupo.get(grupo["id"], 0)

    return render_template("admin_grupos.html", activo="admin", grupos=grupos, grados=grados, sedes=sedes, docentes=docentes,
                           nuevo=nuevo, academico=academico, errores=errores, mensaje=mensaje)


def materia_con_notas(grupo_id, materia_id):
    nota = base_datos.consultar_uno(
        "SELECT notas.id FROM notas JOIN matriculas ON matriculas.estudiante_id = notas.estudiante_id AND matriculas.anio = notas.anio "
        "WHERE matriculas.grupo_id = ? AND matriculas.estado = 'activa' AND notas.materia_id = ? AND notas.valor IS NOT NULL LIMIT 1",
        [grupo_id, materia_id],
    )
    return nota is not None


def asignaciones_por_materia(grupo_id):
    actuales = {}
    for asignacion in base_datos.asignaciones_del_grupo(grupo_id):
        actuales[asignacion["materia_id"]] = asignacion
    return actuales


def filas_de_asignaciones(grupo_id, materias, docentes):
    actuales = asignaciones_por_materia(grupo_id)
    activos = []
    for docente in docentes:
        activos.append(docente["id"])
    filas = []
    for materia in materias:
        fila = {"materia": materia, "docente_id": None, "docente": "", "horas": "", "inactivo": False}
        if materia["id"] in actuales:
            asignacion = actuales[materia["id"]]
            fila["docente_id"] = asignacion["docente_id"]
            fila["docente"] = asignacion["docente"]
            fila["horas"] = asignacion["horas_semana"]
            if asignacion["docente_id"] not in activos:
                fila["inactivo"] = True
        filas.append(fila)
    return filas


def guardar_asignaciones(grupo, materias, docentes):
    resultado = {"cambios": 0, "errores": [], "avisos": []}
    colegio_id = g.colegio["id"]
    actuales = asignaciones_por_materia(grupo["id"])
    for materia in materias:
        clave = str(materia["id"])
        if ("docente-" + clave) in request.form:
            texto_docente = request.form.get("docente-" + clave, "").strip()
            texto_horas = request.form.get("horas-" + clave, "").strip()
            actual = None
            if materia["id"] in actuales:
                actual = actuales[materia["id"]]
            if texto_docente == "":
                if actual is not None and materia_con_notas(grupo["id"], materia["id"]):
                    resultado["avisos"].append(materia["nombre"] + " ya tiene notas en este grupo: no se quitó su asignación.")
                elif actual is not None:
                    base_datos.ejecutar("DELETE FROM asignaciones WHERE id = ? AND colegio_id = ?", [actual["id"], colegio_id])
                    resultado["cambios"] = resultado["cambios"] + 1
            else:
                docente = buscar_por_id(docentes, texto_docente)
                horas = numero(texto_horas, 1, 40)
                docente_id = None
                if docente is not None:
                    docente_id = docente["id"]
                elif actual is not None and entero(texto_docente) == actual["docente_id"]:
                    docente_id = actual["docente_id"]
                if docente_id is None:
                    resultado["errores"].append(materia["nombre"] + ": elige un docente activo del colegio.")
                elif horas is None or horas != int(horas):
                    resultado["errores"].append(materia["nombre"] + ": las horas por semana deben ser un número entero de 1 a 40.")
                elif actual is None:
                    base_datos.ejecutar(
                        "INSERT INTO asignaciones (colegio_id, grupo_id, materia_id, docente_id, horas_semana) VALUES (?, ?, ?, ?, ?)",
                        [colegio_id, grupo["id"], materia["id"], docente_id, int(horas)],
                    )
                    resultado["cambios"] = resultado["cambios"] + 1
                elif actual["docente_id"] != docente_id or actual["horas_semana"] != int(horas):
                    base_datos.ejecutar(
                        "UPDATE asignaciones SET docente_id = ?, horas_semana = ? WHERE id = ? AND colegio_id = ?",
                        [docente_id, int(horas), actual["id"], colegio_id],
                    )
                    resultado["cambios"] = resultado["cambios"] + 1
    return resultado


def matricula_del_grupo(grupo_id):
    return base_datos.consultar_uno(
        "SELECT matriculas.*, usuarios.nombre AS nombre, usuarios.usuario AS usuario FROM matriculas "
        "JOIN usuarios ON usuarios.id = matriculas.estudiante_id "
        "WHERE matriculas.id = ? AND matriculas.grupo_id = ? AND matriculas.colegio_id = ? AND matriculas.estado = 'activa'",
        [entero(request.form.get("matricula_id", "")), grupo_id, g.colegio["id"]],
    )


@app.route("/admin/grupos/<int:grupo_id>", methods=["GET", "POST"])
def admin_grupo(grupo_id):
    academico = tiene_alguno(g.yo, ACADEMICO)
    puede_matricular = tiene_alguno(g.yo, MATRICULA)
    if not academico and not puede_matricular:
        return redirect("/inicio")
    colegio_id = g.colegio["id"]
    anio = g.colegio["anio"]
    grupo = base_datos.buscar_grupo(grupo_id)
    if grupo is None or grupo["colegio_id"] != colegio_id or grupo["anio"] != anio:
        return redirect("/admin/grupos")

    sedes = base_datos.sedes_del_colegio(colegio_id)
    docentes = base_datos.usuarios_con_rol(colegio_id, "docente")
    materias = base_datos.materias_del_colegio(colegio_id)
    grupos_del_anio = base_datos.grupos_del_colegio(colegio_id, anio)
    otros_grupos = []
    for otro in grupos_del_anio:
        if otro["id"] != grupo_id:
            otros_grupos.append(otro)

    errores = []
    avisos = []
    mensaje = ""
    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion in ["datos", "asignaciones"] and not academico:
            return redirect("/inicio")
        if accion in ["retirar", "trasladar", "matricular"] and not puede_matricular:
            return redirect("/inicio")

        if accion == "datos":
            nombre = limpiar_espacios(request.form.get("nombre", ""))
            sede = buscar_por_id(sedes, request.form.get("sede_id", ""))
            texto_director = request.form.get("director_id", "")
            director_id = None
            errores = errores_nombre_grupo(nombre, grupos_del_anio, grupo_id)
            if sede is None:
                errores.append("Elige una sede del colegio.")
            if texto_director != "":
                director = buscar_por_id(docentes, texto_director)
                if director is not None:
                    director_id = director["id"]
                elif entero(texto_director) == grupo["director_id"]:
                    director_id = grupo["director_id"]
                else:
                    errores.append("El director de grupo debe ser un docente activo del colegio.")
            if len(errores) == 0:
                base_datos.ejecutar("UPDATE grupos SET nombre = ?, sede_id = ?, director_id = ? WHERE id = ? AND colegio_id = ?",
                                    [nombre, sede["id"], director_id, grupo_id, colegio_id])
                registrar("Editó un grupo", grupo["nombre"] + " → " + nombre)
                mensaje = "Datos del grupo guardados."
        elif accion == "asignaciones":
            resultado = guardar_asignaciones(grupo, materias, docentes)
            errores = resultado["errores"]
            avisos = resultado["avisos"]
            if resultado["cambios"] > 0:
                registrar("Guardó asignaciones", grupo["nombre"] + ": " + str(resultado["cambios"]) + " cambios")
            mensaje = "Asignaciones guardadas (" + cantidad(resultado["cambios"], "cambio", "cambios") + ")."
        elif accion == "retirar":
            matricula = matricula_del_grupo(grupo_id)
            if matricula is None:
                errores.append("Esa matrícula no está activa en este grupo.")
            else:
                base_datos.ejecutar("UPDATE matriculas SET estado = 'retirada', fecha_retiro = ? WHERE id = ?", [hoy(), matricula["id"]])
                registrar("Retiró a un estudiante", matricula["usuario"] + " de " + grupo["nombre"])
                mensaje = "Se retiró a " + matricula["nombre"] + " del grupo " + grupo["nombre"] + "."
        elif accion == "trasladar":
            matricula = matricula_del_grupo(grupo_id)
            destino = buscar_por_id(otros_grupos, request.form.get("grupo_destino", ""))
            if matricula is None:
                errores.append("Esa matrícula no está activa en este grupo.")
            elif destino is None:
                errores.append("Elige otro grupo de " + str(anio) + ".")
            else:
                base_datos.ejecutar("UPDATE matriculas SET estado = 'trasladada', fecha_retiro = ? WHERE id = ?", [hoy(), matricula["id"]])
                matricular(matricula["estudiante_id"], destino["id"])
                registrar("Trasladó a un estudiante", matricula["usuario"] + ": " + grupo["nombre"] + " → " + destino["nombre"])
                mensaje = "Se trasladó a " + matricula["nombre"] + " al grupo " + destino["nombre"] + "."
        elif accion == "matricular":
            estudiante = buscar_por_id(estudiantes_sin_matricula(), request.form.get("estudiante_id", ""))
            if estudiante is None:
                errores.append("Elige un estudiante activo que todavía no tenga matrícula en " + str(anio) + ".")
            else:
                matricular(estudiante["id"], grupo_id)
                registrar("Matriculó a un estudiante", estudiante["usuario"] + " en " + grupo["nombre"])
                mensaje = "Se matriculó a " + estudiante["nombre"] + " en " + grupo["nombre"] + "."
        else:
            errores.append("Acción no válida.")
        grupo = base_datos.buscar_grupo(grupo_id)

    estudiantes = base_datos.consultar(
        "SELECT matriculas.id, matriculas.estudiante_id, matriculas.fecha_matricula, usuarios.nombre, usuarios.usuario, usuarios.documento "
        "FROM matriculas JOIN usuarios ON usuarios.id = matriculas.estudiante_id "
        "WHERE matriculas.grupo_id = ? AND matriculas.colegio_id = ? AND matriculas.estado = 'activa' ORDER BY usuarios.nombre",
        [grupo_id, colegio_id],
    )
    salidas = base_datos.consultar(
        "SELECT matriculas.estado, matriculas.fecha_retiro, matriculas.estudiante_id, usuarios.nombre "
        "FROM matriculas JOIN usuarios ON usuarios.id = matriculas.estudiante_id "
        "WHERE matriculas.grupo_id = ? AND matriculas.colegio_id = ? AND matriculas.estado != 'activa' "
        "ORDER BY matriculas.fecha_retiro DESC, usuarios.nombre",
        [grupo_id, colegio_id],
    )
    sin_matricula = []
    if puede_matricular:
        sin_matricula = estudiantes_sin_matricula()
    director_inactivo = False
    if grupo["director_id"] is not None and buscar_por_id(docentes, str(grupo["director_id"])) is None:
        director_inactivo = True

    return render_template("admin_grupo.html", activo="admin", grupo=grupo, sedes=sedes, docentes=docentes,
                           asignaciones=filas_de_asignaciones(grupo_id, materias, docentes), estudiantes=estudiantes,
                           salidas=salidas, otros_grupos=otros_grupos, sin_matricula=sin_matricula,
                           director_inactivo=director_inactivo, academico=academico, puede_matricular=puede_matricular,
                           errores=errores, avisos=avisos, mensaje=mensaje)


@app.route("/admin/usuarios")
def admin_usuarios():
    if not tiene_alguno(g.yo, MATRICULA):
        return redirect("/inicio")

    rol = request.args.get("rol", "")
    texto = limpiar_espacios(request.args.get("texto", ""))
    estado = request.args.get("estado", "todos")
    if rol not in ROLES_ASIGNABLES:
        rol = ""
    if estado not in ESTADOS_USUARIO:
        estado = "todos"
    buscado = quitar_tildes(texto)

    personas = []
    for persona in base_datos.usuarios_del_colegio(g.colegio["id"]):
        coincide = True
        if rol != "" and rol not in persona["roles"]:
            coincide = False
        if estado == "activos" and persona["activo"] == 0:
            coincide = False
        if estado == "inactivos" and persona["activo"] == 1:
            coincide = False
        if buscado != "":
            en_nombre = buscado in quitar_tildes(persona["nombre"])
            en_usuario = buscado in persona["usuario"]
            en_documento = buscado in quitar_tildes(persona["documento"])
            if not en_nombre and not en_usuario and not en_documento:
                coincide = False
        if coincide:
            personas.append(persona)

    return render_template("admin_usuarios.html", activo="admin", personas=personas, roles=ROLES_ASIGNABLES,
                           rol=rol, texto=texto, estado=estado)


@app.route("/admin/usuarios/nuevo", methods=["GET", "POST"])
def admin_usuario_nuevo():
    if not tiene_alguno(g.yo, MATRICULA):
        return redirect("/inicio")

    grupos = base_datos.grupos_del_colegio(g.colegio["id"], g.colegio["anio"])
    datos = {"nombre": "", "documento": "", "correo": "", "telefono": ""}
    roles = []
    grupo_elegido = ""
    errores = []
    creado = None
    if request.method == "POST":
        datos = datos_del_formulario()
        roles = roles_del_formulario()
        grupo_elegido = request.form.get("grupo_id", "")
        errores = errores_de_persona(datos, roles, 0)
        grupo = None
        if grupo_elegido != "":
            grupo = buscar_por_id(grupos, grupo_elegido)
            if grupo is None:
                errores.append("El grupo elegido no existe en " + str(g.colegio["anio"]) + ".")
            elif "estudiante" not in roles:
                errores.append("Solo se puede matricular a quien tenga el rol Estudiante.")
        if len(errores) == 0:
            creado = crear_usuario(datos, roles)
            if grupo is not None:
                matricular(creado["id"], grupo["id"])
                creado["grupo"] = grupo["nombre"]
            registrar("Creó un usuario", creado["usuario"] + " (" + ", ".join(roles) + ")")
            datos = {"nombre": "", "documento": "", "correo": "", "telefono": ""}
            roles = []
            grupo_elegido = ""

    return render_template("admin_usuario_nuevo.html", activo="admin", datos=datos, roles_marcados=roles,
                           opciones_roles=opciones_de_roles(), grupos=grupos, grupo_elegido=grupo_elegido,
                           errores=errores, creado=creado)


@app.route("/admin/usuarios/<int:usuario_id>", methods=["GET", "POST"])
def admin_usuario(usuario_id):
    if not tiene_alguno(g.yo, MATRICULA):
        return redirect("/inicio")
    persona = usuario_del_colegio(usuario_id)
    if persona is None:
        return redirect("/admin/usuarios")

    colegio_id = g.colegio["id"]
    gestionable = puede_gestionar(persona)
    errores = []
    mensaje = ""
    clave_nueva = ""
    datos = persona
    roles = persona["roles"]
    if request.method == "POST":
        if not gestionable:
            return redirect("/inicio")
        accion = request.form.get("accion", "")
        if accion == "datos":
            datos = datos_del_formulario()
            roles = roles_del_formulario()
            errores = errores_de_persona(datos, roles, persona["id"]) + errores_de_roles(persona, roles)
            if len(errores) == 0:
                base_datos.ejecutar(
                    "UPDATE usuarios SET nombre = ?, documento = ?, correo = ?, telefono = ? WHERE id = ? AND colegio_id = ?",
                    [datos["nombre"], datos["documento"], datos["correo"], datos["telefono"], persona["id"], colegio_id],
                )
                for rol in persona["roles"]:
                    if rol not in roles:
                        base_datos.ejecutar("DELETE FROM roles_usuario WHERE usuario_id = ? AND rol = ?", [persona["id"], rol])
                for rol in roles:
                    if rol not in persona["roles"]:
                        base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [persona["id"], rol])
                registrar("Editó un usuario", persona["usuario"] + " (" + ", ".join(roles) + ")")
                mensaje = "Datos guardados."
        elif accion == "desactivar":
            if persona["id"] == g.yo["id"]:
                errores.append("No puedes desactivar tu propio usuario.")
            elif "administrador" in persona["roles"] and administradores_activos_sin(persona["id"]) == 0:
                errores.append("El colegio debe tener al menos un administrador activo.")
            else:
                base_datos.ejecutar("UPDATE usuarios SET activo = 0 WHERE id = ? AND colegio_id = ?", [persona["id"], colegio_id])
                registrar("Desactivó un usuario", persona["usuario"])
                mensaje = "Usuario desactivado: ya no puede entrar a la plataforma."
        elif accion == "activar":
            base_datos.ejecutar("UPDATE usuarios SET activo = 1 WHERE id = ? AND colegio_id = ?", [persona["id"], colegio_id])
            registrar("Activó un usuario", persona["usuario"])
            mensaje = "Usuario activado: ya puede entrar otra vez."
        elif accion == "restablecer":
            if persona["id"] == g.yo["id"]:
                errores.append("Para cambiar tu propia contraseña usa Mi cuenta.")
            else:
                clave_nueva = clave_temporal()
                base_datos.ejecutar("UPDATE usuarios SET clave = ?, debe_cambiar_clave = 1 WHERE id = ? AND colegio_id = ?",
                                    [generate_password_hash(clave_nueva), persona["id"], colegio_id])
                registrar("Restableció una contraseña", persona["usuario"])
                mensaje = "Contraseña restablecida. La clave anterior ya no sirve."
        elif accion == "agregar_acudido":
            estudiante = estudiante_del_colegio(entero(request.form.get("estudiante_id", "")))
            parentesco = request.form.get("parentesco", "")
            if "acudiente" not in persona["roles"]:
                errores.append("Primero dale el rol Acudiente a esta persona.")
            elif estudiante is None or estudiante["id"] == persona["id"]:
                errores.append("Elige un estudiante del colegio.")
            elif parentesco not in PARENTESCOS:
                errores.append("Elige el parentesco de la lista.")
            elif base_datos.consultar_uno("SELECT id FROM acudientes WHERE acudiente_id = ? AND estudiante_id = ?",
                                          [persona["id"], estudiante["id"]]) is not None:
                errores.append(estudiante["nombre"] + " ya está a cargo de esta persona.")
            else:
                base_datos.ejecutar(
                    "INSERT INTO acudientes (colegio_id, acudiente_id, estudiante_id, parentesco) VALUES (?, ?, ?, ?)",
                    [colegio_id, persona["id"], estudiante["id"], parentesco],
                )
                registrar("Asignó un estudiante a un acudiente", persona["usuario"] + " → " + estudiante["usuario"] + " (" + parentesco + ")")
                mensaje = estudiante["nombre"] + " quedó a cargo de " + persona["nombre"] + "."
        elif accion == "quitar_acudido":
            relacion = base_datos.consultar_uno(
                "SELECT acudientes.id, usuarios.nombre, usuarios.usuario FROM acudientes JOIN usuarios ON usuarios.id = acudientes.estudiante_id "
                "WHERE acudientes.acudiente_id = ? AND acudientes.estudiante_id = ? AND acudientes.colegio_id = ?",
                [persona["id"], entero(request.form.get("estudiante_id", "")), colegio_id],
            )
            if relacion is None:
                errores.append("Ese estudiante no está a cargo de esta persona.")
            else:
                base_datos.ejecutar("DELETE FROM acudientes WHERE id = ?", [relacion["id"]])
                registrar("Quitó un estudiante a un acudiente", persona["usuario"] + " → " + relacion["usuario"])
                mensaje = relacion["nombre"] + " ya no está a cargo de " + persona["nombre"] + "."
        else:
            errores.append("Acción no válida.")
        persona = usuario_del_colegio(usuario_id)
        if len(errores) == 0 or accion != "datos":
            datos = persona
            roles = persona["roles"]

    a_cargo = []
    opciones_estudiantes = []
    if "acudiente" in persona["roles"]:
        a_cargo = base_datos.estudiantes_a_cargo(persona["id"])
        ya_a_cargo = []
        for hijo in a_cargo:
            ya_a_cargo.append(hijo["id"])
        for estudiante in base_datos.usuarios_con_rol(colegio_id, "estudiante"):
            if estudiante["id"] not in ya_a_cargo and estudiante["id"] != persona["id"]:
                opciones_estudiantes.append(estudiante)
    grupo = None
    acudientes = []
    if "estudiante" in persona["roles"]:
        matricula = base_datos.matricula_activa(persona["id"], g.colegio["anio"])
        if matricula is not None:
            grupo = base_datos.buscar_grupo(matricula["grupo_id"])
        acudientes = base_datos.acudientes_de(persona["id"])

    return render_template("admin_usuario.html", activo="admin", persona=persona, datos=datos, roles_marcados=roles,
                           opciones_roles=opciones_de_roles(), gestionable=gestionable, clave_nueva=clave_nueva,
                           a_cargo=a_cargo, opciones_estudiantes=opciones_estudiantes, parentescos=PARENTESCOS,
                           grupo=grupo, acudientes=acudientes, errores=errores, mensaje=mensaje)


def revisar_linea(linea, grupos, documentos):
    resultado = {"error": "", "datos": None, "grupo": None}
    partes = linea.split(";")
    if len(partes) > 3:
        resultado["error"] = "tiene más de tres datos; usa Nombre completo;Documento;Grupo."
        return resultado
    if len(partes) < 3 or partes[0].strip() == "" or partes[1].strip() == "" or partes[2].strip() == "":
        resultado["error"] = "la línea está incompleta; usa Nombre completo;Documento;Grupo."
        return resultado
    datos = {"nombre": limpiar_espacios(partes[0]), "documento": limpiar_documento(partes[1]), "correo": "", "telefono": ""}
    nombre_grupo = limpiar_espacios(partes[2])
    grupo = None
    for posible in grupos:
        if clave_grupo(posible["nombre"]) == clave_grupo(nombre_grupo):
            grupo = posible
    if len(palabras_del_nombre(datos["nombre"])) < 2 or len(datos["nombre"]) > 100:
        resultado["error"] = "escribe el nombre completo: al menos un nombre y un apellido."
    elif not documento_valido(datos["documento"]):
        resultado["error"] = "el documento " + datos["documento"] + " no es válido (solo letras y números, entre 4 y 20)."
    elif datos["documento"] in documentos:
        resultado["error"] = "el documento " + datos["documento"] + " ya está registrado en el colegio."
    elif grupo is None:
        resultado["error"] = "el grupo " + nombre_grupo + " no existe en " + str(g.colegio["anio"]) + "."
    else:
        resultado["datos"] = datos
        resultado["grupo"] = grupo
    return resultado


@app.route("/admin/cargue", methods=["GET", "POST"])
def admin_cargue():
    if not tiene_alguno(g.yo, MATRICULA):
        return redirect("/inicio")

    grupos = base_datos.grupos_del_colegio(g.colegio["id"], g.colegio["anio"])
    texto = ""
    errores = []
    creados = []
    procesado = False
    if request.method == "POST":
        procesado = True
        original = request.form.get("lineas", "")
        lineas = original.replace("\t", ";").split("\n")
        if len(lineas) > MAXIMO_LINEAS:
            errores.append("Puedes cargar hasta " + str(MAXIMO_LINEAS) + " líneas a la vez. Divide la lista en partes.")
            texto = original
        else:
            documentos = documentos_del_colegio()
            pendientes = []
            numero_linea = 0
            for linea in lineas:
                numero_linea = numero_linea + 1
                limpia = linea.strip()
                while limpia.endswith(";"):
                    limpia = limpia[0:len(limpia) - 1].strip()
                if limpia != "":
                    resultado = revisar_linea(limpia, grupos, documentos)
                    if resultado["error"] != "":
                        errores.append("Línea " + str(numero_linea) + ": " + resultado["error"])
                        pendientes.append(limpia)
                    else:
                        nuevo = crear_usuario(resultado["datos"], ["estudiante"])
                        matricular(nuevo["id"], resultado["grupo"]["id"])
                        nuevo["grupo"] = resultado["grupo"]["nombre"]
                        creados.append(nuevo)
                        documentos.append(nuevo["documento"])
            texto = "\n".join(pendientes)
            if len(creados) > 0:
                registrar("Cargue masivo de estudiantes", cantidad(len(creados), "estudiante creado", "estudiantes creados")
                          + " y matriculados, " + cantidad(len(errores), "línea", "líneas") + " con error")

    return render_template("admin_cargue.html", activo="admin", grupos=grupos, texto=texto, errores=errores,
                           creados=creados, procesado=procesado, maximo=MAXIMO_LINEAS)


@app.route("/admin/registro")
def admin_registro():
    if not tiene_alguno(g.yo, VEN_REGISTRO):
        return redirect("/inicio")

    texto = limpiar_espacios(request.args.get("texto", ""))
    sql = ("SELECT registro_accesos.*, usuarios.nombre AS persona, usuarios.usuario AS usuario FROM registro_accesos "
           "LEFT JOIN usuarios ON usuarios.id = registro_accesos.usuario_id WHERE registro_accesos.colegio_id = ?")
    valores = [g.colegio["id"]]
    if texto != "":
        patron = "%" + texto + "%"
        sql = sql + (" AND (registro_accesos.accion LIKE ? OR registro_accesos.detalle LIKE ? "
                     "OR usuarios.nombre LIKE ? OR usuarios.usuario LIKE ?)")
        valores = valores + [patron, patron, patron, patron]
    sql = sql + " ORDER BY registro_accesos.id DESC LIMIT 200"

    return render_template("admin_registro.html", activo="admin", registros=base_datos.consultar(sql, valores), texto=texto)
