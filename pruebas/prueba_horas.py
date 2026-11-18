import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import modulo_horas
import modulo_certificados
import base_datos
from nucleo import hoy
from werkzeug.security import generate_password_hash


def suma(estudiante_id, tipo, estado):
    fila = base_datos.consultar_uno(
        "SELECT SUM(horas) AS total FROM horas_registradas WHERE estudiante_id = ? AND tipo = ? AND estado = ?",
        [estudiante_id, tipo, estado],
    )
    if fila["total"] is None:
        return 0
    return fila["total"]


def pendiente_de(estudiante_id, tipo):
    return base_datos.consultar_uno(
        "SELECT * FROM horas_registradas WHERE estudiante_id = ? AND tipo = ? AND estado = 'pendiente' ORDER BY id",
        [estudiante_id, tipo],
    )


def contar(sql, valores):
    return len(base_datos.consultar(sql, valores))


def crear_usuario(colegio_id, usuario, nombre, rol):
    nuevo_id = base_datos.ejecutar(
        "INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
        [colegio_id, usuario, generate_password_hash("pijao2026"), nombre],
    )
    base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [nuevo_id, rol])
    return nuevo_id


def proyecto_por_nombre(nombre):
    return base_datos.consultar_uno("SELECT * FROM proyectos_sociales WHERE nombre = ?", [nombre])


print("Datos de ejemplo")
revisar("hay 3 proyectos de 2026", contar("SELECT id FROM proyectos_sociales WHERE colegio_id = 1 AND anio = 2026", []) == 3)
revisar("Luisa tiene 82 horas sociales aprobadas", suma(26, "social", "aprobada") == 82)
revisar("Luisa tiene 50 horas constitucionales aprobadas", suma(26, "constitucional", "aprobada") == 50)
revisar("Esteban tiene 64 sociales y 40 constitucionales", suma(23, "social", "aprobada") == 64 and suma(23, "constitucional", "aprobada") == 40)
revisar("Andrés tiene 20 horas sociales", suma(25, "social", "aprobada") == 20)
revisar("hay 3 registros pendientes", contar("SELECT id FROM horas_registradas WHERE estado = 'pendiente'", []) == 3)

pendiente_esteban = pendiente_de(23, "social")
pendiente_andres = pendiente_de(25, "social")
pendiente_constitucional = pendiente_de(23, "constitucional")

print("Permisos de /horas")
estudiante = entrar("esteban.ramirez")
revisar("el estudiante no entra a /horas", destino(estudiante.get("/horas")) == "/inicio")
revisar("la secretaría no entra a /horas", destino(entrar("secretaria").get("/horas")) == "/inicio")
revisar("la acudiente no entra a /horas", destino(entrar("olga.gomez").get("/horas")) == "/inicio")

coordinadora = entrar("coordinadora")
html = coordinadora.get("/horas").get_data(as_text=True)
revisar("la coordinadora ve los tres pendientes",
        "observacion-" + str(pendiente_esteban["id"]) in html and "observacion-" + str(pendiente_andres["id"]) in html
        and "observacion-" + str(pendiente_constitucional["id"]) in html)
revisar("la coordinadora ve los dos grupos", "Grupo 10-A" in html and "Grupo 11-A" in html)
revisar("la coordinadora puede crear proyectos", "Nuevo proyecto pedagógico" in html)
revisar("hay alerta para 11° sin completar", "Alertas de último grado" in html and "Le faltan 16 horas de servicio social" in html)

director = entrar("h.aguirre")
html = director.get("/horas").get_data(as_text=True)
revisar("el director ve su grupo 10-A", "Grupo 10-A" in html and "Melany Osorio" in html)
revisar("el director no ve el grupo 11-A", "Grupo 11-A" not in html and "Esteban Ramírez" not in html)
revisar("el director no ve horas por aprobar", "Horas por aprobar" not in html)

directora = entrar("s.grajales")
html = directora.get("/horas").get_data(as_text=True)
revisar("la responsable de la huerta ve el pendiente de Andrés", "observacion-" + str(pendiente_andres["id"]) in html)
revisar("la responsable de la huerta no ve pendientes de otros proyectos",
        "observacion-" + str(pendiente_esteban["id"]) not in html and "observacion-" + str(pendiente_constitucional["id"]) not in html)

responsable = entrar("j.estrada")
html = responsable.get("/horas").get_data(as_text=True)
revisar("el responsable de alfabetización ve el pendiente de Esteban", "observacion-" + str(pendiente_esteban["id"]) in html)
revisar("el responsable no ve grupos ni el formulario de proyectos", "Grupo 10-A" not in html and "Nuevo proyecto" not in html)

docente = entrar("c.munoz")
respuesta = docente.get("/horas")
revisar("una docente sin proyectos ve un mensaje vacío", respuesta.status_code == 200 and "No tienes proyectos" in respuesta.get_data(as_text=True))
html = entrar("rectora").get("/horas").get_data(as_text=True)
revisar("la rectora ve proyectos pero no los crea", "Huerta escolar y café" in html and "Nuevo proyecto" not in html)

print("Crear y editar proyectos")
formulario = {"accion": "crear_proyecto", "nombre": "Brigada ambiental del río Lejos", "descripcion": "Limpieza y siembra de árboles en la ribera del río.",
              "entidad_aliada": "Alcaldía de Pijao", "lugar": "Ribera del río Lejos", "responsable_id": "9", "cupos": "12"}
respuesta = coordinadora.post("/horas", data=formulario)
revisar("la coordinadora crea un proyecto", "creado" in respuesta.get_data(as_text=True) and proyecto_por_nombre("Brigada ambiental del río Lejos") is not None)
respuesta = coordinadora.post("/horas", data=formulario)
revisar("no deja repetir el nombre en el mismo año", "Ya existe un proyecto" in respuesta.get_data(as_text=True))
malo = {"accion": "crear_proyecto", "nombre": "", "descripcion": "corta", "lugar": "", "responsable_id": "23", "cupos": "0"}
html = coordinadora.post("/horas", data=malo).get_data(as_text=True)
revisar("valida nombre, descripción, lugar, responsable y cupos",
        "entre 5 y 120" in html and "Describe el proyecto" in html and "Escribe el lugar" in html
        and "docente activo" in html and "entre 1 y 200" in html)
revisar("un estudiante no puede ser responsable", proyecto_por_nombre("") is None)
cantidad = contar("SELECT id FROM proyectos_sociales", [])
otro = {"accion": "crear_proyecto", "nombre": "Proyecto de un docente", "descripcion": "Intento de crear sin permiso.",
        "lugar": "Aula", "responsable_id": "10", "cupos": "5"}
revisar("un docente no puede crear proyectos", destino(responsable.post("/horas", data=otro)) == "/inicio"
        and contar("SELECT id FROM proyectos_sociales", []) == cantidad)

revisar("la coordinadora abre el proyecto", "Guardar cambios" in coordinadora.get("/horas/proyecto/1").get_data(as_text=True))
html = responsable.get("/horas/proyecto/1").get_data(as_text=True)
revisar("el responsable ve su proyecto sin editarlo", "Luisa Fernanda Montoya" in html and "Guardar cambios" not in html)
revisar("una docente ajena no ve el proyecto", destino(docente.get("/horas/proyecto/1")) == "/inicio")
edicion = {"nombre": "Huerta escolar y café", "descripcion": "Recuperación de la huerta del colegio con café.",
           "entidad_aliada": "", "lugar": "Huerta del colegio", "responsable_id": "8", "cupos": "2", "activo": "1"}
revisar("el responsable no puede editar", destino(directora.post("/horas/proyecto/2", data=edicion)) == "/inicio")
html = coordinadora.post("/horas/proyecto/2", data=edicion).get_data(as_text=True)
revisar("los cupos no pueden ser menos que los inscritos", "los cupos no pueden ser menos" in html)
edicion["cupos"] = "15"
coordinadora.post("/horas/proyecto/2", data=edicion)
revisar("la coordinadora cambia los cupos", base_datos.consultar_uno("SELECT cupos FROM proyectos_sociales WHERE id = 2", [])["cupos"] == 15)

print("Aprobar y rechazar")
datos = {"accion": "revisar", "registro_id": str(pendiente_andres["id"]), "decision": "aprobada", "observacion": ""}
revisar("el responsable no aprueba horas de otro proyecto", destino(responsable.post("/horas", data=datos)) == "/inicio"
        and pendiente_de(25, "social") is not None)
datos = {"accion": "revisar", "registro_id": str(pendiente_constitucional["id"]), "decision": "aprobada", "observacion": ""}
revisar("el responsable no aprueba horas constitucionales", destino(responsable.post("/horas", data=datos)) == "/inicio")
datos = {"accion": "revisar", "registro_id": str(pendiente_esteban["id"]), "decision": "aprobada", "observacion": "Buen trabajo"}
html = responsable.post("/horas", data=datos).get_data(as_text=True)
revisar("el responsable aprueba horas de su proyecto", "Horas aprobadas" in html and suma(23, "social", "aprobada") == 68)
revisar("guarda quién revisó", base_datos.consultar_uno("SELECT revisado_por FROM horas_registradas WHERE id = ?", [pendiente_esteban["id"]])["revisado_por"] == 10)
html = responsable.post("/horas", data=datos).get_data(as_text=True)
revisar("no se puede revisar dos veces", "ya fue revisado" in html)
datos = {"accion": "revisar", "registro_id": str(pendiente_constitucional["id"]), "decision": "rechazada", "observacion": ""}
html = coordinadora.post("/horas", data=datos).get_data(as_text=True)
revisar("rechazar exige observación", "Escribe una observación" in html and pendiente_de(23, "constitucional") is not None)
datos["observacion"] = "Falta la relatoría firmada"
coordinadora.post("/horas", data=datos)
revisar("la coordinadora rechaza con observación",
        base_datos.consultar_uno("SELECT estado FROM horas_registradas WHERE id = ?", [pendiente_constitucional["id"]])["estado"] == "rechazada")

print("Mis horas")
html = entrar("luisa.montoya").get("/mis-horas").get_data(as_text=True)
codigo_luisa = base_datos.consultar_uno("SELECT codigo FROM certificados WHERE estudiante_id = 26 AND tipo = 'servicio_social'", [])["codigo"]
revisar("Luisa ve requisito cumplido", "Requisito cumplido" in html)
revisar("Luisa ve el enlace a su certificado de servicio social", "/certificados/" + codigo_luisa in html)
html = estudiante.get("/mis-horas").get_data(as_text=True)
revisar("Esteban ve su avance sin requisito cumplido", "68" in html and "Requisito cumplido" not in html)

maria = entrar("maria.valencia")
html = maria.post("/mis-horas", data={"accion": "inscribir", "proyecto_id": "3"}).get_data(as_text=True)
revisar("María se inscribe en un proyecto con cupos", "Quedaste inscrito" in html
        and contar("SELECT id FROM inscripciones_sociales WHERE estudiante_id = 28 AND proyecto_id = 3", []) == 1)
html = maria.post("/mis-horas", data={"accion": "inscribir", "proyecto_id": "3"}).get_data(as_text=True)
revisar("no se inscribe dos veces", "Ya estás inscrito" in html)
coordinadora.post("/horas", data={"accion": "crear_proyecto", "nombre": "Ludoteca para niños", "descripcion": "Juegos y lectura con niños de primaria.",
                                  "lugar": "Biblioteca escolar", "responsable_id": "6", "cupos": "1"})
lleno = proyecto_por_nombre("Ludoteca para niños")
entrar("kevin.largo").post("/mis-horas", data={"accion": "inscribir", "proyecto_id": str(lleno["id"])})
html = maria.post("/mis-horas", data={"accion": "inscribir", "proyecto_id": str(lleno["id"])}).get_data(as_text=True)
revisar("no se inscribe en un proyecto sin cupos", "ya no tiene cupos" in html)
brigada = proyecto_por_nombre("Brigada ambiental del río Lejos")
base_datos.ejecutar("UPDATE proyectos_sociales SET activo = 0 WHERE id = ?", [brigada["id"]])
html = maria.post("/mis-horas", data={"accion": "inscribir", "proyecto_id": str(brigada["id"])}).get_data(as_text=True)
revisar("no se inscribe en un proyecto inactivo", "no está disponible" in html)

registro = {"accion": "registrar", "tipo": "social", "proyecto_id": "3", "fecha": hoy(), "horas": "2,5",
            "actividad": "Organización de la biblioteca infantil", "evidencia": "Fotos y planilla"}
html = maria.post("/mis-horas", data=registro).get_data(as_text=True)
nuevo = pendiente_de(28, "social")
revisar("registra horas sociales pendientes", "Registraste 2,5 horas" in html and nuevo is not None and nuevo["horas"] == 2.5)
registro["horas"] = "6"
html = maria.post("/mis-horas", data=registro).get_data(as_text=True)
revisar("no pasa de 8 horas en un día", "no se pueden pasar de 8" in html)
casos = [
    ["fecha futura", {"fecha": "2099-01-01"}, "no puede ser futura"],
    ["fecha mal escrita", {"fecha": "17/11/2026"}, "AAAA-MM-DD"],
    ["mes imposible", {"fecha": "2026-13-01"}, "AAAA-MM-DD"],
    ["más de 8 horas", {"horas": "9"}, "entre 0,5 y 8"],
    ["menos de media hora", {"horas": "0.2"}, "entre 0,5 y 8"],
    ["horas con letras", {"horas": "dos"}, "entre 0,5 y 8"],
    ["actividad vacía", {"actividad": ""}, "Describe la actividad"],
    ["evidencia vacía", {"evidencia": ""}, "Escribe la evidencia"],
    ["proyecto no inscrito", {"proyecto_id": "1"}, "estés inscrito"],
    ["tipo inválido", {"tipo": "otro"}, "Elige si son horas"],
]
antes = contar("SELECT id FROM horas_registradas WHERE estudiante_id = 28", [])
for caso in casos:
    datos = {"accion": "registrar", "tipo": "social", "proyecto_id": "3", "fecha": "2026-11-10", "horas": "2",
             "actividad": "Apoyo en el taller de lectura", "evidencia": "Planilla firmada"}
    for campo in caso[1]:
        datos[campo] = caso[1][campo]
    html = maria.post("/mis-horas", data=datos).get_data(as_text=True)
    revisar("rechaza " + caso[0], caso[2] in html)
revisar("ningún registro inválido se guardó", contar("SELECT id FROM horas_registradas WHERE estudiante_id = 28", []) == antes)
constitucional = {"accion": "registrar", "tipo": "constitucional", "proyecto_id": "3", "fecha": "2026-11-09", "horas": "3",
                  "actividad": "Taller sobre la acción de tutela", "evidencia": "https://ejemplo.edu.co/taller"}
maria.post("/mis-horas", data=constitucional)
fila = pendiente_de(28, "constitucional")
revisar("las horas constitucionales se guardan sin proyecto", fila is not None and fila["proyecto_id"] is None)

print("Estudiante que no es de Media")
noveno = base_datos.consultar_uno("SELECT id FROM grados WHERE colegio_id = 1 AND nombre = 'Noveno'", [])["id"]
grupo_noveno = base_datos.ejecutar("INSERT INTO grupos (colegio_id, anio, grado_id, sede_id, nombre) VALUES (1, 2026, ?, 1, '9-A')", [noveno])
tomas = crear_usuario(1, "tomas.noveno", "Tomás Noveno Prueba", "estudiante")
base_datos.ejecutar("INSERT INTO matriculas (colegio_id, anio, estudiante_id, grupo_id, fecha_matricula) VALUES (1, 2026, ?, ?, '2026-01-26')",
                    [tomas, grupo_noveno])
cliente_tomas = entrar("tomas.noveno")
html = cliente_tomas.get("/mis-horas").get_data(as_text=True)
revisar("ve que el requisito es en 10° y 11°", "10° y 11°" in html and "Registrar horas" not in html)
cliente_tomas.post("/mis-horas", data={"accion": "registrar", "tipo": "constitucional", "fecha": "2026-11-09", "horas": "2",
                                        "actividad": "Intento de registro", "evidencia": "Ninguna"})
revisar("no puede registrar horas", contar("SELECT id FROM horas_registradas WHERE estudiante_id = ?", [tomas]) == 0)

print("Resumen de un estudiante")
revisar("la madre de Esteban ve sus horas", entrar("olga.gomez").get("/horas/estudiante/23").status_code == 200)
revisar("otra acudiente no ve las horas de Esteban", destino(entrar("gloria.cardenas").get("/horas/estudiante/23")) == "/inicio")
revisar("el director de 10-A no ve a un estudiante de 11-A", destino(director.get("/horas/estudiante/23")) == "/inicio")
revisar("el director de 10-A ve a su estudiante", director.get("/horas/estudiante/13").status_code == 200)
revisar("un estudiante no ve las horas de otro", destino(estudiante.get("/horas/estudiante/26")) == "/inicio")
html = coordinadora.get("/horas/estudiante/26").get_data(as_text=True)
revisar("la coordinadora ve el enlace para emitir el certificado constitucional", "/certificados?estudiante=26" in html)
revisar("la vista es de solo lectura", "Registrar horas" not in html and "Inscribirme" not in html)

print("Aislamiento entre colegios")
otro_colegio = base_datos.ejecutar(
    "INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
    ["Colegio Vecino", "Col. Vecino", "Génova", "Quindío", 2026],
)
docente_vecino = crear_usuario(otro_colegio, "docente.vecino", "Docente Vecino", "docente")
estudiante_vecino = crear_usuario(otro_colegio, "estudiante.vecino", "Estudiante Vecino", "estudiante")
proyecto_vecino = base_datos.ejecutar(
    "INSERT INTO proyectos_sociales (colegio_id, anio, nombre, descripcion, lugar, responsable_id, cupos) VALUES (?, 2026, ?, ?, ?, ?, 10)",
    [otro_colegio, "Proyecto vecino", "Proyecto de otro colegio", "Génova", docente_vecino],
)
registro_vecino = base_datos.ejecutar(
    "INSERT INTO horas_registradas (colegio_id, estudiante_id, tipo, proyecto_id, fecha, horas, actividad, evidencia, registrado_por, registrado_en) "
    "VALUES (?, ?, 'social', ?, '2026-11-01', 4, 'Actividad', 'Fotos', ?, '2026-11-01 10:00')",
    [otro_colegio, estudiante_vecino, proyecto_vecino, estudiante_vecino],
)
revisar("la coordinadora no ve proyectos de otro colegio", destino(coordinadora.get("/horas/proyecto/" + str(proyecto_vecino))) == "/inicio")
revisar("la coordinadora no ve estudiantes de otro colegio", destino(coordinadora.get("/horas/estudiante/" + str(estudiante_vecino))) == "/inicio")
datos = {"accion": "revisar", "registro_id": str(registro_vecino), "decision": "aprobada", "observacion": ""}
revisar("la coordinadora no aprueba horas de otro colegio", destino(coordinadora.post("/horas", data=datos)) == "/inicio"
        and base_datos.consultar_uno("SELECT estado FROM horas_registradas WHERE id = ?", [registro_vecino])["estado"] == "pendiente")
html = maria.post("/mis-horas", data={"accion": "inscribir", "proyecto_id": str(proyecto_vecino)}).get_data(as_text=True)
revisar("un estudiante no se inscribe en proyectos de otro colegio", "no está disponible" in html
        and contar("SELECT id FROM inscripciones_sociales WHERE proyecto_id = ?", [proyecto_vecino]) == 0)
html = coordinadora.get("/horas").get_data(as_text=True)
revisar("el panel no muestra datos de otro colegio", "Proyecto vecino" not in html and "observacion-" + str(registro_vecino) not in html)

ayuda.terminar()
