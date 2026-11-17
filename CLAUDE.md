# Plataforma de gestión escolar

Plataforma web en Python con Flask para manejar todo un colegio colombiano: notas, asistencia, convivencia, horas sociales, familias, pagos y reportes. Se venderá a instituciones públicas y privadas, de Transición a Once. Empezó como un proyecto de clase del SENA con las notas de Décimo de la Institución Educativa Instituto Pijao (Pijao, Quindío), que ahora es el **colegio piloto**.

Plan maestro (visión, ley, roles, módulos, fases): https://claude.ai/artifact/QQYMz3DWLH2gvuDGn6a4yu

## Reglas para trabajar en este proyecto

- Todo en español: nombres de variables, funciones, rutas, tablas, columnas y textos de la página.
- No escribir comentarios en el código. Solo lo necesario.
- Mantenerlo sencillo. En clase se han visto: secuenciales, condicionales (`if`, `elif`, `else`), ciclo `for` y ciclo `while`. También se permiten variables, listas, diccionarios, funciones (`def`), Flask, `sqlite3` (viene con Python) y `werkzeug.security` (viene con Flask).
- Evitar lo que no se ha visto: clases, `lambda`, listas por comprensión, `try`/`except`, `with`, `sorted` con `key`, decoradores propios, librerías extra.
- No pensar solo en el Instituto Pijao: todo debe servir para cualquier colegio. Cada tabla lleva `colegio_id` y cada consulta filtra por el colegio del usuario.
- Lo que cambia de un colegio a otro (escala, períodos, grados, materias, logo) se guarda en la base de datos, no en el código.
- Base de datos: SQLite hasta la fase 4 del plan maestro; luego PostgreSQL.
- Mantener el diseño actual (ver "Diseño").
- Soy principiante: explica cada cambio con palabras sencillas y dime cómo probarlo.

## Cómo se ejecuta (Windows, terminal de VS Code)

Desde la carpeta `plataforma_escolar`:

```
py -m pip install flask
py app.py
```

Luego abrir http://127.0.0.1:5000 en el navegador.

La primera vez, `app.py` crea el archivo `plataforma.db` y lo llena con los datos de `datos.py`. Para volver a los datos iniciales: cerrar el programa, borrar `plataforma.db` y abrirlo otra vez. `plataforma.db` no se sube a GitHub (está en `.gitignore`) porque guarda datos de estudiantes.

## Estructura

- `app.py`: rutas, permisos por rol y cálculos (promedios, puestos, alertas).
- `base_datos.py`: todo lo que habla con SQLite. Crea las tablas, carga los datos iniciales y tiene funciones para leer y guardar (`usuarios_del_colegio`, `materias_del_colegio`, `notas_del_colegio`, `guardar_nota`).
- `datos.py`: datos iniciales del colegio piloto. Solo se usan para llenar la base cuando está vacía.
- `templates/`: `base.html`, `login.html`, `materias.html`, `calificar.html`, `consolidado.html`, `boletin.html` (plantillas Jinja).
- `static/`: `estilos.css` y `escudo.png`.

## Tablas de la base de datos

- `colegios`: nombre, municipio, departamento, año y número de períodos.
- `usuarios`: colegio, usuario (único), contraseña cifrada, nombre y rol.
- `materias`: colegio, nombre, nombre corto y profesor (su usuario). El `id` es un número y se usa en `/calificar/<id>`.
- `notas`: colegio, estudiante, materia, período y valor. Una fila por estudiante, materia y período. `valor` vacío (`NULL`) = nota pendiente.

En `app.py`, `datos_del_colegio(colegio_id)` reúne todo en un diccionario con `colegio`, `usuarios`, `estudiantes`, `materias`, `notas` (estudiante → id de materia → lista de notas por período) y `periodos`.

## Roles y permisos

Contraseña de prueba para todos: `pijao2026` (`CLAVE_PRUEBA` en `datos.py`). En la base se guarda cifrada.

- `rectora` y `coordinadora`: ven el consolidado del grado (`/consolidado`) y el boletín de cualquier estudiante de su colegio. Solo lectura.
- `director` (`h.aguirre`, Hernán Darío Aguirre, dicta Filosofía y Ciencias Sociales): califica sus materias y ve el consolidado como "Mi grupo".
- `profesor`: solo ve y califica sus materias (`/materias`, `/calificar/<id_materia>`).
- `estudiante`: solo ve su propio boletín (`/boletin/<usuario>`).

Nadie ve datos de otro colegio. 10 estudiantes de prueba, 8 materias, 7 docentes, 4 períodos.

## Reglas de las notas

- Escala de 1.0 a 5.0, un decimal.
- Desempeño: Bajo 1.0–2.9, Básico 3.0–3.9, Alto 4.0–4.5, Superior 4.6–5.0, Pendiente si no hay nota. Es la escala nacional del Decreto 1290 de 2009; más adelante cada colegio configura la suya.
- Promedio de una materia: promedio de las notas de los períodos que ya existen.
- Promedio general: promedio de todas las materias.
- Puesto: 1 + número de compañeros con mejor promedio (los empates comparten puesto).

## Dónde se usa cada tema de clase

- Secuenciales: `datos.py`.
- `while`: `buscar_usuario` (búsqueda del usuario al iniciar sesión).
- `if` / `elif` / `else`: `desempeno`, el login, los permisos de cada ruta y el mensaje del boletín.
- `for`: `promedio`, `tabla_grupo` (puestos), alertas, resumen por materia, guardar notas y cargar los datos iniciales.
- Funciones: `base_datos.py` (una función por cada consulta).

## Diseño

- Colores: azul `#1E3A5F`, azul oscuro `#122844`, verde cafetero `#3F6B4A`, verde oscuro `#2C4E35`, terracota `#BD5B2E`, dorado `#C98A2B`, crema `#FBF8F2`.
- Fuentes: Fraunces (títulos) e Inter (texto), desde Google Fonts.
- Montañas del Paisaje Cultural Cafetero en el login y franja bajo la barra superior.
- El nombre "Instituto Pijao" todavía está escrito en `base.html` y `login.html`. Cuando haya varios colegios, saldrá de la tabla `colegios`.

## Estado

Fase 1 del plan maestro: base de datos y todo el colegio.

- [x] Notas, usuarios y materias guardados en SQLite, con `colegio_id`.
- [x] Contraseñas cifradas.
- [ ] Grados y grupos de Transición a Once (tablas `grados`, `grupos`, `matriculas`, `asignaciones`). Hoy `GRADO` sigue fijo en `datos.py`.
- [ ] Rol de administrador del colegio que crea usuarios, materias y grupos desde la página.
- [ ] Escala, períodos y porcentajes configurables por colegio.
- [ ] Contraseña propia para cada usuario y cambio de contraseña.

Puerta para pasar a la fase 2: el piloto cierra un período completo con las notas en la base de datos.

Siguientes fases: 2 núcleo escolar (asistencia, observador, horas sociales, matrícula, boletines y certificados), 3 familias y comunicación, 4 lista para vender (varios colegios, en internet, seguridad), 5 bienestar e inclusión, 6 administración del colegio, 7 app y modo sin conexión.
