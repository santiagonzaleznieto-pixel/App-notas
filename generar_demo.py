import os
import shutil
import base_datos

base_datos.ARCHIVO = os.path.join(base_datos.CARPETA_PROYECTO, "demo.db")
if os.path.exists(base_datos.ARCHIVO):
    os.remove(base_datos.ARCHIVO)

from app import app
from datos import CLAVE_PRUEBA

CARPETA_DEMO = os.path.join(base_datos.CARPETA_PROYECTO, "docs")
MAXIMO_POR_USUARIO = 400
PAGINAS_PUBLICAS = ["/privacidad", "/verificar"]

AVISO = (
    '<div style="background:#C98A2B;color:#122844;text-align:center;padding:8px 16px;'
    'font:500 14px Inter,sans-serif;">Demo de solo lectura con datos de prueba: '
    'puedes recorrer las páginas, pero nada se guarda.</div>'
)


def nombre_archivo(usuario, ruta):
    if ruta == "/" or ruta == "/salir":
        return "index.html"
    texto = ruta[1:]
    for letra in "/?=&":
        texto = texto.replace(letra, "-")
    return usuario + "--" + texto + ".html"


def enlaces_internos(html):
    enlaces = []
    inicio = html.find('href="/')
    while inicio != -1:
        fin = html.find('"', inicio + 6)
        ruta = html[inicio + 6:fin].replace("&amp;", "&")
        if not ruta.startswith("/static/") and ruta not in enlaces:
            enlaces.append(ruta)
        inicio = html.find('href="/', fin)
    return enlaces


def adaptar(html, usuario, enlaces, alias):
    html = html.replace('href="/static/', 'href="static/')
    html = html.replace('src="/static/', 'src="static/')
    for ruta in enlaces:
        original = ruta.replace("&", "&amp;")
        destino = ruta
        if ruta in alias:
            destino = alias[ruta]
        html = html.replace('href="' + original + '"', 'href="' + nombre_archivo(usuario, destino) + '"')
    html = html.replace('<form method="post"', '<form onsubmit="alert(\'En la demo no se guarda nada.\'); return false;"')
    html = html.replace("<body>", "<body>\n" + AVISO, 1)
    return html


def guardar(nombre, html):
    archivo = open(os.path.join(CARPETA_DEMO, nombre), "w", encoding="utf-8")
    archivo.write(html)
    archivo.close()


def ruta_de(direccion):
    if direccion.startswith("http://localhost"):
        return direccion[len("http://localhost"):]
    return direccion


def recorrer(usuario):
    cliente = app.test_client()
    cliente.post("/", data={"usuario": usuario, "clave": CLAVE_PRUEBA})
    pendientes = ["/inicio"]
    hechas = []
    paginas = {}
    alias = {}
    while len(pendientes) > 0 and len(paginas) < MAXIMO_POR_USUARIO:
        ruta = pendientes.pop(0)
        if ruta not in hechas and ruta != "/" and ruta != "/salir":
            hechas.append(ruta)
            respuesta = cliente.get(ruta)
            if respuesta.status_code == 302:
                destino = ruta_de(respuesta.headers.get("Location", "/inicio"))
                alias[ruta] = destino
                pendientes.append(destino)
            elif respuesta.status_code == 200:
                html = respuesta.get_data(as_text=True)
                paginas[ruta] = html
                for enlace in enlaces_internos(html):
                    pendientes.append(enlace)
    for ruta in paginas:
        html = paginas[ruta]
        guardar(nombre_archivo(usuario, ruta), adaptar(html, usuario, enlaces_internos(html), alias))
    print(usuario + ": " + str(len(paginas)) + " páginas")
    return nombre_archivo(usuario, "/inicio")


def paginas_publicas():
    cliente = app.test_client()
    for ruta in PAGINAS_PUBLICAS:
        html = cliente.get(ruta).get_data(as_text=True)
        guardar(nombre_archivo("publico", ruta), adaptar(html, "publico", enlaces_internos(html), {}))


def pagina_de_entrada(primeras):
    cliente = app.test_client()
    html = cliente.get("/").get_data(as_text=True)
    for ruta in PAGINAS_PUBLICAS:
        html = html.replace('href="' + ruta + '"', 'href="' + nombre_archivo("publico", ruta) + '"')
    html = html.replace('href="/static/', 'href="static/').replace('src="/static/', 'src="static/')
    html = html.replace("<body>", "<body>\n" + AVISO, 1)
    for usuario in primeras:
        html = html.replace(
            '<form method="post" action="/">\n          <input type="hidden" name="usuario" value="' + usuario + '">',
            '<form method="get" action="' + primeras[usuario] + '">',
        )
    html = html.replace('<input type="hidden" name="clave" value="' + CLAVE_PRUEBA + '">', "")

    paginas = ""
    for usuario in primeras:
        paginas = paginas + '"' + usuario + '": "' + primeras[usuario] + '", '
    script = (
        "<script>\nvar paginas = {" + paginas + "};\n"
        "function entrarDemo(formulario) {\n"
        "  var usuario = formulario.usuario.value.trim().toLowerCase();\n"
        "  if (paginas[usuario] && formulario.clave.value === '" + CLAVE_PRUEBA + "') {\n"
        "    location.href = paginas[usuario];\n"
        "  } else {\n"
        "    alert('En la demo solo funcionan los usuarios de acceso rápido, con la contraseña " + CLAVE_PRUEBA + ".');\n"
        "  }\n"
        "  return false;\n"
        "}\n</script>\n"
    )
    html = html.replace('<form method="post" action="/">', '<form onsubmit="return entrarDemo(this);">')
    html = html.replace("</body>", script + "</body>")
    guardar("index.html", html)


def usuarios_de_acceso_rapido():
    usuarios = []
    roles_vistos = []
    personas = base_datos.consultar("SELECT * FROM usuarios WHERE colegio_id = 1 AND activo = 1 ORDER BY id", [])
    for persona in personas:
        roles = base_datos.roles_de(persona["id"])
        if len(roles) > 0 and roles[0] not in roles_vistos:
            roles_vistos.append(roles[0])
            usuarios.append(persona["usuario"])
    return usuarios


if os.path.exists(CARPETA_DEMO):
    shutil.rmtree(CARPETA_DEMO)
os.makedirs(CARPETA_DEMO)
shutil.copytree(os.path.join(base_datos.CARPETA_PROYECTO, "static"), os.path.join(CARPETA_DEMO, "static"))
guardar(".nojekyll", "")

primeras = {}
for usuario in usuarios_de_acceso_rapido():
    primeras[usuario] = recorrer(usuario)
if "h.aguirre" not in primeras:
    primeras["h.aguirre"] = recorrer("h.aguirre")

paginas_publicas()
pagina_de_entrada(primeras)
os.remove(base_datos.ARCHIVO)
print("Demo lista en la carpeta docs")
