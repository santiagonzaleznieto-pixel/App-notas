import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import modulo_asistencia
import modulo_observador
import base_datos
import nucleo
from datetime import date, timedelta
from werkzeug.security import generate_password_hash


def hoy_de_prueba():
    return "2026-11-17"


nucleo.hoy = hoy_de_prueba


def contar(sql, valores):
    return base_datos.consultar_uno("SELECT COUNT(*) AS total FROM " + sql, valores)["total"]


def estado_de(asignacion_id, estudiante_id, fecha):
    fila = base_datos.consultar_uno("SELECT estado FROM asistencia WHERE asignacion_id = ? AND estudiante_id = ? AND fecha = ?",
                                    [asignacion_id, estudiante_id, fecha])
    if fila is None:
        return None
    return fila["estado"]


def lista_de_10a(fecha):
    formulario = {"fecha": fecha}
    for estudiante_id in range(13, 23):
        formulario["estado-" + str(estudiante_id)] = "presente"
    return formulario


def poner_fallas(asignacion_id, estudiante_id, desde, hasta):
    dia = date.fromisoformat(desde)
    while dia <= date.fromisoformat(hasta):
        if dia.weekday() < 5:
            base_datos.ejecutar(
                "INSERT OR REPLACE INTO asistencia (colegio_id, fecha, asignacion_id, estudiante_id, estado, registrado_por, registrado_en) "
                "VALUES (1, ?, ?, ?, 'falla', 5, ?)",
                [dia.isoformat(), asignacion_id, estudiante_id, dia.isoformat() + " 07:00"],
            )
        dia = dia + timedelta(days=1)


print("Datos de ejemplo")
revisar("hay 90 registros de Matemáticas 10-A (9 días hábiles)", contar("asistencia WHERE asignacion_id = 1", []) == 90)
revisar("hay 90 registros de Sociales 10-A", contar("asistencia WHERE asignacion_id = 5", []) == 90)
revisar("Juan Pablo tiene 3 fallas", contar("asistencia WHERE estudiante_id = 14 AND estado = 'falla'", []) == 3)
revisar("Melany tiene 1 falla", contar("asistencia WHERE estudiante_id = 13 AND estado = 'falla'", []) == 1)
revisar("hay una excusa pendiente de Melany", contar("excusas WHERE estudiante_id = 13 AND estado = 'pendiente'", []) == 1)
revisar("la excusa la envió gloria.cardenas", base_datos.consultar_uno("SELECT enviada_por FROM excusas WHERE id = 1", [])["enviada_por"] == 29)

print("Permisos")
anonimo = ayuda.app.test_client()
revisar("sin sesión no se entra a asistencia", destino(anonimo.get("/asistencia")) == "/inicio")
docente = entrar("c.munoz")
respuesta = docente.get("/asistencia")
html = respuesta.get_data(as_text=True)
revisar("la docente ve sus clases", respuesta.status_code == 200 and "Tomar lista" in html and "Matemáticas" in html)
revisar("la docente no ve excusas pendientes", "Excusas por revisar" not in html)
revisar("la docente abre la lista de su clase", docente.get("/asistencia/tomar/1").status_code == 200)
revisar("la docente no toma lista en clases ajenas", destino(docente.get("/asistencia/tomar/5")) == "/inicio")
revisar("la docente no ve la asistencia del grupo", destino(docente.get("/asistencia/grupo/1")) == "/inicio")
revisar("la docente no revisa excusas", destino(docente.get("/asistencia/excusas")) == "/inicio")
revisar("la docente no ve la asistencia de un estudiante", destino(docente.get("/asistencia/estudiante/13")) == "/inicio")
director = entrar("h.aguirre")
html = director.get("/asistencia").get_data(as_text=True)
revisar("el director ve su grupo y las excusas", "/asistencia/grupo/1" in html and "Excusas por revisar" in html)
revisar("el director no ve el grupo ajeno en la lista", "/asistencia/grupo/2" not in html)
revisar("el director ve la asistencia de su grupo", director.get("/asistencia/grupo/1").status_code == 200)
revisar("el director no ve la asistencia de otro grupo", destino(director.get("/asistencia/grupo/2")) == "/inicio")
revisar("el director no ve estudiantes de otro grupo", destino(director.get("/asistencia/estudiante/23")) == "/inicio")
estudiante = entrar("melany.osorio")
revisar("la estudiante no entra al tablero de asistencia", destino(estudiante.get("/asistencia")) == "/inicio")
revisar("mi asistencia lleva a su página", destino(estudiante.get("/mi-asistencia")) == "/asistencia/estudiante/13")
revisar("la estudiante ve su asistencia", estudiante.get("/asistencia/estudiante/13").status_code == 200)
revisar("la estudiante no ve la de un compañero", destino(estudiante.get("/asistencia/estudiante/14")) == "/inicio")
revisar("la estudiante no toma lista", destino(estudiante.get("/asistencia/tomar/1")) == "/inicio")
revisar("la estudiante no ve el formulario de excusas", "Enviar excusa" not in estudiante.get("/asistencia/estudiante/13").get_data(as_text=True))
madre = entrar("gloria.cardenas")
respuesta = madre.get("/asistencia/estudiante/13")
revisar("la acudiente ve la asistencia de su hija y el formulario", respuesta.status_code == 200 and "Enviar excusa" in respuesta.get_data(as_text=True))
revisar("la acudiente no ve otros estudiantes", destino(madre.get("/asistencia/estudiante/14")) == "/inicio")
revisar("la acudiente no entra al tablero", destino(madre.get("/asistencia")) == "/inicio")
coordinadora = entrar("coordinadora")
html = coordinadora.get("/asistencia").get_data(as_text=True)
revisar("la coordinadora ve todos los grupos", "/asistencia/grupo/1" in html and "/asistencia/grupo/2" in html)
orientadora = entrar("orientadora")
revisar("la orientadora ve el tablero", orientadora.get("/asistencia").status_code == 200)
revisar("la orientadora no revisa excusas", destino(orientadora.get("/asistencia/excusas")) == "/inicio")

print("Tomar lista")
formulario = lista_de_10a("2026-11-18")
html = docente.post("/asistencia/tomar/1", data=formulario).get_data(as_text=True)
revisar("no acepta fechas futuras", "todavía no llega" in html and contar("asistencia WHERE fecha = '2026-11-18'", []) == 0)
html = docente.post("/asistencia/tomar/1", data=lista_de_10a("2026-01-10")).get_data(as_text=True)
revisar("no acepta fechas fuera del año escolar", "año escolar" in html and contar("asistencia WHERE fecha = '2026-01-10'", []) == 0)
html = docente.post("/asistencia/tomar/1", data=lista_de_10a("17/11/2026")).get_data(as_text=True)
revisar("no acepta fechas mal escritas", "AAAA-MM-DD" in html)
html = docente.post("/asistencia/tomar/1", data=lista_de_10a("2026-02-30")).get_data(as_text=True)
revisar("no acepta fechas que no existen", "AAAA-MM-DD" in html)
html = docente.get("/asistencia/tomar/1?fecha=2026-12-24").get_data(as_text=True)
revisar("al abrir una fecha futura muestra el error y no el formulario", "todavía no llega" in html and "Guardar lista" not in html)
formulario = lista_de_10a("2026-11-17")
formulario["estado-14"] = "dormido"
html = docente.post("/asistencia/tomar/1", data=formulario).get_data(as_text=True)
revisar("un estado inválido da error", "elige Presente, Falla o Retardo" in html)
revisar("con errores no se guarda nada", contar("asistencia WHERE asignacion_id = 1 AND fecha = '2026-11-17'", []) == 0)
formulario = lista_de_10a("2026-11-17")
formulario["estado-14"] = "falla"
formulario["estado-15"] = "retardo"
formulario["estado-23"] = "falla"
html = docente.post("/asistencia/tomar/1", data=formulario).get_data(as_text=True)
revisar("guarda la lista", "Lista del 2026-11-17 guardada" in html)
revisar("guarda un registro por estudiante del grupo", contar("asistencia WHERE asignacion_id = 1 AND fecha = '2026-11-17'", []) == 10)
revisar("guarda la falla", estado_de(1, 14, "2026-11-17") == "falla")
revisar("guarda el retardo", estado_de(1, 15, "2026-11-17") == "retardo")
revisar("ignora estudiantes de otro grupo en el formulario", estado_de(1, 23, "2026-11-17") is None)
html = docente.get("/asistencia/tomar/1?fecha=2026-11-17").get_data(as_text=True)
revisar("al volver muestra lo guardado", 'name="estado-15" value="retardo" checked' in html)
revisar("por defecto marca presente", 'name="estado-13" value="presente" checked' in html)
revisar("el tablero muestra la lista de hoy tomada", "Tomada" in docente.get("/asistencia").get_data(as_text=True))
formulario["estado-14"] = "presente"
docente.post("/asistencia/tomar/1", data=formulario)
revisar("volver a tomar lista no duplica", contar("asistencia WHERE asignacion_id = 1 AND fecha = '2026-11-17'", []) == 10)
revisar("volver a tomar lista corrige el estado", estado_de(1, 14, "2026-11-17") == "presente")
docente.post("/asistencia/tomar/1", data={"fecha": "2026-11-17", "accion": "todos", "estado-15": "retardo"})
revisar("todos presentes deja a todos en presente",
        contar("asistencia WHERE asignacion_id = 1 AND fecha = '2026-11-17' AND estado != 'presente'", []) == 0)
otro_formulario = lista_de_10a("2026-11-17")
otro_formulario["estado-13"] = "falla"
revisar("otro docente no puede guardar en esta clase", destino(director.post("/asistencia/tomar/1", data=otro_formulario)) == "/inicio")
revisar("la lista no cambió", estado_de(1, 13, "2026-11-17") == "presente")

print("Excusas")
excusa_valida = {"fecha_inicio": "2026-11-16", "fecha_fin": "2026-11-17", "motivo": "Gripa con fiebre. Fue al centro de salud."}
revisar("la estudiante no puede enviar excusas", destino(estudiante.post("/asistencia/estudiante/13", data=excusa_valida)) == "/inicio")
revisar("no se creó la excusa de la estudiante", contar("excusas WHERE estudiante_id = 13", []) == 1)
html = madre.post("/asistencia/estudiante/13", data={"fecha_inicio": "2026-11-17", "fecha_fin": "2026-11-16", "motivo": "Gripa"}).get_data(as_text=True)
revisar("la fecha final no puede ser anterior", "anterior a la fecha inicial" in html)
html = madre.post("/asistencia/estudiante/13", data={"fecha_inicio": "2026-10-01", "fecha_fin": "2026-10-02", "motivo": "Gripa"}).get_data(as_text=True)
revisar("no recibe excusas de hace más de 30 días", "últimos 30 días" in html)
html = madre.post("/asistencia/estudiante/13", data={"fecha_inicio": "16-11-2026", "fecha_fin": "2026-11-17", "motivo": "Gripa"}).get_data(as_text=True)
revisar("las fechas deben ser válidas", "AAAA-MM-DD" in html)
html = madre.post("/asistencia/estudiante/13", data={"fecha_inicio": "2026-11-16", "fecha_fin": "2026-11-17", "motivo": "  "}).get_data(as_text=True)
revisar("el motivo es obligatorio", "Escribe el motivo" in html)
revisar("con errores no se guarda la excusa", contar("excusas WHERE estudiante_id = 13", []) == 1)
respuesta = madre.post("/asistencia/estudiante/13", data=excusa_valida)
revisar("la acudiente envía una excusa", "enviada=1" in destino(respuesta))
revisar("la excusa queda pendiente", contar("excusas WHERE estudiante_id = 13 AND estado = 'pendiente' AND enviada_por = 29", []) == 2)
revisar("la acudiente no envía excusas de otros estudiantes", destino(madre.post("/asistencia/estudiante/14", data=excusa_valida)) == "/inicio")
directora_once = entrar("s.grajales")
html = directora_once.get("/asistencia/excusas").get_data(as_text=True)
revisar("la directora de 11-A no ve excusas de 10-A", "Melany" not in html)
html = directora_once.post("/asistencia/excusas", data={"excusa_id": "1", "accion": "aprobar"}).get_data(as_text=True)
revisar("la directora de 11-A no puede aprobarla", "no te corresponde" in html)
revisar("la excusa sigue pendiente", base_datos.consultar_uno("SELECT estado FROM excusas WHERE id = 1", [])["estado"] == "pendiente")
revisar("el director de 10-A ve la excusa de Melany", "Melany" in director.get("/asistencia/excusas").get_data(as_text=True))
html = coordinadora.post("/asistencia/excusas", data={"excusa_id": "1", "accion": "rechazar", "respuesta": ""}).get_data(as_text=True)
revisar("rechazar exige una respuesta", "motivo del rechazo" in html)
html = coordinadora.post("/asistencia/excusas", data={"excusa_id": "1", "accion": "borrar"}).get_data(as_text=True)
revisar("una acción inválida da error", "Elige si apruebas" in html)
html = coordinadora.post("/asistencia/excusas", data={"excusa_id": "abc", "accion": "aprobar"}).get_data(as_text=True)
revisar("un id inválido da error", "no existe" in html)
html = coordinadora.post("/asistencia/excusas", data={"excusa_id": "1", "accion": "aprobar", "respuesta": "Constancia recibida."}).get_data(as_text=True)
revisar("la coordinadora aprueba la excusa", "Fallas justificadas: 1" in html)
revisar("la excusa queda aprobada", base_datos.consultar_uno("SELECT estado, revisada_por FROM excusas WHERE id = 1", [])["revisada_por"] == 3)
revisar("aprobar convierte la falla en excusa", estado_de(1, 13, "2026-11-10") == "excusa")
revisar("Melany queda sin fallas sin excusa", contar("asistencia WHERE estudiante_id = 13 AND estado = 'falla'", []) == 0)
html = coordinadora.post("/asistencia/excusas", data={"excusa_id": "1", "accion": "aprobar"}).get_data(as_text=True)
revisar("no se revisa dos veces", "ya fue revisada" in html)
formulario = lista_de_10a("2026-11-10")
formulario["estado-13"] = "falla"
docente.post("/asistencia/tomar/1", data=formulario)
revisar("con excusa aprobada la falla se guarda como excusa", estado_de(1, 13, "2026-11-10") == "excusa")
html = director.post("/asistencia/excusas", data={"excusa_id": "2", "accion": "rechazar", "respuesta": "No llegó la constancia médica."}).get_data(as_text=True)
revisar("el director rechaza la excusa de su estudiante", "rechazada" in html)
revisar("la excusa queda rechazada", base_datos.consultar_uno("SELECT estado FROM excusas WHERE id = 2", [])["estado"] == "rechazada")
html = madre.get("/asistencia/estudiante/13").get_data(as_text=True)
revisar("la acudiente ve el estado de sus excusas", "Aprobada" in html and "Rechazada" in html and "No llegó la constancia" in html)

print("Alertas")
revisar("fecha válida", modulo_asistencia.fecha_valida("2028-02-29"))
revisar("2026 no es bisiesto", not modulo_asistencia.fecha_valida("2026-02-29"))
revisar("el mes 13 no existe", not modulo_asistencia.fecha_valida("2026-13-01"))
revisar("la fecha debe tener guiones", not modulo_asistencia.fecha_valida("2026/11/17"))
registros = [
    {"fecha": "2026-11-16", "estado": "falla"},
    {"fecha": "2026-11-13", "estado": "falla"},
    {"fecha": "2026-11-13", "estado": "falla"},
    {"fecha": "2026-11-12", "estado": "presente"},
]
continua = modulo_asistencia.inasistencia_continua(registros)
revisar("cuenta días calendario entre listas (viernes a lunes = 4)", continua["dias"] == 4 and continua["vigente"])
registros = [
    {"fecha": "2026-11-16", "estado": "falla"},
    {"fecha": "2026-11-16", "estado": "presente"},
    {"fecha": "2026-11-13", "estado": "falla"},
    {"fecha": "2026-11-12", "estado": "excusa"},
    {"fecha": "2026-11-11", "estado": "falla"},
]
continua = modulo_asistencia.inasistencia_continua(registros)
revisar("un día con alguna clase asistida o con excusa corta la cadena", continua["dias"] == 1 and continua["hasta"] == "2026-11-13")
revisar("sin fallas no hay inasistencia continua", modulo_asistencia.inasistencia_continua([{"fecha": "2026-11-16", "estado": "presente"}])["dias"] == 0)
html = director.get("/asistencia/grupo/1").get_data(as_text=True)
revisar("alerta de 3 fallas sin excusa en 30 días", "3 fallas sin excusa en los últimos 30 días" in html)
poner_fallas(7, 15, "2026-10-05", "2026-10-16")
html = director.get("/asistencia/grupo/1").get_data(as_text=True)
revisar("marca los 10 días de inasistencia continua", "12 días calendario de inasistencia continua" in html and "Pasó los 10 días" in html)
revisar("avisa que ya volvió a clase", "Ya volvió a clase" in html)
poner_fallas(9, 27, "2026-10-13", "2026-11-17")
html = directora_once.get("/asistencia/grupo/2").get_data(as_text=True)
revisar("marca más de 30 días y el retiro del SIMAT", "36 días calendario" in html and "Supera los 30 días" in html and "SIMAT" in html)
revisar("el tablero cuenta estudiantes con alertas", "Con alertas" in directora_once.get("/asistencia").get_data(as_text=True))
html = entrar("jorge.restrepo").get("/asistencia/estudiante/14").get_data(as_text=True)
revisar("el acudiente ve la alerta de su hijo", "3 fallas sin excusa" in html)

print("Aislamiento entre colegios")
otro = base_datos.ejecutar("INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
                           ["Colegio de prueba", "Col. prueba", "Génova", "Quindío", 2026])
sede = base_datos.ejecutar("INSERT INTO sedes (colegio_id, nombre, jornada) VALUES (?, ?, ?)", [otro, "Principal", "Mañana"])
grado = base_datos.ejecutar("INSERT INTO grados (colegio_id, nombre, nivel, orden) VALUES (?, ?, ?, ?)", [otro, "Sexto", "Básica secundaria", 6])
clave = generate_password_hash("pijao2026")
profe = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
                            [otro, "profe.otro", clave, "Profesor de otro colegio"])
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [profe, "docente"])
alumno = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
                             [otro, "alumno.otro", clave, "Alumno de otro colegio"])
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [alumno, "estudiante"])
grupo_otro = base_datos.ejecutar("INSERT INTO grupos (colegio_id, anio, grado_id, sede_id, nombre, director_id) VALUES (?, ?, ?, ?, ?, ?)",
                                 [otro, 2026, grado, sede, "6-A", profe])
base_datos.ejecutar("INSERT INTO matriculas (colegio_id, anio, estudiante_id, grupo_id, fecha_matricula) VALUES (?, ?, ?, ?, ?)",
                    [otro, 2026, alumno, grupo_otro, "2026-01-26"])
materia_otra = base_datos.ejecutar("INSERT INTO materias (colegio_id, nombre, corto) VALUES (?, ?, ?)", [otro, "Matemáticas", "Mat"])
asignacion_otra = base_datos.ejecutar("INSERT INTO asignaciones (colegio_id, grupo_id, materia_id, docente_id) VALUES (?, ?, ?, ?)",
                                      [otro, grupo_otro, materia_otra, profe])
excusa_otra = base_datos.ejecutar(
    "INSERT INTO excusas (colegio_id, estudiante_id, fecha_inicio, fecha_fin, motivo, enviada_por, enviada_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
    [otro, alumno, "2026-11-16", "2026-11-16", "Prueba de otro colegio", profe, "2026-11-16 08:00"],
)
revisar("la coordinadora no ve estudiantes de otro colegio", destino(coordinadora.get("/asistencia/estudiante/" + str(alumno))) == "/inicio")
revisar("la coordinadora no ve grupos de otro colegio", destino(coordinadora.get("/asistencia/grupo/" + str(grupo_otro))) == "/inicio")
html = coordinadora.get("/asistencia/excusas").get_data(as_text=True)
revisar("la coordinadora no ve excusas de otro colegio", "Prueba de otro colegio" not in html)
html = coordinadora.post("/asistencia/excusas", data={"excusa_id": str(excusa_otra), "accion": "aprobar"}).get_data(as_text=True)
revisar("la coordinadora no aprueba excusas de otro colegio",
        "no existe" in html and base_datos.consultar_uno("SELECT estado FROM excusas WHERE id = ?", [excusa_otra])["estado"] == "pendiente")
profe_otro = entrar("profe.otro")
revisar("el docente de otro colegio no toma lista en el piloto", destino(profe_otro.get("/asistencia/tomar/1")) == "/inicio")
revisar("el docente de otro colegio no ve grupos del piloto", destino(profe_otro.get("/asistencia/grupo/1")) == "/inicio")
revisar("el docente de otro colegio no ve estudiantes del piloto", destino(profe_otro.get("/asistencia/estudiante/13")) == "/inicio")
revisar("el docente de otro colegio no ve excusas del piloto", "Melany" not in profe_otro.get("/asistencia/excusas").get_data(as_text=True))
profe_otro.post("/asistencia/tomar/" + str(asignacion_otra), data={"fecha": "2026-11-17", "estado-" + str(alumno): "falla"})
revisar("el otro colegio guarda su propia lista", contar("asistencia WHERE colegio_id = ? AND estudiante_id = ? AND estado = 'falla'", [otro, alumno]) == 1)

ayuda.terminar()
