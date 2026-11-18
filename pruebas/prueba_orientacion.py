import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import modulo_orientacion
import modulo_gobierno
import base_datos
from datetime import date, timedelta
from nucleo import hoy
from werkzeug.security import generate_password_hash


def dia(desplazamiento):
    return (date.fromisoformat(hoy()) + timedelta(days=desplazamiento)).isoformat()


def crear_usuario(colegio_id, usuario, nombre, rol):
    nuevo_id = base_datos.ejecutar(
        "INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
        [colegio_id, usuario, generate_password_hash("pijao2026"), nombre],
    )
    base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [nuevo_id, rol])
    return nuevo_id


def contar(sql, valores):
    return len(base_datos.consultar(sql, valores))


crear_usuario(1, "docente.nuevo", "Docente Sin Grupos", "docente")
otro_colegio = base_datos.ejecutar(
    "INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
    ["Colegio de Prueba", "Prueba", "Génova", "Quindío", 2026],
)
ajeno = crear_usuario(otro_colegio, "estudiante.ajeno", "Estudiante De Otro Colegio", "estudiante")

print("Fechas")
revisar("acepta una fecha bien escrita", modulo_orientacion.fecha_valida("2026-11-17"))
revisar("rechaza fechas con barras", not modulo_orientacion.fecha_valida("2026/11/17"))
revisar("rechaza fechas al revés", not modulo_orientacion.fecha_valida("17-11-2026"))
revisar("rechaza meses imposibles", not modulo_orientacion.fecha_valida("2026-13-01"))
revisar("rechaza letras", not modulo_orientacion.fecha_valida("2026-1a-01"))

print("Datos de ejemplo")
revisar("hay una atención abierta de Andrés", contar("SELECT id FROM atenciones_orientacion WHERE estudiante_id = 25 AND estado = 'abierta'", []) == 1)
revisar("hay una remisión pendiente de c.munoz", contar("SELECT id FROM remisiones_docentes WHERE docente_id = 5 AND estado = 'pendiente'", []) == 1)
revisar("Kevin tiene PIAR con dos materias", contar("SELECT id FROM piar_ajustes WHERE piar_id = 1", []) == 2)

print("Permisos de orientación")
orientadora = entrar("orientadora")
html = orientadora.get("/orientacion").get_data(as_text=True)
revisar("la orientadora ve el panel", "Remisiones de docentes" in html)
revisar("la orientadora ve la remisión y la cita de Andrés", "Andrés Felipe Quintero" in html and "2026-11-24" in html)
html = orientadora.get("/orientacion?buscar=andres").get_data(as_text=True)
revisar("el buscador encuentra sin tildes", "/orientacion/estudiante/25" in html)
html = orientadora.get("/orientacion/estudiante/25").get_data(as_text=True)
revisar("la orientadora ve el historial", "finca" in html and "Nueva atención" in html)

rectora = entrar("rectora")
html = rectora.get("/orientacion").get_data(as_text=True)
revisar("la rectora ve cifras por motivo", "Académico" in html and "Atenciones del año por motivo" in html)
revisar("la rectora no ve nombres ni descripciones", "Quintero" not in html and "finca" not in html and "desmotiv" not in html)
revisar("la rectora no abre el historial", destino(rectora.get("/orientacion/estudiante/25")) == "/inicio")
coordinadora = entrar("coordinadora")
html = coordinadora.get("/orientacion").get_data(as_text=True)
revisar("la coordinadora solo ve cifras", "Remisiones de docentes pendientes" in html and "Quintero" not in html)
revisar("la coordinadora no abre el historial", destino(coordinadora.get("/orientacion/estudiante/25")) == "/inicio")

docente = entrar("c.munoz")
revisar("la docente no entra a orientación", destino(docente.get("/orientacion")) == "/inicio")
revisar("la docente no ve el historial", destino(docente.get("/orientacion/estudiante/25")) == "/inicio")
revisar("la docente no escribe atenciones", destino(docente.post("/orientacion/estudiante/25", data={"accion": "nueva"})) == "/inicio")
for usuario in ["melany.osorio", "gloria.cardenas", "secretaria", "admin", "enfermeria"]:
    revisar(usuario + " no entra a orientación", destino(entrar(usuario).get("/orientacion")) == "/inicio")
revisar("no abre estudiantes de otro colegio", destino(orientadora.get("/orientacion/estudiante/" + str(ajeno))) == "/inicio")
revisar("no abre a un docente como estudiante", destino(orientadora.get("/orientacion/estudiante/5")) == "/inicio")

print("Remisiones de docentes")
html = docente.get("/orientacion/remitir/25").get_data(as_text=True)
revisar("la docente ve el formulario de remisión", "Enviar a orientación" in html)
revisar("la docente no ve nada más de orientación", "desmotiv" not in html and "finca" not in html and "2026-11-24" not in html)
revisar("la docente ve la lista de sus estudiantes", "/orientacion/remitir/13" in docente.get("/orientacion/remitir").get_data(as_text=True))
html = docente.post("/orientacion/remitir/13", data={"motivo": "   "}).get_data(as_text=True)
revisar("la remisión sin motivo da error", "Escribe por qué" in html)
html = docente.post("/orientacion/remitir/13", data={"motivo": "Llora en clase y no quiere salir al descanso."}).get_data(as_text=True)
revisar("la remisión se envía", "fue enviada" in html)
revisar("la remisión queda pendiente", contar("SELECT id FROM remisiones_docentes WHERE estudiante_id = 13 AND docente_id = 5 AND estado = 'pendiente'", []) == 1)
nuevo = entrar("docente.nuevo")
revisar("un docente sin el grupo no remite", destino(nuevo.get("/orientacion/remitir/13")) == "/inicio")
revisar("un docente sin el grupo no envía por POST", destino(nuevo.post("/orientacion/remitir/13", data={"motivo": "x"})) == "/inicio")
revisar("un docente sin grupos no ve la lista", destino(nuevo.get("/orientacion/remitir")) == "/inicio")
revisar("el estudiante no remite", destino(entrar("melany.osorio").get("/orientacion/remitir/14")) == "/inicio")

print("Atenciones")
base = {"accion": "nueva", "fecha": dia(-1), "motivo": "emocional", "descripcion": "Refiere ansiedad antes de los exámenes.",
        "acciones": "Ejercicios de respiración.", "remision": "ninguna", "proxima_cita": dia(6)}
formulario = dict(base)
formulario["descripcion"] = ""
html = orientadora.post("/orientacion/estudiante/13", data=formulario).get_data(as_text=True)
revisar("sin descripción da error", "Escribe la descripción" in html)
formulario = dict(base)
formulario["fecha"] = "2026-13-45"
html = orientadora.post("/orientacion/estudiante/13", data=formulario).get_data(as_text=True)
revisar("una fecha inválida da error", "no es válida" in html)
formulario = dict(base)
formulario["fecha"] = dia(5)
html = orientadora.post("/orientacion/estudiante/13", data=formulario).get_data(as_text=True)
revisar("una fecha futura da error", "no puede ser futura" in html)
formulario = dict(base)
formulario["proxima_cita"] = dia(-3)
html = orientadora.post("/orientacion/estudiante/13", data=formulario).get_data(as_text=True)
revisar("una cita anterior a la atención da error", "debe ser después" in html)
formulario = dict(base)
formulario["motivo"] = "chisme"
formulario["remision"] = "bruja"
html = orientadora.post("/orientacion/estudiante/13", data=formulario).get_data(as_text=True)
revisar("motivo y remisión inventados dan error", "Elige el motivo" in html and "remisión externa válida" in html)
revisar("nada inválido se guardó", contar("SELECT id FROM atenciones_orientacion WHERE estudiante_id = 13", []) == 0)
html = orientadora.post("/orientacion/estudiante/13", data=base).get_data(as_text=True)
revisar("la atención válida se guarda", "Atención registrada" in html)
atencion = base_datos.consultar_uno("SELECT * FROM atenciones_orientacion WHERE estudiante_id = 13", [])
revisar("la atención queda abierta con su cita", atencion is not None and atencion["estado"] == "abierta" and atencion["proxima_cita"] == dia(6))
registros = base_datos.consultar("SELECT detalle FROM registro_accesos", [])
sensible = False
for registro in registros:
    if "ansiedad" in registro["detalle"] or "emocional" in registro["detalle"] or "Llora" in registro["detalle"]:
        sensible = True
revisar("el registro de accesos no guarda datos sensibles", not sensible)

remision = base_datos.consultar_uno("SELECT id FROM remisiones_docentes WHERE estudiante_id = 13", [])
html = orientadora.post("/orientacion/estudiante/25", data={"accion": "remision_atendida", "remision_id": str(remision["id"])}).get_data(as_text=True)
revisar("no marca la remisión desde otro estudiante", "No se encontró la remisión" in html)
orientadora.post("/orientacion/estudiante/13", data={"accion": "remision_atendida", "remision_id": str(remision["id"])})
revisar("la remisión queda atendida", base_datos.consultar_uno("SELECT estado FROM remisiones_docentes WHERE id = ?", [remision["id"]])["estado"] == "atendida")
html = orientadora.post("/orientacion/estudiante/25", data={"accion": "cerrar", "atencion_id": str(atencion["id"])}).get_data(as_text=True)
revisar("no cierra la atención desde otro estudiante", "No se encontró la atención" in html)
orientadora.post("/orientacion/estudiante/13", data={"accion": "cerrar", "atencion_id": str(atencion["id"])})
revisar("la atención se cierra", base_datos.consultar_uno("SELECT estado FROM atenciones_orientacion WHERE id = ?", [atencion["id"]])["estado"] == "cerrada")
html = rectora.get("/orientacion").get_data(as_text=True)
revisar("la rectora no ve la nueva atención por nombre", "Melany" not in html and "ansiedad" not in html)

print("PIAR: permisos")
revisar("la rectora no ve PIAR", destino(rectora.get("/piar")) == "/inicio")
revisar("la secretaria no ve PIAR", destino(entrar("secretaria").get("/piar/1")) == "/inicio")
html = docente.get("/piar").get_data(as_text=True)
revisar("la docente ve el PIAR de su estudiante", "Kevin Stiven Largo" in html)
html = docente.get("/piar/1").get_data(as_text=True)
revisar("la docente edita su materia", 'name="materia_id" value="1"' in html)
revisar("la docente no edita otras materias", 'name="materia_id" value="2"' not in html and 'value="general"' not in html)
html = nuevo.get("/piar").get_data(as_text=True)
revisar("un docente sin el grupo no ve el PIAR en la lista", "Kevin" not in html)
revisar("un docente sin el grupo no abre el PIAR", destino(nuevo.get("/piar/1")) == "/inicio")
kevin = entrar("kevin.largo")
html = kevin.get("/piar/1").get_data(as_text=True)
revisar("el estudiante ve su PIAR", "Kevin Stiven Largo" in html and "Ajustes razonables" in html)
revisar("el estudiante lo ve en solo lectura", "<textarea" not in html and "Revisé el PIAR" not in html)
revisar("el estudiante ve su PIAR en la lista", "/piar/1" in kevin.get("/piar").get_data(as_text=True))
maria = entrar("maria.valencia")
revisar("otro estudiante no abre el PIAR", destino(maria.get("/piar/1")) == "/inicio")
revisar("otro estudiante no lo ve en la lista", "Kevin" not in maria.get("/piar").get_data(as_text=True))
madre = entrar("gloria.cardenas")
revisar("una acudiente ajena no abre el PIAR", destino(madre.get("/piar/1")) == "/inicio")

print("PIAR: edición")
ajuste = {"accion": "ajuste", "materia_id": "1", "objetivo": "Resolver sistemas 2x2.", "ajustes": "Guías por pasos.",
          "evaluacion": "Oral.", "seguimiento": "Avanza."}
html = docente.post("/piar/1", data=ajuste).get_data(as_text=True)
revisar("la docente guarda su ajuste", "guardados" in html)
revisar("el ajuste de Matemáticas cambió", base_datos.consultar_uno("SELECT objetivo FROM piar_ajustes WHERE piar_id = 1 AND materia_id = 1", [])["objetivo"] == "Resolver sistemas 2x2.")
otro = dict(ajuste)
otro["materia_id"] = "2"
revisar("la docente no guarda el ajuste de Castellano", destino(docente.post("/piar/1", data=otro)) == "/inicio")
revisar("el ajuste de Castellano no cambió", base_datos.consultar_uno("SELECT objetivo FROM piar_ajustes WHERE piar_id = 1 AND materia_id = 2", [])["objetivo"] != "Resolver sistemas 2x2.")
revisar("la docente no edita la información general", destino(docente.post("/piar/1", data={"accion": "general", "descripcion_estudiante": "x"})) == "/inicio")
vacio = dict(ajuste)
vacio["objetivo"] = ""
revisar("un ajuste sin objetivo da error", "al menos el objetivo" in docente.post("/piar/1", data=vacio).get_data(as_text=True))
aguirre = entrar("h.aguirre")
html = aguirre.get("/piar/1").get_data(as_text=True)
revisar("el docente de Sociales edita Sociales y Filosofía", 'name="materia_id" value="5"' in html and 'name="materia_id" value="6"' in html and 'name="materia_id" value="1"' not in html)
revisar("el estudiante no edita su PIAR", destino(kevin.post("/piar/1", data=ajuste)) == "/inicio")
revisar("el estudiante no marca revisado", destino(kevin.post("/piar/1", data={"accion": "revisado"})) == "/inicio")

print("PIAR: creación y revisión de la familia")
crear = {"estudiante_id": "13", "descripcion_estudiante": "Melany es líder y muy organizada.", "barreras": "Baja visión.", "apoyos_familia": "Control con optometría."}
revisar("la docente no crea PIAR", destino(docente.post("/piar", data=crear)) == "/inicio")
sin_descripcion = dict(crear)
sin_descripcion["descripcion_estudiante"] = ""
html = orientadora.post("/piar", data=sin_descripcion).get_data(as_text=True)
revisar("sin descripción no se crea", "Escribe la descripción del estudiante" in html)
ajeno_form = dict(crear)
ajeno_form["estudiante_id"] = str(ajeno)
revisar("no crea PIAR a estudiantes de otro colegio", "Elige un estudiante del colegio" in orientadora.post("/piar", data=ajeno_form).get_data(as_text=True))
respuesta = orientadora.post("/piar", data=crear)
nuevo_plan = base_datos.consultar_uno("SELECT * FROM piar WHERE estudiante_id = 13", [])
revisar("la orientadora crea el PIAR", nuevo_plan is not None and destino(respuesta) == "/piar/" + str(nuevo_plan["id"]) + "?creado=1")
repetido = dict(crear)
repetido["estudiante_id"] = "27"
revisar("no se crea un segundo PIAR el mismo año", "ya tiene PIAR" in orientadora.post("/piar", data=repetido).get_data(as_text=True))
ruta = "/piar/" + str(nuevo_plan["id"])
html = madre.get(ruta).get_data(as_text=True)
revisar("la acudiente ve el PIAR de su hija", "Melany es líder" in html and "Revisé el PIAR" in html)
revisar("la acudiente lo ve en la lista", ruta in madre.get("/piar").get_data(as_text=True))
revisar("la acudiente no edita", destino(madre.post(ruta, data={"accion": "general", "descripcion_estudiante": "x"})) == "/inicio")
html = madre.post(ruta, data={"accion": "revisado"}).get_data(as_text=True)
revisar("la acudiente marca revisado", "revisaste el PIAR" in html)
revisar("queda la fecha de revisión", base_datos.consultar_uno("SELECT revisado_acudiente_en FROM piar WHERE id = ?", [nuevo_plan["id"]])["revisado_acudiente_en"] != "")
html = coordinadora.post(ruta, data={"accion": "general", "descripcion_estudiante": "Melany lidera el grupo.", "barreras": "Baja visión.", "apoyos_familia": ""}).get_data(as_text=True)
revisar("la coordinadora edita la información general", "guardada" in html)
html = coordinadora.post(ruta, data={"accion": "ajuste", "materia_id": "3", "objetivo": "Leer textos cortos.", "ajustes": "Letra grande.", "evaluacion": "", "seguimiento": ""}).get_data(as_text=True)
revisar("la coordinadora edita cualquier materia", "Ajustes de Inglés guardados" in html)
html = coordinadora.post(ruta, data={"accion": "ajuste", "materia_id": "99", "objetivo": "a", "ajustes": "b"}).get_data(as_text=True)
revisar("una materia que no es del grupo da error", "no es del grupo" in html)

ayuda.terminar()
