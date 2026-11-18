import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import modulo_orientacion
import modulo_gobierno
import base_datos
from werkzeug.security import generate_password_hash


def contar(sql, valores):
    return len(base_datos.consultar(sql, valores))


def columnas(tabla):
    lista = []
    if base_datos.usa_postgres():
        filas = base_datos.consultar("SELECT column_name AS name FROM information_schema.columns WHERE table_name = ?", [tabla])
    else:
        filas = base_datos.consultar("PRAGMA table_info(" + tabla + ")", [])
    for fila in filas:
        lista.append(fila["name"])
    return lista


def votos_de(eleccion_id):
    return contar("SELECT id FROM votos WHERE eleccion_id = ?", [eleccion_id])


def votantes_de(eleccion_id):
    return contar("SELECT id FROM votantes WHERE eleccion_id = ?", [eleccion_id])


def candidato(eleccion_id, estudiante_id):
    fila = base_datos.consultar_uno("SELECT id FROM candidatos WHERE eleccion_id = ? AND estudiante_id = ?", [eleccion_id, estudiante_id])
    if fila is None:
        return ""
    return str(fila["id"])


otro_colegio = base_datos.ejecutar(
    "INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
    ["Colegio de Prueba", "Prueba", "Génova", "Quindío", 2026],
)
ajeno = base_datos.ejecutar(
    "INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
    [otro_colegio, "estudiante.ajeno", generate_password_hash("pijao2026"), "Estudiante Ajeno"],
)
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, 'estudiante')", [ajeno])
eleccion_ajena = base_datos.ejecutar(
    "INSERT INTO elecciones (colegio_id, anio, cargo, titulo, apertura, cierre, estado) VALUES (?, 2026, 'personero', ?, ?, ?, 'cerrada')",
    [otro_colegio, "Personero de otro colegio", "2026-03-01 07:00", "2026-03-01 12:00"],
)

print("Fechas y horas")
revisar("acepta fecha y hora bien escritas", modulo_gobierno.fecha_hora_valida("2031-05-10 07:00"))
revisar("rechaza horas imposibles", not modulo_gobierno.fecha_hora_valida("2031-05-10 25:00"))
revisar("rechaza el texto sin hora", not modulo_gobierno.fecha_hora_valida("2031-05-10"))
revisar("rechaza meses imposibles", not modulo_gobierno.fecha_hora_valida("2031-15-10 07:00"))

print("Voto secreto en la base de datos")
revisar("la tabla votos no guarda quién votó ni la hora", columnas("votos") == ["id", "colegio_id", "eleccion_id", "candidato_id"])
revisar("la tabla votantes no guarda por quién votó", "candidato_id" not in columnas("votantes"))

print("Datos de ejemplo")
revisar("la elección de personero tiene 13 votos y 13 votantes", votos_de(1) == 13 and votantes_de(1) == 13)
revisar("hay 2 candidatos a representante de 10-A en preparación", contar("SELECT id FROM candidatos WHERE eleccion_id = 2", []) == 2)
revisar("los ids de los votos no siguen el orden de los votantes", base_datos.consultar_uno("SELECT MIN(id) AS menor FROM votos", [])["menor"] >= 100000000000)

print("Permisos")
for usuario in ["c.munoz", "gloria.cardenas", "secretaria", "tesoreria"]:
    revisar(usuario + " no entra a elecciones", destino(entrar(usuario).get("/elecciones")) == "/inicio")
melany = entrar("melany.osorio")
html = melany.get("/elecciones").get_data(as_text=True)
revisar("la estudiante ve sus elecciones", "Personero estudiantil 2026" in html and "Representante de grupo 10-A" in html)
revisar("la estudiante ve el ganador de la cerrada", "Luisa Fernanda Montoya" in html and "Próximamente" in html)
revisar("la estudiante no ve el formulario de directivos", "Nueva elección" not in html)
esteban = entrar("esteban.ramirez")
revisar("un estudiante de 11-A no ve la elección de 10-A", "Representante de grupo 10-A" not in esteban.get("/elecciones").get_data(as_text=True))
html = melany.get("/elecciones/1").get_data(as_text=True)
revisar("los resultados cerrados son públicos", "Ganó la elección" in html and "Luisa Fernanda Montoya" in html)
revisar("una docente ve resultados cerrados", entrar("c.munoz").get("/elecciones/1").status_code == 200)
revisar("la estudiante no ve resultados en preparación", destino(melany.get("/elecciones/2")) == "/inicio")
revisar("la estudiante no gestiona elecciones", destino(melany.post("/elecciones", data={"accion": "abrir", "eleccion_id": "2"})) == "/inicio")
revisar("la elección sigue en preparación", modulo_gobierno.base_datos.consultar_uno("SELECT estado FROM elecciones WHERE id = 2", [])["estado"] == "preparacion")
revisar("ya votó en la de ejemplo", "Ya votaste" in melany.get("/elecciones/1/votar").get_data(as_text=True))
revisar("no se vota en una cerrada", "no está abierta" in entrar("jhon.castano").get("/elecciones/1/votar").get_data(as_text=True))
revisar("no se vota en preparación", "no está abierta" in melany.post("/elecciones/2/votar", data={"paso": "votar", "opcion": candidato(2, 20)}).get_data(as_text=True))
revisar("nadie votó en preparación", votos_de(2) == 0 and votantes_de(2) == 0)
coordinadora = entrar("coordinadora")
revisar("la coordinadora ve resultados en preparación", coordinadora.get("/elecciones/2").status_code == 200)
revisar("la orientadora gestiona elecciones", "Nueva elección" in entrar("orientadora").get("/elecciones").get_data(as_text=True))
revisar("el administrador gestiona elecciones", "Nueva elección" in entrar("admin").get("/elecciones").get_data(as_text=True))
revisar("no se ven elecciones de otro colegio", destino(coordinadora.get("/elecciones/" + str(eleccion_ajena))) == "/inicio")
html = coordinadora.post("/elecciones", data={"accion": "abrir", "eleccion_id": str(eleccion_ajena)}).get_data(as_text=True)
revisar("no se cambian elecciones de otro colegio", "No se encontró la elección" in html)

print("Crear elección")
base = {"accion": "crear", "cargo": "personero", "titulo": "Personero de prueba", "grupo_id": "", "apertura": "2031-05-10T07:00", "cierre": "2031-05-10T12:00"}
formulario = dict(base)
formulario["apertura"] = "10/05/2031 7am"
revisar("una apertura mal escrita da error", "La apertura debe tener" in coordinadora.post("/elecciones", data=formulario).get_data(as_text=True))
formulario = dict(base)
formulario["cierre"] = "2031-05-10T06:00"
revisar("un cierre antes de la apertura da error", "después de la apertura" in coordinadora.post("/elecciones", data=formulario).get_data(as_text=True))
formulario = dict(base)
formulario["cargo"] = "representante"
revisar("representante sin grupo da error", "Elige el grupo" in coordinadora.post("/elecciones", data=formulario).get_data(as_text=True))
formulario = dict(base)
formulario["cargo"] = "alcalde"
formulario["titulo"] = ""
html = coordinadora.post("/elecciones", data=formulario).get_data(as_text=True)
revisar("cargo inventado y título vacío dan error", "Elige el cargo" in html and "Escribe el título" in html)
revisar("nada inválido se guardó", contar("SELECT id FROM elecciones WHERE colegio_id = 1", []) == 2)
html = coordinadora.post("/elecciones", data=base).get_data(as_text=True)
revisar("la elección válida se crea", "Elección creada" in html)
nueva = base_datos.consultar_uno("SELECT * FROM elecciones WHERE titulo = 'Personero de prueba'", [])
revisar("queda en preparación con la hora bien guardada", nueva["estado"] == "preparacion" and nueva["apertura"] == "2031-05-10 07:00" and nueva["grupo_id"] is None)
eid = str(nueva["id"])

print("Candidatos")
agregar = {"accion": "agregar_candidato", "eleccion_id": eid, "estudiante_id": "28", "numero": "1", "propuesta": "Más deporte y cultura."}
formulario = dict(agregar)
formulario["estudiante_id"] = "13"
revisar("un estudiante de Décimo no se postula a personero", "no puede postularse" in coordinadora.post("/elecciones", data=formulario).get_data(as_text=True))
formulario["estudiante_id"] = str(ajeno)
revisar("un estudiante de otro colegio no se postula", "Elige al estudiante" in coordinadora.post("/elecciones", data=formulario).get_data(as_text=True))
formulario = dict(agregar)
formulario["propuesta"] = ""
revisar("sin propuesta da error", "Escribe la propuesta" in coordinadora.post("/elecciones", data=formulario).get_data(as_text=True))
revisar("una candidata de Once se agrega", "Candidato agregado" in coordinadora.post("/elecciones", data=agregar).get_data(as_text=True))
revisar("no se repite la candidata", "ya es candidato" in coordinadora.post("/elecciones", data=agregar).get_data(as_text=True))
formulario = dict(agregar)
formulario["estudiante_id"] = "27"
revisar("no se repite el número", "ya lo tiene otro candidato" in coordinadora.post("/elecciones", data=formulario).get_data(as_text=True))
formulario["numero"] = "2"
coordinadora.post("/elecciones", data=formulario)
revisar("hay dos candidatos", contar("SELECT id FROM candidatos WHERE eleccion_id = ?", [nueva["id"]]) == 2)
representante = {"accion": "agregar_candidato", "eleccion_id": "2", "estudiante_id": "23", "numero": "3", "propuesta": "x"}
revisar("un estudiante de 11-A no se postula en 10-A", "no puede postularse" in coordinadora.post("/elecciones", data=representante).get_data(as_text=True))
representante["estudiante_id"] = "13"
coordinadora.post("/elecciones", data=representante)
quitar = candidato(2, 13)
revisar("una estudiante de 10-A se postula en 10-A", quitar != "")
revisar("se quita un candidato en preparación", "Candidato retirado" in coordinadora.post("/elecciones", data={"accion": "quitar_candidato", "candidato_id": quitar}).get_data(as_text=True))
contralor = dict(base)
contralor["cargo"] = "contralor"
contralor["titulo"] = "Contralor de prueba"
coordinadora.post("/elecciones", data=contralor)
vacia = base_datos.consultar_uno("SELECT id FROM elecciones WHERE titulo = 'Contralor de prueba'", [])
html = coordinadora.post("/elecciones", data={"accion": "abrir", "eleccion_id": str(vacia["id"])}).get_data(as_text=True)
revisar("no se abre una elección sin candidatos", "al menos un candidato" in html)
html = coordinadora.post("/elecciones", data={"accion": "abrir", "eleccion_id": eid}).get_data(as_text=True)
revisar("la votación se abre", "quedó abierta" in html)
html = coordinadora.post("/elecciones", data={"accion": "quitar_candidato", "candidato_id": candidato(nueva["id"], 28)}).get_data(as_text=True)
revisar("no se quitan candidatos con la votación abierta", "Solo se quitan" in html)
formulario = dict(agregar)
formulario["estudiante_id"] = "26"
formulario["numero"] = "3"
revisar("no se agregan candidatos con la votación abierta", "Solo se agregan" in coordinadora.post("/elecciones", data=formulario).get_data(as_text=True))

print("Votar")
ruta = "/elecciones/" + eid + "/votar"
html = melany.get(ruta).get_data(as_text=True)
revisar("el tarjetón muestra candidatos y voto en blanco", "María José Valencia" in html and "Voto en blanco" in html and "Más deporte" in html)
html = melany.post(ruta, data={"paso": "confirmar", "opcion": candidato(nueva["id"], 28)}).get_data(as_text=True)
revisar("pide confirmación antes de votar", "Confirma tu voto" in html and "María José Valencia" in html)
revisar("la confirmación no registra el voto", votantes_de(nueva["id"]) == 0 and votos_de(nueva["id"]) == 0)
html = melany.post(ruta, data={"paso": "votar", "opcion": candidato(1, 26)}).get_data(as_text=True)
revisar("no se vota por un candidato de otra elección", "Marca un candidato" in html and votos_de(nueva["id"]) == 0)
html = melany.post(ruta, data={"paso": "votar", "opcion": candidato(nueva["id"], 28)}).get_data(as_text=True)
revisar("el voto se registra", "Tu voto fue registrado" in html)
revisar("la página final no dice por quién votó", "María José Valencia" not in html)
revisar("hay un votante y un voto", votantes_de(nueva["id"]) == 1 and votos_de(nueva["id"]) == 1)
html = melany.post(ruta, data={"paso": "votar", "opcion": "blanco"}).get_data(as_text=True)
revisar("nadie vota dos veces", "Ya votaste" in html and votos_de(nueva["id"]) == 1)
eleccion = base_datos.consultar_uno("SELECT * FROM elecciones WHERE id = ?", [nueva["id"]])
revisar("el registro doble se rechaza también en la base", not modulo_gobierno.emitir_voto(eleccion, 13, None) and votos_de(nueva["id"]) == 1)
revisar("la estudiante ve que ya votó", "Votaste" in melany.get("/elecciones").get_data(as_text=True))
ultimo = base_datos.consultar_uno("SELECT detalle FROM registro_accesos WHERE accion = 'Votó en una elección' ORDER BY id DESC", [])
revisar("el registro de accesos no guarda el voto", ultimo is not None and "Valencia" not in ultimo["detalle"] and "María" not in ultimo["detalle"])
entrar("juan.restrepo").post(ruta, data={"paso": "votar", "opcion": "blanco"})
esteban.post(ruta, data={"paso": "votar", "opcion": candidato(nueva["id"], 28)})
revisar("el voto en blanco se guarda sin candidato", contar("SELECT id FROM votos WHERE eleccion_id = ? AND candidato_id IS NULL", [nueva["id"]]) == 1)
revisar("los de Once también votan personero", votantes_de(nueva["id"]) == 3)
revisar("la estudiante no ve resultados con la votación abierta", destino(melany.get("/elecciones/" + eid)) == "/inicio")
html = coordinadora.get("/elecciones/" + eid).get_data(as_text=True)
revisar("con la votación abierta la coordinadora ve la participación", "3 de 16" in html)
revisar("con la votación abierta nadie ve el conteo por candidato", "Votos por candidato" not in html and "voto secreto" in html)
coordinadora.post("/elecciones", data={"accion": "cerrar", "eleccion_id": eid})
revisar("la votación se cierra", base_datos.consultar_uno("SELECT estado FROM elecciones WHERE id = ?", [nueva["id"]])["estado"] == "cerrada")
sharon = entrar("sharon.loaiza")
html = sharon.post(ruta, data={"paso": "votar", "opcion": "blanco"}).get_data(as_text=True)
revisar("no se vota después del cierre", "no está abierta" in html and votos_de(nueva["id"]) == 3)
html = melany.get("/elecciones/" + eid).get_data(as_text=True)
revisar("con la elección cerrada todos ven el ganador", "Ganó la elección" in html and "María José Valencia" in html)

print("Representante de grupo")
coordinadora.post("/elecciones", data={"accion": "abrir", "eleccion_id": "2"})
revisar("un estudiante de 11-A no vota en 10-A", destino(esteban.get("/elecciones/2/votar")) == "/inicio")
revisar("un estudiante de 11-A no vota por POST en 10-A", destino(esteban.post("/elecciones/2/votar", data={"paso": "votar", "opcion": "blanco"})) == "/inicio")
html = melany.post("/elecciones/2/votar", data={"paso": "votar", "opcion": candidato(2, 20)}).get_data(as_text=True)
revisar("una estudiante de 10-A vota en 10-A", "Tu voto fue registrado" in html)
revisar("los habilitados son solo los de 10-A", "1 de 10" in coordinadora.get("/elecciones/2").get_data(as_text=True))
revisar("un estudiante de otro colegio no vota", destino(entrar("estudiante.ajeno").get("/elecciones/2/votar")) == "/inicio")

ayuda.terminar()
