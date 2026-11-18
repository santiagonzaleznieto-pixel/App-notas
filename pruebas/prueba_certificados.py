import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import modulo_horas
import modulo_certificados
import base_datos
from werkzeug.security import generate_password_hash


def certificados(estudiante_id, tipo):
    return base_datos.consultar("SELECT * FROM certificados WHERE estudiante_id = ? AND tipo = ? ORDER BY id", [estudiante_id, tipo])


def total():
    return len(base_datos.consultar("SELECT id FROM certificados", []))


def codigo_de(respuesta):
    ruta = destino(respuesta)
    if not ruta.startswith("/certificados/"):
        return ""
    return ruta[len("/certificados/"):]


def emitir(cliente, estudiante_id, tipo):
    return cliente.post("/certificados", data={"accion": "emitir", "tipo": tipo, "estudiante_id": str(estudiante_id)})


def codigo_valido(codigo):
    if len(codigo) != 10:
        return False
    for letra in codigo:
        if letra not in modulo_certificados.LETRAS_CODIGO:
            return False
    return True


print("Datos de ejemplo y códigos")
constancia_melany = certificados(13, "constancia_estudio")
social_luisa = certificados(26, "servicio_social")
revisar("hay una constancia de estudio de Melany", len(constancia_melany) == 1)
revisar("hay un certificado de servicio social de Luisa", len(social_luisa) == 1 and "82 horas" in social_luisa[0]["contenido"])
revisar("los códigos de ejemplo tienen 10 caracteres válidos", codigo_valido(constancia_melany[0]["codigo"]) and codigo_valido(social_luisa[0]["codigo"]))
generados = []
repetidos = 0
for vuelta in range(300):
    codigo = modulo_certificados.generar_codigo()
    if codigo in generados or not codigo_valido(codigo):
        repetidos = repetidos + 1
    generados.append(codigo)
revisar("generar_codigo da códigos válidos y distintos", repetidos == 0)
confusos = 0
for letra in "O0I1":
    if letra in modulo_certificados.LETRAS_CODIGO:
        confusos = confusos + 1
revisar("los códigos no usan caracteres confusos", confusos == 0)
revisar("detecta si una tabla no existe", not modulo_certificados.tabla_existe("tabla_que_no_existe"))

print("Permisos")
revisar("una docente no entra a certificados", destino(entrar("c.munoz").get("/certificados")) == "/inicio")
revisar("la orientadora no entra a certificados", destino(entrar("orientadora").get("/certificados")) == "/inicio")
secretaria = entrar("secretaria")
html = secretaria.get("/certificados").get_data(as_text=True)
revisar("la secretaría ve el buscador y los últimos emitidos", "Buscar estudiante" in html and "Últimos certificados emitidos" in html)
html = secretaria.get("/certificados?buscar=Montoya").get_data(as_text=True)
revisar("busca estudiantes por nombre", "/certificados?estudiante=26" in html and "/certificados?estudiante=13" not in html)
melany = entrar("melany.osorio")
html = melany.get("/certificados").get_data(as_text=True)
revisar("la estudiante ve sus certificados", "Mis certificados" in html and constancia_melany[0]["codigo"] in html)
revisar("la estudiante no ve el buscador ni certificados ajenos", "Buscar estudiante" not in html and social_luisa[0]["codigo"] not in html)
madre = entrar("gloria.cardenas")
html = madre.get("/certificados").get_data(as_text=True)
revisar("la acudiente ve los certificados de su hija", "Melany Osorio" in html and constancia_melany[0]["codigo"] in html)

print("Emitir como secretaría")
respuesta = emitir(secretaria, 14, "constancia_estudio")
codigo_juan = codigo_de(respuesta)
fila = base_datos.consultar_uno("SELECT * FROM certificados WHERE codigo = ?", [codigo_juan])
revisar("emite una constancia de estudio y lleva a la vista para imprimir", fila is not None and fila["estudiante_id"] == 14 and fila["emitido_por"] == 11)
revisar("la constancia dice el grupo y el año", "grupo 10-A" in fila["contenido"] and "2026" in fila["contenido"])
codigo_notas = codigo_de(emitir(secretaria, 13, "notas"))
fila = base_datos.consultar_uno("SELECT * FROM certificados WHERE codigo = ?", [codigo_notas])
revisar("emite el certificado de notas con materias y desempeño", fila is not None and "Matemáticas | " in fila["contenido"] and "Superior" in fila["contenido"])
antes = total()
html = emitir(secretaria, 23, "servicio_social").get_data(as_text=True)
revisar("no emite servicio social si no cumplió las 80 horas", "todavía no cumple" in html and total() == antes)
html = secretaria.get("/certificados?estudiante=26").get_data(as_text=True)
revisar("ofrece servicio social y constitucionales a Luisa", 'value="servicio_social"' in html and 'value="estudios_constitucionales"' in html)
html = secretaria.get("/certificados?estudiante=23").get_data(as_text=True)
revisar("no ofrece servicio social a Esteban", 'value="servicio_social"' not in html and "Lleva 64 de 80" in html)
codigo_const = codigo_de(emitir(secretaria, 26, "estudios_constitucionales"))
revisar("emite estudios constitucionales a quien cumplió", codigo_const != "" and len(certificados(26, "estudios_constitucionales")) == 1)
revisar("rechaza un tipo inválido", "tipo de certificado" in emitir(secretaria, 14, "diploma").get_data(as_text=True))
revisar("no emite a un docente como si fuera estudiante", "tipo de certificado" in emitir(secretaria, 4, "constancia_estudio").get_data(as_text=True))

print("Emitir como estudiante y acudiente")
codigo_propio = codigo_de(emitir(melany, 13, "constancia_estudio"))
revisar("la estudiante emite su propia constancia", codigo_propio != "" and len(certificados(13, "constancia_estudio")) == 2)
antes = total()
revisar("la estudiante no emite constancias de otros", destino(emitir(melany, 14, "constancia_estudio")) == "/inicio" and total() == antes)
revisar("la estudiante no emite su certificado de notas", destino(emitir(melany, 13, "notas")) == "/inicio" and total() == antes)
revisar("la estudiante no emite servicio social", destino(emitir(entrar("luisa.montoya"), 26, "servicio_social")) == "/inicio" and total() == antes)
revisar("la acudiente emite la constancia de su hija", codigo_de(emitir(madre, 13, "constancia_estudio")) != "")
antes = total()
revisar("la acudiente no emite constancias de otros", destino(emitir(madre, 14, "constancia_estudio")) == "/inicio" and total() == antes)

print("Vista para imprimir")
html = melany.get("/certificados/" + codigo_propio).get_data(as_text=True)
revisar("la estudiante ve su certificado", "Constancia de estudio" in html)
revisar("tiene escudo, firma de la rectora, código y verificación",
        "/static/escudo.png" in html and "Martha Cecilia Vallejo" in html and codigo_propio in html
        and "Verifique este documento en" in html and "/verificar" in html and "window.print()" in html)
revisar("acepta el código en minúsculas", melany.get("/certificados/" + codigo_propio.lower()).status_code == 200)
juan = entrar("juan.restrepo")
revisar("otro estudiante no ve el certificado", destino(juan.get("/certificados/" + codigo_propio)) == "/inicio")
revisar("la madre ve el certificado de su hija", madre.get("/certificados/" + codigo_propio).status_code == 200)
revisar("otro acudiente no lo ve", destino(entrar("jorge.restrepo").get("/certificados/" + codigo_propio)) == "/inicio")
revisar("la coordinadora lo ve", entrar("coordinadora").get("/certificados/" + codigo_propio).status_code == 200)
revisar("una docente no lo ve", destino(entrar("c.munoz").get("/certificados/" + codigo_propio)) == "/inicio")
revisar("sin sesión no se ve", destino(ayuda.app.test_client().get("/certificados/" + codigo_propio)) == "/")
html = secretaria.get("/certificados/" + codigo_notas).get_data(as_text=True)
revisar("el certificado de notas muestra la tabla", "Promedio general" in html and "Nota final" in html)

print("Verificación pública")
publico = ayuda.app.test_client()
respuesta = publico.get("/verificar")
revisar("la verificación abre sin iniciar sesión", respuesta.status_code == 200 and "Código de verificación" in respuesta.get_data(as_text=True))
base_datos.ejecutar("UPDATE usuarios SET documento = '1094887766' WHERE id = 13", [])
html = publico.get("/verificar?codigo=" + codigo_notas).get_data(as_text=True)
revisar("un código válido muestra tipo, estudiante, colegio y fecha",
        "Certificado válido" in html and "Certificado de notas" in html and "Melany Osorio" in html
        and "Institución Educativa Instituto Pijao" in html and "de noviembre de 2026" in html)
revisar("no muestra el documento ni las notas", "1094887766" not in html and "Matemáticas" not in html and "Promedio" not in html)
html = publico.post("/verificar", data={"codigo": " " + codigo_juan.lower() + " "}).get_data(as_text=True)
revisar("por POST y en minúsculas también verifica", "Certificado válido" in html and "Juan Pablo Restrepo" in html)
html = publico.get("/verificar?codigo=ZZZZZZZZZZ").get_data(as_text=True)
revisar("un código inexistente se informa", "Código no encontrado" in html)
revisar("el código del usuario se muestra escapado", "<b>" not in publico.get("/verificar?codigo=<b>x</b>").get_data(as_text=True))

print("Anular")
fila = base_datos.consultar_uno("SELECT id FROM certificados WHERE codigo = ?", [codigo_juan])
coordinadora = entrar("coordinadora")
revisar("la coordinadora no puede anular", destino(coordinadora.post("/certificados", data={"accion": "anular", "certificado_id": str(fila["id"])})) == "/inicio"
        and base_datos.consultar_uno("SELECT anulado FROM certificados WHERE id = ?", [fila["id"]])["anulado"] == 0)
revisar("la estudiante no puede anular", destino(melany.post("/certificados", data={"accion": "anular", "certificado_id": str(fila["id"])})) == "/inicio")
html = secretaria.post("/certificados", data={"accion": "anular", "certificado_id": str(fila["id"])}).get_data(as_text=True)
anulado = base_datos.consultar_uno("SELECT * FROM certificados WHERE id = ?", [fila["id"]])
revisar("la secretaría anula un certificado", "anulado" in html and anulado["anulado"] == 1 and anulado["anulado_por"] == 11)
revisar("no se anula dos veces", "ya estaba anulado" in secretaria.post("/certificados", data={"accion": "anular", "certificado_id": str(fila["id"])}).get_data(as_text=True))
html = publico.get("/verificar?codigo=" + codigo_juan).get_data(as_text=True)
revisar("la verificación muestra que está anulado", "Certificado anulado" in html and "Juan Pablo Restrepo" not in html)
revisar("la vista para imprimir marca el anulado", "ANULADO" in secretaria.get("/certificados/" + codigo_juan).get_data(as_text=True))
rectora = entrar("rectora")
fila = base_datos.consultar_uno("SELECT id FROM certificados WHERE codigo = ?", [codigo_const])
rectora.post("/certificados", data={"accion": "anular", "certificado_id": str(fila["id"])})
revisar("la rectora también puede anular", base_datos.consultar_uno("SELECT anulado FROM certificados WHERE id = ?", [fila["id"]])["anulado"] == 1)

print("Aislamiento entre colegios")
otro_colegio = base_datos.ejecutar(
    "INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
    ["Colegio Vecino", "Col. Vecino", "Génova", "Quindío", 2026],
)
estudiante_vecino = base_datos.ejecutar(
    "INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
    [otro_colegio, "estudiante.vecino", generate_password_hash("pijao2026"), "Estudiante Vecino"],
)
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, 'estudiante')", [estudiante_vecino])
codigo_vecino = modulo_certificados.generar_codigo()
certificado_vecino = base_datos.ejecutar(
    "INSERT INTO certificados (colegio_id, codigo, tipo, estudiante_id, emitido_por, emitido_en, contenido) VALUES (?, ?, 'constancia_estudio', ?, ?, '2026-11-01 09:00', 'Texto')",
    [otro_colegio, codigo_vecino, estudiante_vecino, estudiante_vecino],
)
revisar("la secretaría no ve certificados de otro colegio", destino(secretaria.get("/certificados/" + codigo_vecino)) == "/inicio")
antes = total()
html = emitir(secretaria, estudiante_vecino, "constancia_estudio").get_data(as_text=True)
revisar("no emite certificados a estudiantes de otro colegio", "Elige un estudiante de este colegio" in html and total() == antes)
revisar("no anula certificados de otro colegio", destino(secretaria.post("/certificados", data={"accion": "anular", "certificado_id": str(certificado_vecino)})) == "/inicio"
        and base_datos.consultar_uno("SELECT anulado FROM certificados WHERE id = ?", [certificado_vecino])["anulado"] == 0)
html = secretaria.get("/certificados?buscar=Vecino").get_data(as_text=True)
revisar("el buscador no muestra estudiantes de otro colegio", "Estudiante Vecino" not in html)
html = secretaria.get("/certificados").get_data(as_text=True)
revisar("la lista de emitidos no muestra otro colegio", codigo_vecino not in html)
html = publico.get("/verificar?codigo=" + codigo_vecino).get_data(as_text=True)
revisar("la verificación pública muestra el colegio que emitió", "Colegio Vecino" in html)

ayuda.terminar()
