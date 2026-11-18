import os
import sqlite3

CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(CARPETA_PROYECTO, "plataforma.db")
if os.environ.get("RUTA_BASE_DATOS", "") != "":
    ARCHIVO = os.environ.get("RUTA_BASE_DATOS")
elif os.environ.get("VERCEL", "") != "":
    ARCHIVO = "/tmp/plataforma.db"

URL = os.environ.get("URL_BASE_DATOS", "")
if URL == "":
    URL = os.environ.get("POSTGRES_URL", "")
CONFLICTOS = {
    "notas": ["anio", "estudiante_id", "materia_id", "periodo"],
    "asistencia": ["asignacion_id", "estudiante_id", "fecha"],
    "asistencia_encuentros": ["encuentro_id", "acudiente_id"],
    "calificaciones": ["actividad_id", "estudiante_id"],
    "desempenos_manuales": ["anio", "estudiante_id", "materia_id", "periodo"],
}
COMPARTIDA = {"conexion": None}
PROTEGER_TABLAS = """
DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = current_schema() AND rowsecurity = false LOOP
    EXECUTE 'ALTER TABLE ' || quote_ident(t.tablename) || ' ENABLE ROW LEVEL SECURITY';
  END LOOP;
END $$;
"""

TABLAS = """
CREATE TABLE IF NOT EXISTS colegios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    nombre_corto TEXT NOT NULL,
    municipio TEXT NOT NULL,
    departamento TEXT NOT NULL,
    codigo_dane TEXT NOT NULL DEFAULT '',
    lema TEXT NOT NULL DEFAULT '',
    anio INTEGER NOT NULL,
    nota_minima REAL NOT NULL DEFAULT 1.0,
    nota_maxima REAL NOT NULL DEFAULT 5.0,
    limite_basico REAL NOT NULL DEFAULT 3.0,
    limite_alto REAL NOT NULL DEFAULT 4.0,
    limite_superior REAL NOT NULL DEFAULT 4.6
);

CREATE TABLE IF NOT EXISTS sedes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    nombre TEXT NOT NULL,
    jornada TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS grados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    nombre TEXT NOT NULL,
    nivel TEXT NOT NULL,
    orden INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    usuario TEXT NOT NULL UNIQUE,
    clave TEXT NOT NULL,
    nombre TEXT NOT NULL,
    documento TEXT NOT NULL DEFAULT '',
    correo TEXT NOT NULL DEFAULT '',
    telefono TEXT NOT NULL DEFAULT '',
    activo INTEGER NOT NULL DEFAULT 1,
    debe_cambiar_clave INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS roles_usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    rol TEXT NOT NULL,
    UNIQUE (usuario_id, rol)
);

CREATE TABLE IF NOT EXISTS grupos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    grado_id INTEGER NOT NULL REFERENCES grados(id),
    sede_id INTEGER NOT NULL REFERENCES sedes(id),
    nombre TEXT NOT NULL,
    director_id INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS matriculas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    grupo_id INTEGER NOT NULL REFERENCES grupos(id),
    estado TEXT NOT NULL DEFAULT 'activa',
    fecha_matricula TEXT NOT NULL,
    fecha_retiro TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS acudientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    acudiente_id INTEGER NOT NULL REFERENCES usuarios(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    parentesco TEXT NOT NULL,
    UNIQUE (acudiente_id, estudiante_id)
);

CREATE TABLE IF NOT EXISTS materias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    nombre TEXT NOT NULL,
    corto TEXT NOT NULL,
    area TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS asignaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    grupo_id INTEGER NOT NULL REFERENCES grupos(id),
    materia_id INTEGER NOT NULL REFERENCES materias(id),
    docente_id INTEGER NOT NULL REFERENCES usuarios(id),
    horas_semana INTEGER NOT NULL DEFAULT 1,
    UNIQUE (grupo_id, materia_id)
);

CREATE TABLE IF NOT EXISTS periodos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    numero INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    porcentaje REAL NOT NULL,
    abierto INTEGER NOT NULL DEFAULT 1,
    UNIQUE (colegio_id, anio, numero)
);

CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    materia_id INTEGER NOT NULL REFERENCES materias(id),
    periodo INTEGER NOT NULL,
    valor REAL,
    UNIQUE (anio, estudiante_id, materia_id, periodo)
);

CREATE TABLE IF NOT EXISTS actividades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    asignacion_id INTEGER NOT NULL REFERENCES asignaciones(id),
    periodo INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    fecha TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    creado_por INTEGER REFERENCES usuarios(id),
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    actividad_id INTEGER NOT NULL REFERENCES actividades(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    valor REAL,
    observacion TEXT NOT NULL DEFAULT '',
    actualizado_en TEXT NOT NULL,
    UNIQUE (actividad_id, estudiante_id)
);

CREATE TABLE IF NOT EXISTS desempenos_manuales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    materia_id INTEGER NOT NULL REFERENCES materias(id),
    periodo INTEGER NOT NULL,
    desempeno TEXT NOT NULL,
    definido_por INTEGER REFERENCES usuarios(id),
    definido_en TEXT NOT NULL,
    UNIQUE (anio, estudiante_id, materia_id, periodo)
);

CREATE TABLE IF NOT EXISTS registro_accesos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    accion TEXT NOT NULL,
    detalle TEXT NOT NULL DEFAULT ''
);
"""


def usa_postgres():
    return URL != ""


def convertir_reemplazo(texto):
    resto = texto.lstrip()[len("INSERT OR REPLACE INTO "):]
    tabla = resto[:resto.find("(")].strip()
    columnas = resto[resto.find("(") + 1:resto.find(")")].split(",")
    conflicto = CONFLICTOS[tabla]
    cambios = []
    for columna in columnas:
        nombre = columna.strip()
        if nombre not in conflicto:
            cambios.append(nombre + " = EXCLUDED." + nombre)
    return "INSERT INTO " + resto + " ON CONFLICT (" + ", ".join(conflicto) + ") DO UPDATE SET " + ", ".join(cambios)


def traducir(sql):
    if not usa_postgres():
        return sql
    texto = sql.replace("%", "%%").replace("?", "%s")
    texto = texto.replace(" LIKE ", " ILIKE ")
    texto = texto.replace(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = %s",
        "SELECT table_name AS name FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = %s",
    )
    if texto.lstrip().startswith("INSERT OR IGNORE INTO"):
        texto = texto.replace("INSERT OR IGNORE INTO", "INSERT INTO", 1) + " ON CONFLICT DO NOTHING"
    elif texto.lstrip().startswith("INSERT OR REPLACE INTO"):
        texto = convertir_reemplazo(texto)
    return texto


def limpiar_url(direccion):
    signo = direccion.find("?")
    if signo == -1:
        return direccion
    base = direccion[:signo]
    permitidos = []
    for parte in direccion[signo + 1:].split("&"):
        if parte.startswith("sslmode="):
            permitidos.append(parte)
    if len(permitidos) == 0:
        return base
    return base + "?" + "&".join(permitidos)


def conectar():
    if usa_postgres():
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(limpiar_url(URL), row_factory=dict_row, prepare_threshold=None, connect_timeout=10)
    conexion = sqlite3.connect(ARCHIVO)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def compartida():
    conexion = COMPARTIDA["conexion"]
    if conexion is None or conexion.closed or conexion.broken:
        conexion = conectar()
        conexion.autocommit = True
        COMPARTIDA["conexion"] = conexion
    return conexion


def en(conexion, sql, valores):
    return conexion.execute(traducir(sql), valores)


def consultar(sql, valores):
    if usa_postgres():
        filas = compartida().execute(traducir(sql), valores).fetchall()
    else:
        conexion = conectar()
        filas = conexion.execute(sql, valores).fetchall()
        conexion.close()
    lista = []
    for fila in filas:
        lista.append(dict(fila))
    return lista


def consultar_uno(sql, valores):
    filas = consultar(sql, valores)
    if len(filas) == 0:
        return None
    return filas[0]


def ejecutar(sql, valores):
    if usa_postgres():
        texto = traducir(sql)
        con_id = texto.lstrip().upper().startswith("INSERT") and "RETURNING" not in texto.upper()
        if con_id:
            texto = texto + " RETURNING id"
        cursor = compartida().execute(texto, valores)
        if not con_id:
            return None
        fila = cursor.fetchone()
        if fila is None:
            return None
        return fila["id"]
    conexion = conectar()
    cursor = conexion.execute(sql, valores)
    conexion.commit()
    nuevo_id = cursor.lastrowid
    conexion.close()
    return nuevo_id


def crear_tablas(script):
    if usa_postgres():
        texto = script.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY")
        texto = texto.replace("id INTEGER PRIMARY KEY,", "id BIGINT PRIMARY KEY,")
        texto = texto.replace(" REAL", " DOUBLE PRECISION")
        conexion = conectar()
        conexion.execute("SELECT pg_advisory_xact_lock(20261118)")
        conexion.execute(texto)
        conexion.execute(PROTEGER_TABLAS)
        conexion.commit()
        conexion.close()
        return
    conexion = conectar()
    conexion.executescript(script)
    conexion.close()


def tabla_vacia(tabla):
    return consultar_uno("SELECT id FROM " + tabla + " LIMIT 1", []) is None


def reclamar_siembra(numero):
    if not usa_postgres():
        return True
    crear_tablas("CREATE TABLE IF NOT EXISTS control_siembra (id INTEGER PRIMARY KEY)")
    fila = compartida().execute("INSERT INTO control_siembra (id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id", [numero]).fetchone()
    return fila is not None


def buscar_colegio(colegio_id):
    return consultar_uno("SELECT * FROM colegios WHERE id = ?", [colegio_id])


def buscar_usuario(usuario):
    return consultar_uno("SELECT * FROM usuarios WHERE usuario = ?", [usuario])


def buscar_usuario_por_id(usuario_id):
    return consultar_uno("SELECT * FROM usuarios WHERE id = ?", [usuario_id])


def roles_de(usuario_id):
    roles = []
    for fila in consultar("SELECT rol FROM roles_usuario WHERE usuario_id = ? ORDER BY id", [usuario_id]):
        roles.append(fila["rol"])
    return roles


def usuarios_del_colegio(colegio_id):
    usuarios = consultar("SELECT * FROM usuarios WHERE colegio_id = ? ORDER BY nombre", [colegio_id])
    for persona in usuarios:
        persona["roles"] = roles_de(persona["id"])
    return usuarios


def usuarios_con_rol(colegio_id, rol):
    return consultar(
        "SELECT usuarios.* FROM usuarios JOIN roles_usuario ON roles_usuario.usuario_id = usuarios.id "
        "WHERE usuarios.colegio_id = ? AND roles_usuario.rol = ? AND usuarios.activo = 1 ORDER BY usuarios.nombre",
        [colegio_id, rol],
    )


def sedes_del_colegio(colegio_id):
    return consultar("SELECT * FROM sedes WHERE colegio_id = ? ORDER BY id", [colegio_id])


def grados_del_colegio(colegio_id):
    return consultar("SELECT * FROM grados WHERE colegio_id = ? ORDER BY orden", [colegio_id])


def grupos_del_colegio(colegio_id, anio):
    return consultar(
        "SELECT grupos.*, grados.nombre AS grado, grados.orden AS orden_grado, sedes.nombre AS sede, "
        "usuarios.nombre AS director "
        "FROM grupos JOIN grados ON grados.id = grupos.grado_id JOIN sedes ON sedes.id = grupos.sede_id "
        "LEFT JOIN usuarios ON usuarios.id = grupos.director_id "
        "WHERE grupos.colegio_id = ? AND grupos.anio = ? ORDER BY grados.orden, grupos.nombre",
        [colegio_id, anio],
    )


def buscar_grupo(grupo_id):
    return consultar_uno(
        "SELECT grupos.*, grados.nombre AS grado, grados.nivel AS nivel, sedes.nombre AS sede, sedes.jornada AS jornada, "
        "usuarios.nombre AS director "
        "FROM grupos JOIN grados ON grados.id = grupos.grado_id JOIN sedes ON sedes.id = grupos.sede_id "
        "LEFT JOIN usuarios ON usuarios.id = grupos.director_id WHERE grupos.id = ?",
        [grupo_id],
    )


def grupos_dirigidos(docente_id, anio):
    return consultar("SELECT id FROM grupos WHERE director_id = ? AND anio = ?", [docente_id, anio])


def estudiantes_del_grupo(grupo_id):
    return consultar(
        "SELECT usuarios.* FROM matriculas JOIN usuarios ON usuarios.id = matriculas.estudiante_id "
        "WHERE matriculas.grupo_id = ? AND matriculas.estado = 'activa' ORDER BY usuarios.nombre",
        [grupo_id],
    )


def matricula_activa(estudiante_id, anio):
    return consultar_uno(
        "SELECT * FROM matriculas WHERE estudiante_id = ? AND anio = ? AND estado = 'activa'",
        [estudiante_id, anio],
    )


def materias_del_colegio(colegio_id):
    return consultar("SELECT * FROM materias WHERE colegio_id = ? ORDER BY id", [colegio_id])


def asignaciones_del_grupo(grupo_id):
    return consultar(
        "SELECT asignaciones.*, materias.nombre AS materia, materias.corto AS corto, usuarios.nombre AS docente "
        "FROM asignaciones JOIN materias ON materias.id = asignaciones.materia_id "
        "JOIN usuarios ON usuarios.id = asignaciones.docente_id "
        "WHERE asignaciones.grupo_id = ? ORDER BY materias.id",
        [grupo_id],
    )


def asignaciones_del_docente(docente_id, anio):
    return consultar(
        "SELECT asignaciones.*, materias.nombre AS materia, materias.corto AS corto, grupos.nombre AS grupo, "
        "grados.orden AS orden_grado "
        "FROM asignaciones JOIN materias ON materias.id = asignaciones.materia_id "
        "JOIN grupos ON grupos.id = asignaciones.grupo_id JOIN grados ON grados.id = grupos.grado_id "
        "WHERE asignaciones.docente_id = ? AND grupos.anio = ? ORDER BY grados.orden, grupos.nombre, materias.id",
        [docente_id, anio],
    )


def buscar_asignacion(asignacion_id):
    return consultar_uno(
        "SELECT asignaciones.*, materias.nombre AS materia, materias.corto AS corto, grupos.nombre AS grupo, "
        "usuarios.nombre AS docente "
        "FROM asignaciones JOIN materias ON materias.id = asignaciones.materia_id "
        "JOIN grupos ON grupos.id = asignaciones.grupo_id JOIN usuarios ON usuarios.id = asignaciones.docente_id "
        "WHERE asignaciones.id = ?",
        [asignacion_id],
    )


def periodos_del_anio(colegio_id, anio):
    return consultar("SELECT * FROM periodos WHERE colegio_id = ? AND anio = ? ORDER BY numero", [colegio_id, anio])


def notas_del_estudiante(estudiante_id, anio, cantidad_periodos):
    notas = {}
    filas = consultar("SELECT materia_id, periodo, valor FROM notas WHERE estudiante_id = ? AND anio = ?", [estudiante_id, anio])
    for fila in filas:
        if fila["materia_id"] not in notas:
            lista = []
            for p in range(cantidad_periodos):
                lista.append(None)
            notas[fila["materia_id"]] = lista
        if fila["periodo"] >= 1 and fila["periodo"] <= cantidad_periodos:
            notas[fila["materia_id"]][fila["periodo"] - 1] = fila["valor"]
    return notas


def guardar_nota(colegio_id, anio, estudiante_id, materia_id, periodo, valor):
    ejecutar(
        "INSERT OR REPLACE INTO notas (colegio_id, anio, estudiante_id, materia_id, periodo, valor) VALUES (?, ?, ?, ?, ?, ?)",
        [colegio_id, anio, estudiante_id, materia_id, periodo, valor],
    )


def actividades_del_periodo(asignacion_id, anio, periodo):
    return consultar(
        "SELECT * FROM actividades WHERE asignacion_id = ? AND anio = ? AND periodo = ? ORDER BY fecha, id",
        [asignacion_id, anio, periodo],
    )


def buscar_actividad(actividad_id):
    return consultar_uno("SELECT * FROM actividades WHERE id = ?", [actividad_id])


def calificaciones_del_periodo(asignacion_id, anio, periodo):
    tabla = {}
    filas = consultar(
        "SELECT calificaciones.* FROM calificaciones JOIN actividades ON actividades.id = calificaciones.actividad_id "
        "WHERE actividades.asignacion_id = ? AND actividades.anio = ? AND actividades.periodo = ?",
        [asignacion_id, anio, periodo],
    )
    for fila in filas:
        if fila["estudiante_id"] not in tabla:
            tabla[fila["estudiante_id"]] = {}
        tabla[fila["estudiante_id"]][fila["actividad_id"]] = fila
    return tabla


def guardar_calificacion(colegio_id, actividad_id, estudiante_id, valor, observacion, momento):
    ejecutar(
        "INSERT OR REPLACE INTO calificaciones (colegio_id, actividad_id, estudiante_id, valor, observacion, actualizado_en) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [colegio_id, actividad_id, estudiante_id, valor, observacion, momento],
    )


def borrar_actividad(actividad_id):
    ejecutar("DELETE FROM calificaciones WHERE actividad_id = ?", [actividad_id])
    ejecutar("DELETE FROM actividades WHERE id = ?", [actividad_id])


def desempenos_manuales_de(estudiante_id, anio):
    manuales = {}
    for fila in consultar("SELECT materia_id, periodo, desempeno FROM desempenos_manuales WHERE estudiante_id = ? AND anio = ?",
                          [estudiante_id, anio]):
        if fila["materia_id"] not in manuales:
            manuales[fila["materia_id"]] = {}
        manuales[fila["materia_id"]][fila["periodo"]] = fila["desempeno"]
    return manuales


def guardar_desempeno_manual(colegio_id, anio, estudiante_id, materia_id, periodo, desempeno, usuario_id, momento):
    if desempeno is None:
        ejecutar("DELETE FROM desempenos_manuales WHERE anio = ? AND estudiante_id = ? AND materia_id = ? AND periodo = ?",
                 [anio, estudiante_id, materia_id, periodo])
        return
    ejecutar(
        "INSERT OR REPLACE INTO desempenos_manuales (colegio_id, anio, estudiante_id, materia_id, periodo, desempeno, definido_por, definido_en) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [colegio_id, anio, estudiante_id, materia_id, periodo, desempeno, usuario_id, momento],
    )


def estudiantes_a_cargo(acudiente_id):
    return consultar(
        "SELECT usuarios.*, acudientes.parentesco FROM acudientes JOIN usuarios ON usuarios.id = acudientes.estudiante_id "
        "WHERE acudientes.acudiente_id = ? ORDER BY usuarios.nombre",
        [acudiente_id],
    )


def acudientes_de(estudiante_id):
    return consultar(
        "SELECT usuarios.*, acudientes.parentesco FROM acudientes JOIN usuarios ON usuarios.id = acudientes.acudiente_id "
        "WHERE acudientes.estudiante_id = ? ORDER BY usuarios.nombre",
        [estudiante_id],
    )


def registrar(colegio_id, usuario_id, fecha, accion, detalle):
    ejecutar(
        "INSERT INTO registro_accesos (colegio_id, usuario_id, fecha, accion, detalle) VALUES (?, ?, ?, ?, ?)",
        [colegio_id, usuario_id, fecha, accion, detalle],
    )
