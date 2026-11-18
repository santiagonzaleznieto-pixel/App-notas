from datetime import date, timedelta
from flask import g, render_template, request, redirect
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, numero, estudiante_del_colegio,
                    grupo_del_estudiante, registrar, NOMBRES_ROLES, CON_DATOS_DE_EJEMPLO)
import nucleo
import base_datos

TABLAS_SERVICIOS = """
CREATE TABLE IF NOT EXISTS libros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    titulo TEXT NOT NULL,
    autor TEXT NOT NULL DEFAULT '',
    editorial TEXT NOT NULL DEFAULT '',
    isbn TEXT NOT NULL DEFAULT '',
    ejemplares INTEGER NOT NULL DEFAULT 1,
    ubicacion TEXT NOT NULL DEFAULT '',
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS prestamos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    libro_id INTEGER NOT NULL REFERENCES libros(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    prestado_en TEXT NOT NULL,
    fecha_devolucion TEXT NOT NULL,
    devuelto_en TEXT NOT NULL DEFAULT '',
    prestado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS fichas_salud (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    estudiante_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
    eps TEXT NOT NULL DEFAULT '',
    tipo_sangre TEXT NOT NULL DEFAULT '',
    alergias TEXT NOT NULL DEFAULT '',
    condiciones TEXT NOT NULL DEFAULT '',
    medicamentos TEXT NOT NULL DEFAULT '',
    contacto_emergencia TEXT NOT NULL DEFAULT '',
    telefono_emergencia TEXT NOT NULL DEFAULT '',
    actualizado_por INTEGER REFERENCES usuarios(id),
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS atenciones_enfermeria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    motivo TEXT NOT NULL,
    atencion TEXT NOT NULL,
    envio_a_casa INTEGER NOT NULL DEFAULT 0,
    acudiente_avisado INTEGER NOT NULL DEFAULT 0,
    atendido_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS autorizados_recoger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    nombre TEXT NOT NULL,
    documento TEXT NOT NULL,
    parentesco TEXT NOT NULL,
    telefono TEXT NOT NULL,
    registrado_por INTEGER REFERENCES usuarios(id),
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS salidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    motivo TEXT NOT NULL,
    recogido_por TEXT NOT NULL,
    autorizado_por INTEGER REFERENCES usuarios(id),
    registrado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS ingresos_visitantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    fecha TEXT NOT NULL,
    hora_entrada TEXT NOT NULL,
    hora_salida TEXT NOT NULL DEFAULT '',
    nombre TEXT NOT NULL,
    documento TEXT NOT NULL,
    motivo TEXT NOT NULL,
    a_quien_visita TEXT NOT NULL,
    registrado_por INTEGER REFERENCES usuarios(id)
);
"""

base_datos.crear_tablas(TABLAS_SERVICIOS)

ROLES_BIBLIOTECA = ["bibliotecario", "administrador", "docente", "estudiante"]
GESTIONAN_BIBLIOTECA = ["bibliotecario", "administrador"]
ROLES_PORTERIA = ["porteria", "coordinador", "administrador"]
AUTORIZAN_SALIDAS = ["rector", "coordinador", "orientador", "docente"]
DIAS_PRESTAMO = 8
DIAS_MAXIMOS_PRESTAMO = 180
TIPOS_SANGRE = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
PARENTESCOS = ["Madre", "Padre", "Abuela", "Abuelo", "Tía", "Tío", "Hermana mayor de edad", "Hermano mayor de edad",
               "Madrastra", "Padrastro", "Otro familiar", "Vecino o amigo de la familia", "Transportador escolar"]
CAMPOS_FICHA = ["eps", "tipo_sangre", "alergias", "condiciones", "medicamentos", "contacto_emergencia", "telefono_emergencia"]
SIN_DATO = ["", "-", "no", "na", "n/a", "ninguna", "ninguno", "no tiene", "sin alergias", "ninguna conocida"]
MOTIVOS_SALIDA = ["Cita médica", "Calamidad doméstica", "Enviado a casa por enfermería", "Diligencia familiar",
                  "Actividad deportiva o cultural"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
AVISOS_BIBLIOTECA = {
    "prestado": "Préstamo registrado.",
    "devuelto": "Devolución recibida.",
    "libro": "Libro guardado en el catálogo.",
}

agregar_menu("biblioteca", "Biblioteca", "/biblioteca", ROLES_BIBLIOTECA,
             "Catálogo, préstamos y devoluciones.")
agregar_menu("enfermeria", "Enfermería", "/enfermeria", ["enfermeria"],
             "Fichas de salud y atenciones.")
agregar_menu("salud", "Ficha de salud", "/mi-ficha-salud", ["acudiente"],
             "Alergias, EPS y contacto de emergencia de tus hijos.")
agregar_menu("porteria", "Portería", "/porteria", ROLES_PORTERIA,
             "Salidas de estudiantes, autorizados para recoger y visitantes.")
agregar_menu("autorizados", "Quién recoge", "/autorizados", ["acudiente"],
             "Personas autorizadas para recoger a tus hijos.")


def fecha_valida(texto):
    if len(texto) != 10 or texto[4] != "-" or texto[7] != "-":
        return False
    for posicion in [0, 1, 2, 3, 5, 6, 8, 9]:
        if texto[posicion] not in "0123456789":
            return False
    anio = int(texto[0:4])
    mes = int(texto[5:7])
    dia = int(texto[8:10])
    if anio < 1900 or mes < 1 or mes > 12 or dia < 1:
        return False
    dias_del_mes = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0):
        dias_del_mes[1] = 29
    return dia <= dias_del_mes[mes - 1]


def sumar_dias(fecha, dias):
    return (date.fromisoformat(fecha) + timedelta(days=dias)).isoformat()


def dias_entre(desde, hasta):
    return (date.fromisoformat(hasta) - date.fromisoformat(desde)).days


def fecha_corta(fecha):
    if not fecha_valida(fecha):
        return fecha
    return str(int(fecha[8:10])) + " " + MESES[int(fecha[5:7]) - 1] + " " + fecha[0:4]


def hora_actual():
    return nucleo.ahora()[11:16]


def campo(nombre):
    return request.form.get(nombre, "").strip()


def marcado(nombre):
    if request.form.get(nombre, "") == "1":
        return 1
    return 0


def solo_digitos(texto):
    if texto == "":
        return False
    for letra in texto:
        if letra not in "0123456789":
            return False
    return True


def entero(texto):
    if solo_digitos(texto) and len(texto) < 10:
        return int(texto)
    return None


def limpiar_documento(texto):
    return texto.replace(".", "").replace(" ", "").replace("-", "")


def documento_valido(texto):
    if len(texto) < 5 or len(texto) > 15:
        return False
    for letra in texto:
        if letra not in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz":
            return False
    return True


def telefono_valido(texto):
    digitos = 0
    for letra in texto:
        if letra in "0123456789":
            digitos = digitos + 1
        elif letra not in " +-()":
            return False
    return digitos >= 7 and digitos <= 15


def isbn_valido(texto):
    if len(texto) == 13:
        return solo_digitos(texto)
    if len(texto) == 10:
        return solo_digitos(texto[0:9]) and (texto[9] in "0123456789X")
    return False


def largo_valido(texto, minimo, maximo):
    return len(texto) >= minimo and len(texto) <= maximo


def nombre_del_grupo(estudiante_id):
    grupo = grupo_del_estudiante(estudiante_id)
    if grupo is None:
        return ""
    return grupo["nombre"]


def buscar_estudiantes(texto):
    if texto == "":
        return []
    patron = "%" + texto + "%"
    estudiantes = base_datos.consultar(
        "SELECT usuarios.id, usuarios.nombre, usuarios.usuario, usuarios.documento FROM usuarios "
        "JOIN roles_usuario ON roles_usuario.usuario_id = usuarios.id "
        "WHERE usuarios.colegio_id = ? AND usuarios.activo = 1 AND roles_usuario.rol = 'estudiante' "
        "AND (usuarios.nombre LIKE ? OR usuarios.usuario LIKE ? OR usuarios.documento LIKE ?) "
        "ORDER BY usuarios.nombre LIMIT 20",
        [g.colegio["id"], patron, patron, patron],
    )
    for estudiante in estudiantes:
        estudiante["grupo"] = nombre_del_grupo(estudiante["id"])
    return estudiantes


def acudientes_con_telefono(estudiante_id):
    acudientes = []
    for persona in base_datos.acudientes_de(estudiante_id):
        if persona["colegio_id"] == g.colegio["id"] and persona["activo"] == 1:
            acudientes.append({"id": persona["id"], "nombre": persona["nombre"], "parentesco": persona["parentesco"],
                               "telefono": persona["telefono"]})
    return acudientes


def hijos_del_acudiente():
    hijos = []
    for hijo in base_datos.estudiantes_a_cargo(g.yo["id"]):
        if hijo["colegio_id"] == g.colegio["id"]:
            hijos.append({"id": hijo["id"], "nombre": hijo["nombre"], "parentesco": hijo["parentesco"],
                          "grupo": nombre_del_grupo(hijo["id"])})
    return hijos


def buscar_hijo(hijos, estudiante_id):
    for hijo in hijos:
        if hijo["id"] == estudiante_id:
            return hijo
    return None


def puede_usar_biblioteca():
    return tiene_alguno(g.yo, ROLES_BIBLIOTECA)


def gestiona_biblioteca():
    return tiene_alguno(g.yo, GESTIONAN_BIBLIOTECA)


CONSULTA_LIBROS = ("SELECT libros.*, (SELECT COUNT(*) FROM prestamos WHERE prestamos.libro_id = libros.id "
                   "AND prestamos.devuelto_en = '') AS prestados FROM libros ")

CONSULTA_PRESTAMOS = ("SELECT prestamos.*, libros.titulo, libros.autor, usuarios.nombre AS persona "
                      "FROM prestamos JOIN libros ON libros.id = prestamos.libro_id "
                      "JOIN usuarios ON usuarios.id = prestamos.usuario_id ")


def contar_disponibles(libros):
    for libro in libros:
        libro["disponibles"] = libro["ejemplares"] - libro["prestados"]
    return libros


def libros_del_colegio(buscar, solo_activos):
    sql = CONSULTA_LIBROS + "WHERE libros.colegio_id = ?"
    valores = [g.colegio["id"]]
    if solo_activos:
        sql = sql + " AND libros.activo = 1"
    if buscar != "":
        sql = sql + " AND (libros.titulo LIKE ? OR libros.autor LIKE ?)"
        valores.append("%" + buscar + "%")
        valores.append("%" + buscar + "%")
    return contar_disponibles(base_datos.consultar(sql + " ORDER BY libros.titulo", valores))


def buscar_libro(libro_id):
    libros = base_datos.consultar(CONSULTA_LIBROS + "WHERE libros.id = ? AND libros.colegio_id = ?",
                                  [libro_id, g.colegio["id"]])
    if len(libros) == 0:
        return None
    return contar_disponibles(libros)[0]


def preparar_prestamos(prestamos):
    hoy = nucleo.hoy()
    for prestamo in prestamos:
        prestamo["vencido"] = False
        prestamo["dias_retraso"] = 0
        prestamo["dias_restantes"] = 0
        prestamo["grupo"] = nombre_del_grupo(prestamo["usuario_id"])
        if prestamo["devuelto_en"] == "":
            if prestamo["fecha_devolucion"] < hoy:
                prestamo["vencido"] = True
                prestamo["dias_retraso"] = dias_entre(prestamo["fecha_devolucion"], hoy)
            else:
                prestamo["dias_restantes"] = dias_entre(hoy, prestamo["fecha_devolucion"])
    return prestamos


def prestamos_sin_devolver():
    return preparar_prestamos(base_datos.consultar(
        CONSULTA_PRESTAMOS + "WHERE prestamos.colegio_id = ? AND prestamos.devuelto_en = '' "
        "ORDER BY prestamos.fecha_devolucion, usuarios.nombre",
        [g.colegio["id"]],
    ))


def prestamos_pendientes_de(usuario_id):
    return preparar_prestamos(base_datos.consultar(
        CONSULTA_PRESTAMOS + "WHERE prestamos.colegio_id = ? AND prestamos.usuario_id = ? AND prestamos.devuelto_en = '' "
        "ORDER BY prestamos.fecha_devolucion",
        [g.colegio["id"], usuario_id],
    ))


def prestamos_devueltos_de(usuario_id):
    return base_datos.consultar(
        CONSULTA_PRESTAMOS + "WHERE prestamos.colegio_id = ? AND prestamos.usuario_id = ? AND prestamos.devuelto_en != '' "
        "ORDER BY prestamos.devuelto_en DESC LIMIT 5",
        [g.colegio["id"], usuario_id],
    )


def contar_vencidos(usuario_id):
    fila = base_datos.consultar_uno(
        "SELECT COUNT(*) AS total FROM prestamos WHERE colegio_id = ? AND usuario_id = ? AND devuelto_en = '' "
        "AND fecha_devolucion < ?",
        [g.colegio["id"], usuario_id, nucleo.hoy()],
    )
    return fila["total"]


def ya_tiene_el_libro(usuario_id, libro_id):
    fila = base_datos.consultar_uno(
        "SELECT id FROM prestamos WHERE colegio_id = ? AND usuario_id = ? AND libro_id = ? AND devuelto_en = ''",
        [g.colegio["id"], usuario_id, libro_id],
    )
    return fila is not None


def buscar_personas(texto):
    if texto == "":
        return []
    patron = "%" + texto + "%"
    personas = base_datos.consultar(
        "SELECT id, nombre, usuario FROM usuarios WHERE colegio_id = ? AND activo = 1 "
        "AND (nombre LIKE ? OR usuario LIKE ? OR documento LIKE ?) ORDER BY nombre LIMIT 20",
        [g.colegio["id"], patron, patron, patron],
    )
    for persona in personas:
        nombres = []
        for rol in base_datos.roles_de(persona["id"]):
            nombres.append(NOMBRES_ROLES.get(rol, rol))
        persona["roles"] = nombres
        persona["grupo"] = nombre_del_grupo(persona["id"])
        persona["vencidos"] = contar_vencidos(persona["id"])
    return personas


def persona_del_colegio(usuario_id):
    if usuario_id is None:
        return None
    return base_datos.consultar_uno("SELECT id, nombre, usuario FROM usuarios WHERE id = ? AND colegio_id = ? AND activo = 1",
                                    [usuario_id, g.colegio["id"]])


def ficha_de(estudiante_id):
    return base_datos.consultar_uno(
        "SELECT fichas_salud.*, usuarios.nombre AS quien_actualizo FROM fichas_salud "
        "LEFT JOIN usuarios ON usuarios.id = fichas_salud.actualizado_por "
        "WHERE fichas_salud.estudiante_id = ? AND fichas_salud.colegio_id = ?",
        [estudiante_id, g.colegio["id"]],
    )


def ficha_vacia():
    ficha = {}
    for nombre in CAMPOS_FICHA:
        ficha[nombre] = ""
    return ficha


def ficha_para_formulario(ficha):
    datos = ficha_vacia()
    if ficha is not None:
        for nombre in CAMPOS_FICHA:
            datos[nombre] = ficha[nombre]
    return datos


def leer_ficha():
    ficha = {}
    for nombre in CAMPOS_FICHA:
        ficha[nombre] = campo(nombre)
    return ficha


def errores_de_ficha(ficha):
    errores = []
    if len(ficha["eps"]) > 80:
        errores.append("El nombre de la EPS es demasiado largo.")
    if ficha["tipo_sangre"] != "" and ficha["tipo_sangre"] not in TIPOS_SANGRE:
        errores.append("Elige un tipo de sangre de la lista.")
    if len(ficha["alergias"]) > 500 or len(ficha["condiciones"]) > 500 or len(ficha["medicamentos"]) > 500:
        errores.append("Alergias, condiciones y medicamentos admiten hasta 500 caracteres cada uno.")
    if not largo_valido(ficha["contacto_emergencia"], 3, 120):
        errores.append("Escribe el nombre del contacto de emergencia.")
    if not telefono_valido(ficha["telefono_emergencia"]):
        errores.append("El teléfono de emergencia debe tener entre 7 y 15 dígitos.")
    return errores


def guardar_ficha(estudiante_id, ficha):
    existente = ficha_de(estudiante_id)
    if existente is None:
        base_datos.ejecutar(
            "INSERT INTO fichas_salud (colegio_id, estudiante_id, eps, tipo_sangre, alergias, condiciones, medicamentos, "
            "contacto_emergencia, telefono_emergencia, actualizado_por, actualizado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [g.colegio["id"], estudiante_id, ficha["eps"], ficha["tipo_sangre"], ficha["alergias"], ficha["condiciones"],
             ficha["medicamentos"], ficha["contacto_emergencia"], ficha["telefono_emergencia"], g.yo["id"], nucleo.ahora()],
        )
    else:
        base_datos.ejecutar(
            "UPDATE fichas_salud SET eps = ?, tipo_sangre = ?, alergias = ?, condiciones = ?, medicamentos = ?, "
            "contacto_emergencia = ?, telefono_emergencia = ?, actualizado_por = ?, actualizado_en = ? "
            "WHERE id = ? AND colegio_id = ?",
            [ficha["eps"], ficha["tipo_sangre"], ficha["alergias"], ficha["condiciones"], ficha["medicamentos"],
             ficha["contacto_emergencia"], ficha["telefono_emergencia"], g.yo["id"], nucleo.ahora(),
             existente["id"], g.colegio["id"]],
        )


def sin_dato(texto):
    return texto.strip().lower() in SIN_DATO


def tiene_alergias(estudiante_id):
    ficha = base_datos.consultar_uno("SELECT alergias FROM fichas_salud WHERE estudiante_id = ? AND colegio_id = ?",
                                     [estudiante_id, g.colegio["id"]])
    if ficha is None or sin_dato(ficha["alergias"]):
        return ""
    return "Tiene alergias registradas: " + ficha["alergias"]


def atenciones_de(estudiante_id):
    return base_datos.consultar(
        "SELECT atenciones_enfermeria.*, usuarios.nombre AS atendio FROM atenciones_enfermeria "
        "LEFT JOIN usuarios ON usuarios.id = atenciones_enfermeria.atendido_por "
        "WHERE atenciones_enfermeria.estudiante_id = ? AND atenciones_enfermeria.colegio_id = ? "
        "ORDER BY atenciones_enfermeria.fecha DESC, atenciones_enfermeria.hora DESC",
        [estudiante_id, g.colegio["id"]],
    )


def atenciones_del_dia(fecha):
    atenciones = base_datos.consultar(
        "SELECT atenciones_enfermeria.*, usuarios.nombre AS estudiante FROM atenciones_enfermeria "
        "JOIN usuarios ON usuarios.id = atenciones_enfermeria.estudiante_id "
        "WHERE atenciones_enfermeria.colegio_id = ? AND atenciones_enfermeria.fecha = ? "
        "ORDER BY atenciones_enfermeria.hora DESC",
        [g.colegio["id"], fecha],
    )
    for atencion in atenciones:
        atencion["grupo"] = nombre_del_grupo(atencion["estudiante_id"])
    return atenciones


def contar_fichas():
    fila = base_datos.consultar_uno("SELECT COUNT(*) AS total FROM fichas_salud WHERE colegio_id = ?", [g.colegio["id"]])
    return fila["total"]


def puede_usar_porteria():
    return tiene_alguno(g.yo, ROLES_PORTERIA)


def autorizados_de(estudiante_id):
    return base_datos.consultar(
        "SELECT * FROM autorizados_recoger WHERE estudiante_id = ? AND colegio_id = ? AND activo = 1 ORDER BY nombre",
        [estudiante_id, g.colegio["id"]],
    )


def quienes_autorizan():
    personas = []
    vistos = []
    for rol in AUTORIZAN_SALIDAS:
        for persona in base_datos.usuarios_con_rol(g.colegio["id"], rol):
            if persona["id"] not in vistos:
                vistos.append(persona["id"])
                personas.append({"id": persona["id"], "nombre": persona["nombre"], "rol": NOMBRES_ROLES.get(rol, rol)})
    return personas


def opciones_para_recoger(estudiante_id):
    opciones = []
    for autorizado in autorizados_de(estudiante_id):
        opciones.append({
            "valor": "autorizado-" + str(autorizado["id"]),
            "nombre": autorizado["nombre"],
            "detalle": autorizado["parentesco"] + " · Doc. " + autorizado["documento"] + " · Tel. " + autorizado["telefono"],
            "texto": autorizado["nombre"] + " (" + autorizado["parentesco"] + ", doc. " + autorizado["documento"] + ")",
        })
    for acudiente in acudientes_con_telefono(estudiante_id):
        opciones.append({
            "valor": "acudiente-" + str(acudiente["id"]),
            "nombre": acudiente["nombre"],
            "detalle": acudiente["parentesco"] + " · Acudiente registrado en el colegio",
            "texto": acudiente["nombre"] + " (" + acudiente["parentesco"] + ", acudiente)",
        })
    return opciones


CONSULTA_SALIDAS = ("SELECT salidas.*, estudiantes.nombre AS estudiante, autoriza.nombre AS autorizo, "
                    "registra.nombre AS registro FROM salidas "
                    "JOIN usuarios AS estudiantes ON estudiantes.id = salidas.estudiante_id "
                    "LEFT JOIN usuarios AS autoriza ON autoriza.id = salidas.autorizado_por "
                    "LEFT JOIN usuarios AS registra ON registra.id = salidas.registrado_por ")


def salidas_del_dia(fecha):
    salidas = base_datos.consultar(CONSULTA_SALIDAS + "WHERE salidas.colegio_id = ? AND salidas.fecha = ? ORDER BY salidas.hora DESC",
                                   [g.colegio["id"], fecha])
    for salida in salidas:
        salida["grupo"] = nombre_del_grupo(salida["estudiante_id"])
    return salidas


def salidas_de(estudiante_id):
    return base_datos.consultar(
        CONSULTA_SALIDAS + "WHERE salidas.colegio_id = ? AND salidas.estudiante_id = ? "
        "ORDER BY salidas.fecha DESC, salidas.hora DESC LIMIT 5",
        [g.colegio["id"], estudiante_id],
    )


def visitantes_del_dia(fecha):
    return base_datos.consultar("SELECT * FROM ingresos_visitantes WHERE colegio_id = ? AND fecha = ? ORDER BY hora_entrada DESC",
                                [g.colegio["id"], fecha])


LIBROS_DE_EJEMPLO = [
    {"titulo": "Cien años de soledad", "autor": "Gabriel García Márquez", "editorial": "Penguin Random House",
     "ejemplares": 4, "ubicacion": "Estante A1 · Literatura colombiana"},
    {"titulo": "El coronel no tiene quien le escriba", "autor": "Gabriel García Márquez", "editorial": "Penguin Random House",
     "ejemplares": 3, "ubicacion": "Estante A1 · Literatura colombiana"},
    {"titulo": "Crónica de una muerte anunciada", "autor": "Gabriel García Márquez", "editorial": "Penguin Random House",
     "ejemplares": 5, "ubicacion": "Estante A1 · Literatura colombiana"},
    {"titulo": "La vorágine", "autor": "José Eustasio Rivera", "editorial": "Panamericana Editorial",
     "ejemplares": 3, "ubicacion": "Estante A2 · Literatura colombiana"},
    {"titulo": "María", "autor": "Jorge Isaacs", "editorial": "Panamericana Editorial",
     "ejemplares": 4, "ubicacion": "Estante A2 · Literatura colombiana"},
    {"titulo": "Delirio", "autor": "Laura Restrepo", "editorial": "Alfaguara",
     "ejemplares": 2, "ubicacion": "Estante A2 · Literatura colombiana"},
    {"titulo": "El olvido que seremos", "autor": "Héctor Abad Faciolince", "editorial": "Planeta",
     "ejemplares": 2, "ubicacion": "Estante A3 · Literatura colombiana"},
    {"titulo": "Los ejércitos", "autor": "Evelio Rosero", "editorial": "Tusquets Editores",
     "ejemplares": 2, "ubicacion": "Estante A3 · Literatura colombiana"},
    {"titulo": "La tejedora de coronas", "autor": "Germán Espinosa", "editorial": "Alfaguara",
     "ejemplares": 1, "ubicacion": "Estante A3 · Literatura colombiana"},
    {"titulo": "Diccionario escolar de la lengua española", "autor": "Real Academia Española", "editorial": "Espasa",
     "ejemplares": 6, "ubicacion": "Estante R1 · Consulta"},
    {"titulo": "Atlas básico de Colombia", "autor": "Instituto Geográfico Agustín Codazzi", "editorial": "IGAC",
     "ejemplares": 3, "ubicacion": "Estante R1 · Consulta"},
    {"titulo": "Los Caminos del Saber Matemáticas 10", "autor": "Varios autores", "editorial": "Santillana",
     "ejemplares": 8, "ubicacion": "Estante T1 · Textos escolares"},
]


def sembrar_servicios():
    if not base_datos.tabla_vacia("libros") or base_datos.buscar_colegio(1) is None:
        return
    personas = {}
    for usuario in ["melany.osorio", "juan.restrepo", "esteban.ramirez", "a.trejos", "gloria.cardenas", "olga.gomez",
                    "coordinadora", "biblioteca", "enfermeria", "porteria"]:
        persona = base_datos.buscar_usuario(usuario)
        if persona is None or persona["colegio_id"] != 1:
            return
        personas[usuario] = persona["id"]
    colegio_id = 1
    hoy = nucleo.hoy()
    ayer = sumar_dias(hoy, -1)

    libros = {}
    for libro in LIBROS_DE_EJEMPLO:
        libros[libro["titulo"]] = base_datos.ejecutar(
            "INSERT INTO libros (colegio_id, titulo, autor, editorial, isbn, ejemplares, ubicacion) VALUES (?, ?, ?, ?, '', ?, ?)",
            [colegio_id, libro["titulo"], libro["autor"], libro["editorial"], libro["ejemplares"], libro["ubicacion"]],
        )

    prestamos = [
        {"libro": "Cien años de soledad", "persona": "melany.osorio", "desde": -3, "hasta": 5},
        {"libro": "La vorágine", "persona": "juan.restrepo", "desde": -20, "hasta": -12},
        {"libro": "Crónica de una muerte anunciada", "persona": "a.trejos", "desde": -2, "hasta": 6},
    ]
    for prestamo in prestamos:
        base_datos.ejecutar(
            "INSERT INTO prestamos (colegio_id, libro_id, usuario_id, prestado_en, fecha_devolucion, prestado_por) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [colegio_id, libros[prestamo["libro"]], personas[prestamo["persona"]], sumar_dias(hoy, prestamo["desde"]),
             sumar_dias(hoy, prestamo["hasta"]), personas["biblioteca"]],
        )

    fichas = [
        {"estudiante": "melany.osorio", "eps": "Nueva EPS", "tipo_sangre": "O+", "alergias": "Penicilina",
         "condiciones": "Ninguna", "medicamentos": "Ninguno", "contacto": "Gloria Inés Cárdenas (madre)",
         "telefono": "310 456 7890", "por": "gloria.cardenas"},
        {"estudiante": "esteban.ramirez", "eps": "Asmet Salud", "tipo_sangre": "A+", "alergias": "",
         "condiciones": "Asma leve", "medicamentos": "Salbutamol inhalador en caso de crisis",
         "contacto": "Olga Lucía Gómez (madre)", "telefono": "315 765 4321", "por": "olga.gomez"},
    ]
    for ficha in fichas:
        base_datos.ejecutar(
            "INSERT INTO fichas_salud (colegio_id, estudiante_id, eps, tipo_sangre, alergias, condiciones, medicamentos, "
            "contacto_emergencia, telefono_emergencia, actualizado_por, actualizado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [colegio_id, personas[ficha["estudiante"]], ficha["eps"], ficha["tipo_sangre"], ficha["alergias"],
             ficha["condiciones"], ficha["medicamentos"], ficha["contacto"], ficha["telefono"], personas[ficha["por"]],
             sumar_dias(hoy, -40) + " 19:20"],
        )

    base_datos.ejecutar(
        "INSERT INTO atenciones_enfermeria (colegio_id, estudiante_id, fecha, hora, motivo, atencion, envio_a_casa, "
        "acudiente_avisado, atendido_por) VALUES (?, ?, ?, '10:15', ?, ?, 0, 1, ?)",
        [colegio_id, personas["esteban.ramirez"], ayer, "Dificultad para respirar después de Educación Física",
         "Usó su inhalador y descansó 20 minutos en enfermería. Se recuperó y volvió a clase. Se avisó a la madre.",
         personas["enfermeria"]],
    )

    autorizados = [
        {"nombre": "Rosalba Cárdenas Arango", "documento": "24587123", "parentesco": "Abuela", "telefono": "312 654 9870"},
        {"nombre": "Carlos Mario Osorio", "documento": "1094912345", "parentesco": "Tío", "telefono": "301 456 1234"},
    ]
    for autorizado in autorizados:
        base_datos.ejecutar(
            "INSERT INTO autorizados_recoger (colegio_id, estudiante_id, nombre, documento, parentesco, telefono, registrado_por) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [colegio_id, personas["melany.osorio"], autorizado["nombre"], autorizado["documento"], autorizado["parentesco"],
             autorizado["telefono"], personas["gloria.cardenas"]],
        )

    base_datos.ejecutar(
        "INSERT INTO salidas (colegio_id, estudiante_id, fecha, hora, motivo, recogido_por, autorizado_por, registrado_por) "
        "VALUES (?, ?, ?, '09:40', 'Diligencia familiar', ?, ?, ?)",
        [colegio_id, personas["melany.osorio"], hoy, "Rosalba Cárdenas Arango (Abuela, doc. 24587123)",
         personas["coordinadora"], personas["porteria"]],
    )

    base_datos.ejecutar(
        "INSERT INTO ingresos_visitantes (colegio_id, fecha, hora_entrada, nombre, documento, motivo, a_quien_visita, "
        "registrado_por) VALUES (?, ?, '08:20', 'Ana María Bedoya', '41923456', 'Entrega de documentos de matrícula', "
        "'Secretaría académica', ?)",
        [colegio_id, hoy, personas["porteria"]],
    )


if CON_DATOS_DE_EJEMPLO:
    sembrar_servicios()


@app.route("/biblioteca")
def biblioteca():
    if not puede_usar_biblioteca():
        return redirect("/inicio")
    gestiona = gestiona_biblioteca()
    buscar = request.args.get("buscar", "").strip()
    libros = libros_del_colegio(buscar, not gestiona)

    vencidos = []
    al_dia = []
    cifras = {"titulos": 0, "ejemplares": 0, "prestados": 0}
    if gestiona:
        for prestamo in prestamos_sin_devolver():
            if prestamo["vencido"]:
                vencidos.append(prestamo)
            else:
                al_dia.append(prestamo)
        for libro in libros_del_colegio("", True):
            cifras["titulos"] = cifras["titulos"] + 1
            cifras["ejemplares"] = cifras["ejemplares"] + libro["ejemplares"]
            cifras["prestados"] = cifras["prestados"] + libro["prestados"]

    mis_prestamos = prestamos_pendientes_de(g.yo["id"])
    mis_devueltos = prestamos_devueltos_de(g.yo["id"])
    mostrar_mios = tiene_alguno(g.yo, ["docente", "estudiante"]) or len(mis_prestamos) > 0
    mensaje = AVISOS_BIBLIOTECA.get(request.args.get("aviso", ""), "")

    return render_template("servicios_biblioteca.html", activo="biblioteca", gestiona=gestiona, buscar=buscar,
                           libros=libros, vencidos=vencidos, al_dia=al_dia, cifras=cifras, mis_prestamos=mis_prestamos,
                           mis_devueltos=mis_devueltos, mostrar_mios=mostrar_mios, mensaje=mensaje,
                           dias_prestamo=DIAS_PRESTAMO, fecha_corta=fecha_corta)


def formulario_libro(libro):
    errores = []
    datos = {"titulo": "", "autor": "", "editorial": "", "isbn": "", "ejemplares": "1", "ubicacion": "", "activo": 1}
    if libro is not None:
        datos = {"titulo": libro["titulo"], "autor": libro["autor"], "editorial": libro["editorial"], "isbn": libro["isbn"],
                 "ejemplares": str(libro["ejemplares"]), "ubicacion": libro["ubicacion"], "activo": libro["activo"]}

    if request.method == "POST":
        datos = {"titulo": campo("titulo"), "autor": campo("autor"), "editorial": campo("editorial"),
                 "isbn": limpiar_documento(campo("isbn")).upper(), "ejemplares": campo("ejemplares"),
                 "ubicacion": campo("ubicacion"), "activo": 1}
        if libro is not None:
            datos["activo"] = marcado("activo")
        minimo = 1
        if libro is not None:
            minimo = libro["prestados"]
        ejemplares = numero(datos["ejemplares"], 0, 500)

        if not largo_valido(datos["titulo"], 2, 200):
            errores.append("Escribe el título del libro.")
        if len(datos["autor"]) > 150 or len(datos["editorial"]) > 100 or len(datos["ubicacion"]) > 100:
            errores.append("Autor, editorial o ubicación son demasiado largos.")
        if datos["isbn"] != "" and not isbn_valido(datos["isbn"]):
            errores.append("El ISBN debe tener 10 o 13 dígitos (el de 10 puede terminar en X).")
        if ejemplares is None or ejemplares != int(ejemplares):
            errores.append("Los ejemplares deben ser un número entero entre 0 y 500.")
        elif int(ejemplares) < minimo:
            if libro is None:
                errores.append("Un libro nuevo debe tener al menos 1 ejemplar.")
            else:
                errores.append("Hay " + str(minimo) + " ejemplares prestados: no puedes dejar menos que eso.")

        if len(errores) == 0:
            if libro is None:
                base_datos.ejecutar(
                    "INSERT INTO libros (colegio_id, titulo, autor, editorial, isbn, ejemplares, ubicacion, activo) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                    [g.colegio["id"], datos["titulo"], datos["autor"], datos["editorial"], datos["isbn"], int(ejemplares),
                     datos["ubicacion"]],
                )
                registrar("Agregó un libro a la biblioteca", datos["titulo"])
            else:
                base_datos.ejecutar(
                    "UPDATE libros SET titulo = ?, autor = ?, editorial = ?, isbn = ?, ejemplares = ?, ubicacion = ?, activo = ? "
                    "WHERE id = ? AND colegio_id = ?",
                    [datos["titulo"], datos["autor"], datos["editorial"], datos["isbn"], int(ejemplares), datos["ubicacion"],
                     datos["activo"], libro["id"], g.colegio["id"]],
                )
                registrar("Editó un libro de la biblioteca", datos["titulo"])
            return redirect("/biblioteca?aviso=libro")

    return render_template("servicios_libro.html", activo="biblioteca", libro=libro, datos=datos, errores=errores)


@app.route("/biblioteca/libro/nuevo", methods=["GET", "POST"])
def biblioteca_libro_nuevo():
    if not gestiona_biblioteca():
        return redirect("/inicio")
    return formulario_libro(None)


@app.route("/biblioteca/libro/<int:libro_id>", methods=["GET", "POST"])
def biblioteca_libro(libro_id):
    if not gestiona_biblioteca():
        return redirect("/inicio")
    libro = buscar_libro(libro_id)
    if libro is None:
        return redirect("/inicio")
    return formulario_libro(libro)


@app.route("/biblioteca/prestar", methods=["GET", "POST"])
def biblioteca_prestar():
    if not gestiona_biblioteca():
        return redirect("/inicio")
    hoy = nucleo.hoy()
    errores = []
    buscar = request.args.get("persona", "").strip()
    persona_elegida = None
    libro_elegido = entero(request.args.get("libro", ""))
    por_defecto = sumar_dias(hoy, DIAS_PRESTAMO)
    fecha_devolucion = por_defecto

    if request.method == "POST":
        buscar = campo("buscar")
        persona = persona_del_colegio(entero(campo("persona_id")))
        libro = None
        if entero(campo("libro_id")) is not None:
            libro = buscar_libro(entero(campo("libro_id")))
        fecha_devolucion = campo("fecha_devolucion")

        if persona is None:
            errores.append("Elige a la persona que se lleva el libro.")
        else:
            persona_elegida = persona["id"]
            if contar_vencidos(persona["id"]) > 0:
                errores.append(persona["nombre"] + " tiene préstamos vencidos: primero debe devolverlos.")
        if libro is None or libro["activo"] == 0:
            errores.append("Elige un libro del catálogo.")
        else:
            libro_elegido = libro["id"]
            if libro["disponibles"] <= 0:
                errores.append("No hay ejemplares disponibles de «" + libro["titulo"] + "».")
            elif persona is not None and ya_tiene_el_libro(persona["id"], libro["id"]):
                errores.append(persona["nombre"] + " ya tiene prestado un ejemplar de este libro.")
        if not fecha_valida(fecha_devolucion):
            errores.append("La fecha de devolución no es válida.")
            fecha_devolucion = por_defecto
        elif fecha_devolucion <= hoy or fecha_devolucion > sumar_dias(hoy, DIAS_MAXIMOS_PRESTAMO):
            errores.append("La fecha de devolución debe estar entre mañana y los próximos " + str(DIAS_MAXIMOS_PRESTAMO) + " días.")

        if len(errores) == 0:
            base_datos.ejecutar(
                "INSERT INTO prestamos (colegio_id, libro_id, usuario_id, prestado_en, fecha_devolucion, prestado_por) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [g.colegio["id"], libro["id"], persona["id"], hoy, fecha_devolucion, g.yo["id"]],
            )
            registrar("Prestó un libro", libro["titulo"] + " a " + persona["nombre"] + " hasta el " + fecha_devolucion)
            return redirect("/biblioteca?aviso=prestado")

    return render_template("servicios_prestar.html", activo="biblioteca", errores=errores, buscar=buscar,
                           personas=buscar_personas(buscar), persona_elegida=persona_elegida,
                           libros=libros_del_colegio("", True), libro_elegido=libro_elegido,
                           fecha_devolucion=fecha_devolucion, por_defecto=por_defecto, manana=sumar_dias(hoy, 1),
                           maxima=sumar_dias(hoy, DIAS_MAXIMOS_PRESTAMO), dias_prestamo=DIAS_PRESTAMO, fecha_corta=fecha_corta)


@app.route("/biblioteca/devolver/<int:prestamo_id>", methods=["POST"])
def biblioteca_devolver(prestamo_id):
    if not gestiona_biblioteca():
        return redirect("/inicio")
    prestamo = base_datos.consultar_uno(CONSULTA_PRESTAMOS + "WHERE prestamos.id = ? AND prestamos.colegio_id = ?",
                                        [prestamo_id, g.colegio["id"]])
    if prestamo is None or prestamo["devuelto_en"] != "":
        return redirect("/biblioteca")
    base_datos.ejecutar("UPDATE prestamos SET devuelto_en = ? WHERE id = ? AND colegio_id = ?",
                        [nucleo.hoy(), prestamo_id, g.colegio["id"]])
    registrar("Recibió la devolución de un libro", prestamo["titulo"] + " de " + prestamo["persona"])
    return redirect("/biblioteca?aviso=devuelto")


@app.route("/enfermeria")
def enfermeria():
    if not tiene_rol(g.yo, "enfermeria"):
        return redirect("/inicio")
    buscar = request.args.get("buscar", "").strip()
    resultados = buscar_estudiantes(buscar)
    for estudiante in resultados:
        estudiante["alerta"] = tiene_alergias(estudiante["id"])
    atenciones = atenciones_del_dia(nucleo.hoy())
    enviados = 0
    for atencion in atenciones:
        if atencion["envio_a_casa"] == 1:
            enviados = enviados + 1
    return render_template("servicios_enfermeria.html", activo="enfermeria", buscar=buscar, resultados=resultados,
                           atenciones=atenciones, enviados=enviados, fichas=contar_fichas(), hoy=nucleo.hoy(),
                           fecha_corta=fecha_corta)


@app.route("/enfermeria/estudiante/<int:estudiante_id>", methods=["GET", "POST"])
def enfermeria_estudiante(estudiante_id):
    if not tiene_rol(g.yo, "enfermeria"):
        return redirect("/inicio")
    estudiante = estudiante_del_colegio(estudiante_id)
    if estudiante is None:
        return redirect("/inicio")

    errores = []
    mensaje = ""
    enviado_a_casa = False
    abrir_ficha = False
    nueva = {"motivo": "", "atencion": "", "envio_a_casa": 0, "acudiente_avisado": 0}
    datos_ficha = None
    if request.method == "POST":
        accion = campo("accion")
        if accion == "atencion":
            nueva = {"motivo": campo("motivo"), "atencion": campo("atencion"), "envio_a_casa": marcado("envio_a_casa"),
                     "acudiente_avisado": marcado("acudiente_avisado")}
            if not largo_valido(nueva["motivo"], 3, 300):
                errores.append("Escribe el motivo de la consulta (entre 3 y 300 caracteres).")
            if not largo_valido(nueva["atencion"], 3, 1000):
                errores.append("Escribe qué atención se le dio (entre 3 y 1000 caracteres).")
            if nueva["envio_a_casa"] == 1 and nueva["acudiente_avisado"] == 0:
                errores.append("Para enviarlo a casa, primero llama al acudiente y marca «Avisé al acudiente».")
            if len(errores) == 0:
                base_datos.ejecutar(
                    "INSERT INTO atenciones_enfermeria (colegio_id, estudiante_id, fecha, hora, motivo, atencion, envio_a_casa, "
                    "acudiente_avisado, atendido_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [g.colegio["id"], estudiante_id, nucleo.hoy(), hora_actual(), nueva["motivo"], nueva["atencion"],
                     nueva["envio_a_casa"], nueva["acudiente_avisado"], g.yo["id"]],
                )
                registrar("Registró una atención de enfermería", estudiante["nombre"])
                mensaje = "Atención registrada."
                enviado_a_casa = nueva["envio_a_casa"] == 1
                nueva = {"motivo": "", "atencion": "", "envio_a_casa": 0, "acudiente_avisado": 0}
        elif accion == "ficha":
            datos_ficha = leer_ficha()
            errores = errores_de_ficha(datos_ficha)
            if len(errores) == 0:
                guardar_ficha(estudiante_id, datos_ficha)
                registrar("Actualizó una ficha de salud", estudiante["nombre"])
                mensaje = "Ficha de salud guardada."
                datos_ficha = None
            else:
                abrir_ficha = True

    ficha = ficha_de(estudiante_id)
    if datos_ficha is None:
        datos_ficha = ficha_para_formulario(ficha)

    return render_template("servicios_ficha.html", activo="enfermeria", estudiante=estudiante,
                           grupo=grupo_del_estudiante(estudiante_id), ficha=ficha, datos_ficha=datos_ficha,
                           alerta=tiene_alergias(estudiante_id), acudientes=acudientes_con_telefono(estudiante_id),
                           atenciones=atenciones_de(estudiante_id), nueva=nueva, errores=errores, mensaje=mensaje,
                           enviado_a_casa=enviado_a_casa, abrir_ficha=abrir_ficha, tipos_sangre=TIPOS_SANGRE,
                           fecha_corta=fecha_corta)


@app.route("/mi-ficha-salud", methods=["GET", "POST"])
def mi_ficha_salud():
    if not tiene_rol(g.yo, "acudiente"):
        return redirect("/inicio")
    hijos = hijos_del_acudiente()
    errores = []
    mensaje = ""
    hijo = None
    ficha = None
    datos_ficha = ficha_vacia()
    atenciones = []

    if len(hijos) > 0:
        hijo = hijos[0]
        texto = request.args.get("estudiante", "")
        if request.method == "POST":
            texto = campo("estudiante_id")
        if texto != "":
            hijo = buscar_hijo(hijos, entero(texto))
            if hijo is None:
                return redirect("/inicio")

        guardado = False
        if request.method == "POST":
            datos_ficha = leer_ficha()
            errores = errores_de_ficha(datos_ficha)
            if marcado("autorizo") == 0:
                errores.append("Para guardar, marca la casilla de autorización del tratamiento de datos de salud.")
            if len(errores) == 0:
                guardar_ficha(hijo["id"], datos_ficha)
                registrar("Actualizó la ficha de salud de su acudido", hijo["nombre"])
                mensaje = "Ficha de salud de " + hijo["nombre"] + " guardada. Gracias por mantenerla al día."
                guardado = True

        ficha = ficha_de(hijo["id"])
        if request.method != "POST" or guardado:
            datos_ficha = ficha_para_formulario(ficha)
        atenciones = atenciones_de(hijo["id"])

    return render_template("servicios_mi_salud.html", activo="salud", hijos=hijos, hijo=hijo, ficha=ficha,
                           datos_ficha=datos_ficha, atenciones=atenciones, errores=errores, mensaje=mensaje,
                           tipos_sangre=TIPOS_SANGRE, fecha_corta=fecha_corta)


@app.route("/porteria", methods=["GET", "POST"])
def porteria():
    if not puede_usar_porteria():
        return redirect("/inicio")
    hoy = nucleo.hoy()
    errores = []
    mensaje = ""
    visitante = {"nombre": "", "documento": "", "motivo": "", "a_quien_visita": ""}

    if request.method == "POST":
        accion = campo("accion")
        if accion == "visitante":
            visitante = {"nombre": campo("nombre"), "documento": limpiar_documento(campo("documento")),
                         "motivo": campo("motivo"), "a_quien_visita": campo("a_quien_visita")}
            if not largo_valido(visitante["nombre"], 3, 120):
                errores.append("Escribe el nombre completo del visitante.")
            if not documento_valido(visitante["documento"]):
                errores.append("El documento del visitante debe tener entre 5 y 15 letras o números.")
            if not largo_valido(visitante["motivo"], 3, 200):
                errores.append("Escribe el motivo de la visita.")
            if not largo_valido(visitante["a_quien_visita"], 3, 120):
                errores.append("Escribe a quién o a qué dependencia visita.")
            if len(errores) == 0:
                base_datos.ejecutar(
                    "INSERT INTO ingresos_visitantes (colegio_id, fecha, hora_entrada, nombre, documento, motivo, a_quien_visita, "
                    "registrado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [g.colegio["id"], hoy, hora_actual(), visitante["nombre"], visitante["documento"], visitante["motivo"],
                     visitante["a_quien_visita"], g.yo["id"]],
                )
                registrar("Registró la entrada de un visitante", visitante["nombre"])
                mensaje = "Entrada de " + visitante["nombre"] + " registrada a las " + hora_actual() + "."
                visitante = {"nombre": "", "documento": "", "motivo": "", "a_quien_visita": ""}
        elif accion == "salida_visitante":
            registro = base_datos.consultar_uno(
                "SELECT * FROM ingresos_visitantes WHERE id = ? AND colegio_id = ? AND fecha = ? AND hora_salida = ''",
                [entero(campo("visitante_id")), g.colegio["id"], hoy],
            )
            if registro is None:
                errores.append("Ese visitante ya salió o no entró hoy.")
            else:
                base_datos.ejecutar("UPDATE ingresos_visitantes SET hora_salida = ? WHERE id = ? AND colegio_id = ?",
                                    [hora_actual(), registro["id"], g.colegio["id"]])
                registrar("Registró la salida de un visitante", registro["nombre"])
                mensaje = "Salida de " + registro["nombre"] + " registrada."

    buscar = request.args.get("buscar", "").strip()
    fecha = request.args.get("fecha", "").strip()
    if fecha == "":
        fecha = hoy
    elif not fecha_valida(fecha):
        errores.append("La fecha para consultar no es válida.")
        fecha = hoy

    resultados = buscar_estudiantes(buscar)
    for estudiante in resultados:
        estudiante["autorizados"] = len(autorizados_de(estudiante["id"]))
    visitantes = visitantes_del_dia(fecha)
    adentro = 0
    for persona in visitantes:
        if persona["hora_salida"] == "":
            adentro = adentro + 1

    return render_template("servicios_porteria.html", activo="porteria", buscar=buscar, resultados=resultados,
                           fecha=fecha, es_hoy=fecha == hoy, salidas=salidas_del_dia(fecha), visitantes=visitantes,
                           adentro=adentro, visitante=visitante, errores=errores, mensaje=mensaje, fecha_corta=fecha_corta)


@app.route("/porteria/estudiante/<int:estudiante_id>", methods=["GET", "POST"])
def porteria_estudiante(estudiante_id):
    if not puede_usar_porteria():
        return redirect("/inicio")
    estudiante = estudiante_del_colegio(estudiante_id)
    if estudiante is None:
        return redirect("/inicio")

    opciones = opciones_para_recoger(estudiante_id)
    autorizan = quienes_autorizan()
    errores = []
    mensaje = ""
    vacio = {"motivo": "", "recoge": "", "otro_nombre": "", "otro_documento": "", "autorizado_por": ""}
    for persona in autorizan:
        if persona["id"] == g.yo["id"]:
            vacio["autorizado_por"] = str(g.yo["id"])
    datos = vacio

    if request.method == "POST":
        datos = {"motivo": campo("motivo"), "recoge": campo("recoge"), "otro_nombre": campo("otro_nombre"),
                 "otro_documento": limpiar_documento(campo("otro_documento")), "autorizado_por": campo("autorizado_por")}
        recogido_por = ""
        if datos["recoge"] == "otro":
            if not largo_valido(datos["otro_nombre"], 3, 120):
                errores.append("Escribe el nombre completo de quien recoge al estudiante.")
            if not documento_valido(datos["otro_documento"]):
                errores.append("Escribe el documento de quien recoge al estudiante (entre 5 y 15 letras o números).")
            recogido_por = datos["otro_nombre"] + " (doc. " + datos["otro_documento"] + ") · no estaba en la lista de autorizados"
        else:
            for opcion in opciones:
                if opcion["valor"] == datos["recoge"]:
                    recogido_por = opcion["texto"]
            if recogido_por == "":
                errores.append("Elige quién recoge al estudiante.")
        autoriza = None
        for persona in autorizan:
            if str(persona["id"]) == datos["autorizado_por"]:
                autoriza = persona
        if autoriza is None:
            errores.append("Elige quién autorizó la salida en el colegio.")
        if not largo_valido(datos["motivo"], 3, 200):
            errores.append("Escribe el motivo de la salida.")

        if len(errores) == 0:
            hora = hora_actual()
            base_datos.ejecutar(
                "INSERT INTO salidas (colegio_id, estudiante_id, fecha, hora, motivo, recogido_por, autorizado_por, registrado_por) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [g.colegio["id"], estudiante_id, nucleo.hoy(), hora, datos["motivo"], recogido_por, autoriza["id"], g.yo["id"]],
            )
            registrar("Registró la salida anticipada de un estudiante", estudiante["nombre"])
            mensaje = estudiante["nombre"] + " salió a las " + hora + " con " + recogido_por + "."
            datos = vacio

    return render_template("servicios_porteria_estudiante.html", activo="porteria", estudiante=estudiante,
                           grupo=grupo_del_estudiante(estudiante_id), opciones=opciones, autorizan=autorizan,
                           autorizados=autorizados_de(estudiante_id), salidas=salidas_de(estudiante_id), datos=datos,
                           motivos=MOTIVOS_SALIDA, errores=errores, mensaje=mensaje, fecha_corta=fecha_corta)


@app.route("/autorizados", methods=["GET", "POST"])
def autorizados():
    if not tiene_rol(g.yo, "acudiente"):
        return redirect("/inicio")
    hijos = hijos_del_acudiente()
    errores = []
    mensaje = ""
    vacio = {"estudiante_id": "", "nombre": "", "documento": "", "parentesco": "", "telefono": ""}
    nuevo = vacio

    if request.method == "POST":
        accion = campo("accion")
        if accion == "agregar":
            nuevo = {"estudiante_id": campo("estudiante_id"), "nombre": campo("nombre"),
                     "documento": limpiar_documento(campo("documento")), "parentesco": campo("parentesco"),
                     "telefono": campo("telefono")}
            hijo = buscar_hijo(hijos, entero(nuevo["estudiante_id"]))
            if hijo is None:
                return redirect("/inicio")
            if not largo_valido(nuevo["nombre"], 5, 120):
                errores.append("Escribe el nombre completo de la persona autorizada.")
            if not solo_digitos(nuevo["documento"]) or not largo_valido(nuevo["documento"], 5, 12):
                errores.append("El documento debe tener solo números, entre 5 y 12 dígitos.")
            if nuevo["parentesco"] not in PARENTESCOS:
                errores.append("Elige el parentesco de la lista.")
            if not telefono_valido(nuevo["telefono"]):
                errores.append("El teléfono debe tener entre 7 y 15 dígitos.")
            for autorizado in autorizados_de(hijo["id"]):
                if autorizado["documento"] == nuevo["documento"]:
                    errores.append("Esa persona ya está autorizada para recoger a " + hijo["nombre"] + ".")
            if len(errores) == 0:
                base_datos.ejecutar(
                    "INSERT INTO autorizados_recoger (colegio_id, estudiante_id, nombre, documento, parentesco, telefono, "
                    "registrado_por) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [g.colegio["id"], hijo["id"], nuevo["nombre"], nuevo["documento"], nuevo["parentesco"], nuevo["telefono"],
                     g.yo["id"]],
                )
                registrar("Autorizó a una persona para recoger a su acudido", hijo["nombre"] + ": " + nuevo["nombre"])
                mensaje = nuevo["nombre"] + " ya puede recoger a " + hijo["nombre"] + "."
                nuevo = vacio
        elif accion == "desactivar":
            autorizado = base_datos.consultar_uno(
                "SELECT * FROM autorizados_recoger WHERE id = ? AND colegio_id = ? AND activo = 1",
                [entero(campo("autorizado_id")), g.colegio["id"]],
            )
            if autorizado is None or buscar_hijo(hijos, autorizado["estudiante_id"]) is None:
                return redirect("/inicio")
            base_datos.ejecutar("UPDATE autorizados_recoger SET activo = 0 WHERE id = ? AND colegio_id = ?",
                                [autorizado["id"], g.colegio["id"]])
            registrar("Quitó una autorización para recoger", autorizado["nombre"])
            mensaje = autorizado["nombre"] + " ya no está autorizado(a) para recoger."

    for hijo in hijos:
        hijo["autorizados"] = autorizados_de(hijo["id"])
        hijo["salidas"] = salidas_de(hijo["id"])
        hijo["acudientes"] = acudientes_con_telefono(hijo["id"])

    return render_template("servicios_autorizados.html", activo="autorizados", hijos=hijos, nuevo=nuevo,
                           parentescos=PARENTESCOS, errores=errores, mensaje=mensaje, fecha_corta=fecha_corta)
