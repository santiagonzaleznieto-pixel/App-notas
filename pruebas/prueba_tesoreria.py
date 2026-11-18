import ayuda
from ayuda import entrar, revisar, destino
import nucleo
import modulo_inicio
import modulo_notas
import modulo_tesoreria
import base_datos


def hoy_fijo():
    return "2026-11-17"


nucleo.hoy = hoy_fijo


def contar(sql, valores):
    return base_datos.consultar_uno(sql, valores)["total"]


def cobro_de(estudiante_id, descripcion):
    return base_datos.consultar_uno("SELECT * FROM cobros WHERE estudiante_id = ? AND descripcion LIKE ?",
                                    [estudiante_id, descripcion + "%"])


def texto(respuesta):
    return respuesta.get_data(as_text=True)


print("Ayudas")
revisar("formato de pesos con puntos de miles", modulo_tesoreria.formato_pesos(1250000) == "$1.250.000")
revisar("formato de pesos con números pequeños", modulo_tesoreria.formato_pesos(999) == "$999" and modulo_tesoreria.formato_pesos(0) == "$0")
revisar("formato de pesos con mil", modulo_tesoreria.formato_pesos(1000) == "$1.000")
revisar("lee pesos con puntos de miles", modulo_tesoreria.leer_pesos("1.250.000", 1, 100000000) == 1250000)
revisar("no acepta pesos con decimales", modulo_tesoreria.leer_pesos("320000,50", 1, 100000000) is None)
revisar("acepta una fecha válida", modulo_tesoreria.fecha_valida("2026-11-17"))
revisar("acepta el 29 de febrero de un año bisiesto", modulo_tesoreria.fecha_valida("2028-02-29"))
revisar("rechaza fechas imposibles", not modulo_tesoreria.fecha_valida("2026-02-30") and not modulo_tesoreria.fecha_valida("2026-13-01"))
revisar("rechaza fechas en otro formato", not modulo_tesoreria.fecha_valida("17/11/2026"))

print("Datos de ejemplo")
juan_octubre = cobro_de(14, "Pensión de octubre")
revisar("se sembraron los tres conceptos", contar("SELECT COUNT(*) AS total FROM conceptos_cobro WHERE colegio_id = 1", []) == 3)
revisar("hay pensiones de octubre y noviembre y la salida para 10-A",
        contar("SELECT COUNT(*) AS total FROM cobros WHERE colegio_id = 1", []) == 30)
revisar("Juan Pablo debe la pensión de octubre", juan_octubre["estado"] == "pendiente")
revisar("la pensión de octubre de Melany está pagada", cobro_de(13, "Pensión de octubre")["estado"] == "pagado")
revisar("los recibos tienen el formato R-2026-000001",
        base_datos.consultar_uno("SELECT numero_recibo FROM pagos ORDER BY id LIMIT 1", [])["numero_recibo"] == "R-2026-000001")

print("Permisos")
tesorero = entrar("tesoreria")
rectora = entrar("rectora")
admin = entrar("admin")
docente = entrar("c.munoz")
director = entrar("h.aguirre")
secretaria = entrar("secretaria")
madre = entrar("gloria.cardenas")
padre = entrar("jorge.restrepo")
estudiante = entrar("melany.osorio")
revisar("tesorería ve el tablero", tesorero.get("/tesoreria").status_code == 200)
revisar("la rectora ve el tablero", rectora.get("/tesoreria").status_code == 200)
revisar("administración ve el tablero", admin.get("/tesoreria").status_code == 200)
revisar("un docente no ve tesorería", destino(docente.get("/tesoreria")) == "/inicio")
revisar("secretaría no ve tesorería", destino(secretaria.get("/tesoreria")) == "/inicio")
revisar("una acudiente no ve el tablero", destino(madre.get("/tesoreria")) == "/inicio")
revisar("una estudiante no ve el tablero", destino(estudiante.get("/tesoreria")) == "/inicio")
revisar("tesorería y administración editan conceptos",
        tesorero.get("/tesoreria/conceptos").status_code == 200 and admin.get("/tesoreria/conceptos").status_code == 200)
revisar("la rectora no edita conceptos", destino(rectora.get("/tesoreria/conceptos")) == "/inicio")
revisar("solo tesorería genera cobros",
        tesorero.get("/tesoreria/generar").status_code == 200 and destino(admin.get("/tesoreria/generar")) == "/inicio")
revisar("la cartera es para tesorería y directivos",
        rectora.get("/tesoreria/cartera").status_code == 200 and destino(docente.get("/tesoreria/cartera")) == "/inicio")
revisar("la acudiente ve el estado de cuenta de su hija", madre.get("/tesoreria/estudiante/13").status_code == 200)
revisar("la acudiente no ve el estado de cuenta de otro", destino(madre.get("/tesoreria/estudiante/14")) == "/inicio")
revisar("el director de grupo no ve datos financieros", destino(director.get("/tesoreria/estudiante/13")) == "/inicio")
revisar("la estudiante no ve su estado de cuenta", destino(estudiante.get("/tesoreria/estudiante/13")) == "/inicio")
revisar("la acudiente ve solo lectura", "Registrar pago" not in texto(madre.get("/tesoreria/estudiante/13")))
respuesta = madre.post("/tesoreria/estudiante/13", data={"accion": "pago", "cobro_id": str(cobro_de(13, "Salida")["id"]), "valor": "45000"})
revisar("la acudiente no puede registrar pagos", destino(respuesta) == "/inicio")

print("Tablero y cartera")
html = texto(tesorero.get("/tesoreria"))
revisar("muestra la cartera vencida de Juan Pablo", "Cartera vencida" in html and "$320.000" in html)
revisar("muestra la cartera por grupo", "10-A" in html and "11-A" in html)
html = texto(tesorero.get("/tesoreria/cartera"))
revisar("la cartera lista a Juan Pablo con días de mora", "Juan Pablo Restrepo" in html and "28 días de mora" in html)
revisar("la cartera no lista a quien está al día", "Melany Osorio" not in html)
revisar("la cartera muestra al acudiente", "Jorge Iván Restrepo" in html)
revisar("el recordatorio es respetuoso", "De manera respetuosa" in html and "Copiar recordatorio" in html)
revisar("el recordatorio no amenaza", "centrales de riesgo" not in html and "demanda" not in html)
revisar("la cartera se filtra por grupo", "Juan Pablo Restrepo" not in texto(tesorero.get("/tesoreria/cartera?grupo=2")))

print("Conceptos y tope")
respuesta = admin.post("/tesoreria/conceptos", data={"accion": "tope", "anio": "2027", "tope": "11,24"})
revisar("guarda el tope de aumento", modulo_tesoreria.tope_del_anio(1, 2027) == 11.24)
respuesta = admin.post("/tesoreria/conceptos", data={"accion": "tope", "anio": "2027", "tope": "ciento"})
revisar("rechaza un tope que no es número", "porcentaje entre 0 y 100" in texto(respuesta))
datos = {"accion": "concepto", "nombre": "Pensión mensual 2027", "tipo": "pension", "anio": "2027",
         "valor": "360.000", "valor_anterior": "320.000", "activo": "1"}
html = texto(admin.post("/tesoreria/conceptos", data=datos))
revisar("crea un concepto con puntos de miles",
        base_datos.consultar_uno("SELECT valor FROM conceptos_cobro WHERE nombre = ?", ["Pensión mensual 2027"])["valor"] == 360000)
revisar("advierte si el aumento supera el tope del MEN", "Advertencia" in html and "12,5 %" in html and "11,24 %" in html)
revisar("explica la resolución del Ministerio", "Ministerio de Educación Nacional" in html)
revisar("la pensión 2026 no supera el tope de 9,1 %", "6,67 %" in html and "«Pensión mensual»" not in html)
revisar("no repite nombres en el mismo año", "Ya existe" in texto(admin.post("/tesoreria/conceptos", data=datos)))
datos["nombre"] = "Derechos de grado"
datos["valor"] = "mucho"
revisar("rechaza un valor inválido", "pesos, sin decimales" in texto(admin.post("/tesoreria/conceptos", data=datos)))
nuevo = base_datos.consultar_uno("SELECT * FROM conceptos_cobro WHERE nombre = ?", ["Pensión mensual 2027"])
datos = {"accion": "concepto", "concepto_id": str(nuevo["id"]), "nombre": "Pensión mensual 2027", "tipo": "pension",
         "anio": "2027", "valor": "355000", "valor_anterior": "320000", "activo": "1"}
admin.post("/tesoreria/conceptos", data=datos)
revisar("edita un concepto", base_datos.consultar_uno("SELECT valor FROM conceptos_cobro WHERE id = ?", [nuevo["id"]])["valor"] == 355000)

print("Paz y salvo al día")
html = texto(madre.get("/tesoreria/paz-y-salvo/13"))
revisar("Melany está a paz y salvo", "se encuentra <strong>a paz y salvo</strong>" in html and "window.print()" in html)
revisar("la acudiente ve el paz y salvo en sus pagos", "A paz y salvo" in texto(madre.get("/mis-pagos")))
revisar("la función de paz y salvo sirve a otros módulos",
        modulo_tesoreria.esta_a_paz_y_salvo(1, 13) and not modulo_tesoreria.esta_a_paz_y_salvo(1, 14))

print("Generar cobros")
salida = base_datos.consultar_uno("SELECT id FROM conceptos_cobro WHERE colegio_id = 1 AND tipo = 'otro'", [])["id"]
datos = {"concepto_id": str(salida), "grupo": "2", "descripcion": "Salida pedagógica 11-A", "fecha_limite": "2026-12-01"}
html = texto(tesorero.post("/tesoreria/generar", data=datos))
revisar("genera un cobro por estudiante de 11-A", "Se crearon 6 cobros" in html)
html = texto(tesorero.post("/tesoreria/generar", data=datos))
revisar("no duplica cobros del mismo concepto y fecha", "Se crearon 0 cobros" in html and "6 estudiantes ya tenían" in html)
revisar("quedan 6 cobros, no 12",
        contar("SELECT COUNT(*) AS total FROM cobros WHERE descripcion = ?", ["Salida pedagógica 11-A"]) == 6)
datos["fecha_limite"] = "2026-31-12"
revisar("rechaza una fecha límite inválida", "no es válida" in texto(tesorero.post("/tesoreria/generar", data=datos)))
datos["fecha_limite"] = "2026-11-01"
revisar("rechaza una fecha límite pasada", "anterior a hoy" in texto(tesorero.post("/tesoreria/generar", data=datos)))
datos = {"concepto_id": str(salida), "grupo": "todos", "descripcion": "", "fecha_limite": "2026-12-01"}
html = texto(tesorero.post("/tesoreria/generar", data=datos))
revisar("genera para todo el colegio sin repetir", "Se crearon 10 cobros" in html and "6 estudiantes ya tenían" in html)

print("Otro colegio")
otro_colegio = base_datos.ejecutar(
    "INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
    ["Colegio de Prueba", "Prueba", "Génova", "Quindío", 2026],
)
ajeno = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
                            [otro_colegio, "estudiante.ajeno", "sin-clave", "Estudiante Ajeno"])
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [ajeno, "estudiante"])
concepto_ajeno = base_datos.ejecutar(
    "INSERT INTO conceptos_cobro (colegio_id, anio, nombre, tipo, valor) VALUES (?, ?, ?, ?, ?)",
    [otro_colegio, 2026, "Pensión ajena", "pension", 500000],
)
cobro_ajeno = base_datos.ejecutar(
    "INSERT INTO cobros (colegio_id, anio, estudiante_id, concepto_id, descripcion, valor, fecha_limite, creado_en) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    [otro_colegio, 2026, ajeno, concepto_ajeno, "Pensión ajena", 500000, "2026-10-01", "2026-09-01 08:00"],
)
recibo_esperado = modulo_tesoreria.siguiente_recibo(1, 2026)
base_datos.ejecutar(
    "INSERT INTO pagos (colegio_id, cobro_id, valor, fecha, medio, referencia, recibido_por, registrado_en, numero_recibo) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    [otro_colegio, cobro_ajeno, 100000, "2026-09-15", "efectivo", "", ajeno, "2026-09-15 08:00", recibo_esperado],
)
revisar("no se ve el estado de cuenta de otro colegio", destino(tesorero.get("/tesoreria/estudiante/" + str(ajeno))) == "/inicio")
revisar("no se ve el recibo de otro colegio", destino(tesorero.get("/tesoreria/recibo/" + recibo_esperado)) == "/inicio")
revisar("no se ve el paz y salvo de otro colegio", destino(tesorero.get("/tesoreria/paz-y-salvo/" + str(ajeno))) == "/inicio")
revisar("la cartera no muestra estudiantes de otro colegio", "Estudiante Ajeno" not in texto(tesorero.get("/tesoreria/cartera")))
datos = {"accion": "pago", "cobro_id": str(cobro_ajeno), "valor": "100000", "fecha": "2026-11-17", "medio": "efectivo"}
html = texto(tesorero.post("/tesoreria/estudiante/14", data=datos))
revisar("no se puede pagar un cobro de otro colegio", "Elige un cobro pendiente" in html)
revisar("el cobro ajeno no recibe pagos",
        contar("SELECT COUNT(*) AS total FROM pagos WHERE cobro_id = ?", [cobro_ajeno]) == 1)
datos = {"concepto_id": str(concepto_ajeno), "grupo": "todos", "descripcion": "", "fecha_limite": "2026-12-15"}
revisar("no se generan cobros con conceptos de otro colegio", "concepto de cobro activo" in texto(tesorero.post("/tesoreria/generar", data=datos)))
datos = {"accion": "concepto", "concepto_id": str(concepto_ajeno), "nombre": "Cambiado", "tipo": "pension", "anio": "2026",
         "valor": "1000", "valor_anterior": "", "activo": "1"}
admin.post("/tesoreria/conceptos", data=datos)
revisar("no se editan conceptos de otro colegio",
        base_datos.consultar_uno("SELECT nombre FROM conceptos_cobro WHERE id = ?", [concepto_ajeno])["nombre"] == "Pensión ajena")

print("Pagos y recibos")
datos = {"accion": "pago", "cobro_id": str(juan_octubre["id"]), "valor": "400.000", "fecha": "2026-11-17", "medio": "efectivo"}
revisar("no deja pagar más que el saldo", "mayor que el saldo" in texto(tesorero.post("/tesoreria/estudiante/14", data=datos)))
datos["valor"] = "120.000"
datos["medio"] = "transferencia"
revisar("pide la referencia de una transferencia", "referencia" in texto(tesorero.post("/tesoreria/estudiante/14", data=datos)))
datos["referencia"] = "Bancolombia 99881"
datos["fecha"] = "2026-11-30"
revisar("no acepta pagos con fecha futura", "posterior a hoy" in texto(tesorero.post("/tesoreria/estudiante/14", data=datos)))
datos["fecha"] = "2026-11-17"
html = texto(tesorero.post("/tesoreria/estudiante/14", data=datos))
siguiente = modulo_tesoreria.armar_recibo(2026, int(recibo_esperado[7:]) + 1)
revisar("registra un abono y genera recibo", "Pago registrado con el recibo" in html)
revisar("el número de recibo no se repite aunque otro colegio lo tenga", siguiente in html)
revisar("con un abono el cobro sigue pendiente", cobro_de(14, "Pensión de octubre")["estado"] == "pendiente")
datos["valor"] = "200000"
tesorero.post("/tesoreria/estudiante/14", data=datos)
revisar("al completar el valor el cobro queda pagado", cobro_de(14, "Pensión de octubre")["estado"] == "pagado")
revisar("admin no registra pagos", destino(admin.post("/tesoreria/estudiante/14", data=datos)) == "/inicio")
html = texto(tesorero.get("/tesoreria/recibo/" + siguiente))
revisar("el recibo es imprimible y tiene el escudo", "window.print()" in html and "/static/escudo.png" in html)
revisar("el recibo muestra estudiante, valor y quién recibió",
        "Juan Pablo Restrepo" in html and "$120.000" in html and "Carlos Alberto Ramírez" in html and "Transferencia" in html)
revisar("el padre ve el recibo de su hijo", padre.get("/tesoreria/recibo/" + siguiente).status_code == 200)
revisar("otra acudiente no ve ese recibo", destino(madre.get("/tesoreria/recibo/" + siguiente)) == "/inicio")

print("Descuentos y anulaciones")
juan_noviembre = cobro_de(14, "Pensión de noviembre")
datos = {"accion": "descuento", "cobro_id": str(juan_noviembre["id"]), "valor": "32.000", "motivo": "Beca del Acta 10"}
revisar("tesorería no autoriza descuentos", destino(tesorero.post("/tesoreria/estudiante/14", data=datos)) == "/inicio")
datos["motivo"] = ""
revisar("el descuento pide motivo", "motivo del descuento" in texto(rectora.post("/tesoreria/estudiante/14", data=datos)))
datos["motivo"] = "Beca del Acta 10"
datos["valor"] = "999.000"
revisar("el descuento no supera el saldo", "mayor que el saldo" in texto(rectora.post("/tesoreria/estudiante/14", data=datos)))
datos["valor"] = "32.000"
html = texto(rectora.post("/tesoreria/estudiante/14", data=datos))
revisar("la rectora autoriza un descuento", "Descuento de $32.000 registrado" in html and "$288.000" in html)
salida_juan = cobro_de(14, "Salida pedagógica al")
datos = {"accion": "anular", "cobro_id": str(salida_juan["id"]), "motivo": ""}
revisar("anular pide motivo", "motivo de la anulación" in texto(tesorero.post("/tesoreria/estudiante/14", data=datos)))
datos["motivo"] = "No asistirá a la salida por incapacidad médica"
html = texto(tesorero.post("/tesoreria/estudiante/14", data=datos))
revisar("tesorería anula un cobro sin pagos", cobro_de(14, "Salida pedagógica al")["estado"] == "anulado" and "Cobro anulado" in html)
sharon_salida = cobro_de(15, "Salida pedagógica al")
datos = {"accion": "anular", "cobro_id": str(sharon_salida["id"]), "motivo": "Se generó por error"}
revisar("no se anula un cobro con pagos", "ya tiene pagos" in texto(tesorero.post("/tesoreria/estudiante/15", data=datos)))
revisar("la rectora no anula cobros", destino(rectora.post("/tesoreria/estudiante/15", data=datos)) == "/inicio")

print("Paz y salvo")
html = texto(madre.get("/tesoreria/paz-y-salvo/13"))
revisar("un cobro nuevo quita el paz y salvo", "Todavía no se puede expedir" in html and "Salida pedagógica al Jardín Botánico" in html)
html = texto(tesorero.get("/tesoreria/paz-y-salvo/14"))
revisar("Juan Pablo no tiene paz y salvo y ve lo que debe", "Todavía no se puede expedir" in html and "Pensión de noviembre" in html)
revisar("la acudiente no ve el paz y salvo de otro", destino(madre.get("/tesoreria/paz-y-salvo/14")) == "/inicio")

print("Mis pagos")
html = texto(madre.get("/mis-pagos"))
revisar("la acudiente ve el estado de cuenta de su hija", "Melany Osorio Cárdenas" in html and "Saldo por pagar $45.000" in html)
revisar("la acudiente ve los recibos de sus pagos", "Recibo R-2026-" in html)
revisar("la acudiente no ve a otros estudiantes", "Juan Pablo" not in html)
html = texto(padre.get("/mis-pagos"))
revisar("el padre ve el saldo de su hijo", "Juan Pablo Restrepo" in html and "Saldo por pagar" in html)
revisar("tesorería no tiene la página de acudientes", destino(tesorero.get("/mis-pagos")) == "/inicio")

ayuda.terminar()
