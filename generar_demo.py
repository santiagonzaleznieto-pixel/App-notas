import os
import shutil
import base_datos

base_datos.ARCHIVO = os.path.join(base_datos.CARPETA_PROYECTO, "demo.db")
if os.path.exists(base_datos.ARCHIVO):
    os.remove(base_datos.ARCHIVO)

from app import app
from datos import CLAVE_PRUEBA

CARPETA_DEMO = os.path.join(base_datos.CARPETA_PROYECTO, "docs")

AVISO = (
    '<div style="background:#C98A2B;color:#122844;text-align:center;padding:8px 16px;'
    'font:500 14px Inter,sans-serif;">Demo de solo lectura con datos de prueba: '
    'puedes recorrer las páginas, pero las notas no se guardan.</div>'
)


def nombre_archivo(usuario, ruta):
    if ruta == "/" or ruta == "/salir":
        return "index.html"
    texto = ruta[1:].replace("/", "-").replace("?periodo=", "-periodo-")
    return usuario + "--" + texto + ".html"


def enlaces_internos(html):
    enlaces = []
    inicio = html.find('href="/')
    while inicio != -1:
        fin = html.find('"', inicio + 6)
        ruta = html[inicio + 6:fin]
        if not ruta.startswith("/static/") and ruta not in enlaces:
            enlaces.append(ruta)
        inicio = html.find('href="/', fin)
    return enlaces


def adaptar(html, usuario, enlaces):
    html = html.replace('href="/static/', 'href="static/')
    html = html.replace('src="/static/', 'src="static/')
    for ruta in enlaces:
        html = html.replace('href="' + ruta + '"', 'href="' + nombre_archivo(usuario, ruta) + '"')
    html = html.replace(
        '<form method="post" class="tarjeta">',
        '<form class="tarjeta" onsubmit="alert(\'En la demo no se guardan las notas.\'); return false;">',
    )
    html = html.replace("<body>", "<body>\n" + AVISO, 1)
    return html


def guardar(nombre, html):
    archivo = open(os.path.join(CARPETA_DEMO, nombre), "w", encoding="utf-8")
    archivo.write(html)
    archivo.close()


def recorrer(usuario):
    cliente = app.test_client()
    respuesta = cliente.post("/", data={"usuario": usuario, "clave": CLAVE_PRUEBA}, follow_redirects=True)
    primera = respuesta.request.path
    pendientes = [primera]
    hechas = []
    while len(pendientes) > 0:
        ruta = pendientes.pop(0)
        if ruta not in hechas and ruta != "/" and ruta != "/salir":
            hechas.append(ruta)
            respuesta = cliente.get(ruta)
            if respuesta.status_code == 200:
                html = respuesta.get_data(as_text=True)
                enlaces = enlaces_internos(html)
                for enlace in enlaces:
                    pendientes.append(enlace)
                guardar(nombre_archivo(usuario, ruta), adaptar(html, usuario, enlaces))
    print(usuario + ": " + str(len(hechas)) + " páginas")
    return nombre_archivo(usuario, primera)


def pagina_de_entrada(primeras):
    html = app.test_client().get("/").get_data(as_text=True)
    html = adaptar(html, "", [])
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


if os.path.exists(CARPETA_DEMO):
    shutil.rmtree(CARPETA_DEMO)
os.makedirs(CARPETA_DEMO)
shutil.copytree(os.path.join(base_datos.CARPETA_PROYECTO, "static"), os.path.join(CARPETA_DEMO, "static"))
guardar(".nojekyll", "")

primeras = {}
roles_vistos = []
for persona in base_datos.usuarios_del_colegio(1):
    if persona["rol"] not in roles_vistos:
        roles_vistos.append(persona["rol"])
        primeras[persona["usuario"]] = recorrer(persona["usuario"])

pagina_de_entrada(primeras)
os.remove(base_datos.ARCHIVO)
print("Demo lista en la carpeta docs")
