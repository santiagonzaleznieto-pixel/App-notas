# Plataforma de gestión escolar

Plataforma web en Python con Flask y SQLite para manejar todo un colegio colombiano: notas, asistencia, convivencia, horas sociales, certificados, familias, circulares, orientación, elecciones, tesorería y servicios escolares. Se venderá a instituciones públicas y privadas, de Transición a Once. Empezó como proyecto de clase del SENA con las notas de Décimo de la Institución Educativa Instituto Pijao (Pijao, Quindío), que ahora es el **colegio piloto**.

- Repositorio: https://github.com/santiagonzaleznieto-pixel/App-notas (público, rama `main`)
- En internet (Vercel, proyecto `app-notas`, se publica solo con cada cambio en `main`): https://app-notas-weld.vercel.app
- Demo de solo lectura (GitHub Pages, carpeta `docs`): https://santiagonzaleznieto-pixel.github.io/App-notas/
- Plan maestro (visión, ley, roles, módulos, fases): https://claude.ai/artifact/QQYMz3DWLH2gvuDGn6a4yu

Este repositorio es solo para la plataforma escolar. El sitio del restaurante Amo Pijao Terraza es otro proyecto, en otro repositorio y otra sesión: no se mezclan.

## Reglas para trabajar en este proyecto

- Todo en español: nombres de variables, funciones, rutas, tablas, columnas y textos de la página.
- No escribir comentarios en el código. Solo lo necesario.
- Mantenerlo sencillo. Se permiten: variables, `if`/`elif`/`else`, `for`, `while`, listas, diccionarios, funciones (`def`), Flask (incluidos sus decoradores como `@app.route`, `@app.before_request`), `sqlite3`, `werkzeug.security` y módulos estándar simples (`os`, `datetime`, `secrets`).
- Evitar lo que no se ha visto: clases propias, `lambda`, listas por comprensión, `try`/`except`, `with`, operador ternario, `sorted` con `key`, decoradores propios, f-strings (se usa `+` y `str()`), librerías externas.
- Todo debe servir para cualquier colegio: cada tabla lleva `colegio_id` y cada consulta comprueba que el registro es del colegio del usuario (`g.colegio["id"]`). Nunca confiar en ids que llegan por la URL o el formulario.
- Lo que cambia de un colegio a otro (escala, períodos, grados, materias, sedes) se guarda en la base de datos, no en el código.
- Base de datos: SQLite en el computador y PostgreSQL (Supabase) en internet. El código se escribe para SQLite (con `?`) y `base_datos.py` lo traduce solo a PostgreSQL cuando existe la variable `URL_BASE_DATOS`. Única librería externa permitida además de Flask: `psycopg` (para hablar con PostgreSQL), y solo dentro de `base_datos.py`.
- Nunca hablar directo con la conexión: usar `base_datos.consultar`, `consultar_uno`, `ejecutar`, o `base_datos.en(conexion, sql, valores)` cuando se necesite una transacción. Escribir SQL que funcione en las dos bases: `GROUP BY` con todas las columnas que no son de suma o conteo, `ORDER BY` cuando el orden importe, y nada de funciones de fecha de SQLite (las fechas se calculan en Python con `nucleo.hoy()`).
- El repositorio es público: nunca escribir claves ni contraseñas reales en el código.
- Mantener el diseño (ver "Diseño"). Todo debe verse bien en celular.
- Soy principiante: explica cada cambio con palabras sencillas y dime cómo probarlo.

## Cómo se ejecuta (Windows, terminal de VS Code)

Desde la carpeta del proyecto:

```
py -m pip install flask
py app.py
```

Abrir http://127.0.0.1:5000. La primera vez se crea `plataforma.db` (al lado de `base_datos.py`) con los datos de `datos.py` y los ejemplos de cada módulo. Para volver a empezar: cerrar el programa, borrar `plataforma.db` y abrirlo otra vez. Si cambia la estructura de alguna tabla, también hay que borrar `plataforma.db`.

Pruebas automáticas (una por módulo): `py pruebas/prueba_notas.py`, `py pruebas/prueba_admin.py`, etc. Cada una usa una base temporal y no toca `plataforma.db`. Para probar con PostgreSQL: definir `URL_PRUEBAS_POSTGRES` (por ejemplo `postgresql://postgres:clave@127.0.0.1:5432/postgres`); cada prueba crea su propia base `prueba_...`.

## Arquitectura

- `app.py`: arranca la plataforma; solo importa los módulos. El orden de los `import` es el orden del menú.
- `nucleo.py`: crea la app de Flask, prepara la base, carga la sesión (`g.yo`, `g.colegio`), permisos (`tiene_rol`, `tiene_alguno`, `puede_ver_grupo`, `puede_ver_estudiante`, `puede_anotar_estudiante`, `dicta_en_grupo`), escala (`desempeno`), promedios (`promedio`, `nota_final` con porcentajes), `numero()` para leer números sin `try`, `registrar()` para el registro de accesos, el menú (`agregar_menu`) y la seguridad (formularios de otros sitios, cabeceras, cookies, cambio obligatorio de clave temporal).
- `base_datos.py`: conexión y funciones del núcleo (`consultar`, `consultar_uno`, `ejecutar`, `crear_tablas`) y tablas del núcleo.
- `semilla.py` y `datos.py`: datos iniciales del colegio piloto (solo se usan si la base está vacía).
- `modulo_*.py`: un archivo por módulo con sus tablas (`TABLAS_...` + `crear_tablas`), sus datos de ejemplo (`sembrar_...`), su entrada al menú y sus rutas. Sus plantillas empiezan por el nombre del módulo y su CSS extra va en `static/<modulo>.css`.
- `templates/base.html`: barra, menú automático según los roles, bloques `contenido` (con sesión), `publico` (sin sesión) y `estilos`.
- `generar_demo.py`: crea la demo de solo lectura en `docs/` recorriendo la plataforma como cada usuario de acceso rápido. Correrlo (`py generar_demo.py`) después de cambiar diseño, módulos o datos de prueba.
- `pruebas/`: `ayuda.py` (base temporal, `entrar`, `revisar`) y una prueba por módulo.

## Módulos (archivo · rutas principales · tablas propias)

| Módulo | Rutas | Tablas |
| --- | --- | --- |
| `modulo_inicio.py` | `/`, `/inicio`, `/mi-cuenta`, `/privacidad`, `/sin-conexion`, `/sw.js`, `/salir` | (núcleo) |
| `modulo_notas.py` | `/mis-clases`, `/calificar/<asignacion>`, `/grupos`, `/grupos/<id>`, `/boletin/<estudiante>`, `/mis-notas` | (núcleo) |
| `modulo_tablero.py` | `/indicadores` | ninguna (lee las de otros módulos si existen) |
| `modulo_familias.py` | `/familia`, `/escuela-familias`, `/escuela-familias/<id>`, `/escuela-familias/caracterizacion` | `compromisos_familia`, `encuentros_familias`, `asistencia_encuentros`, `caracterizacion_familias` |
| `modulo_circulares.py` | `/circulares`, `/circulares/nueva`, `/circulares/<id>`, `/agenda` | `circulares`, `lecturas_circular`, `eventos` |
| `modulo_asistencia.py` | `/asistencia`, `/asistencia/tomar/<asignacion>`, `/asistencia/grupo/<id>`, `/asistencia/estudiante/<id>`, `/asistencia/excusas`, `/mi-asistencia` | `asistencia`, `excusas` |
| `modulo_observador.py` | `/observador`, `/observador/estudiante/<id>`, `/observador/caso/<id>`, `/convivencia` | `observaciones`, `seguimientos`, `pasos_protocolo` |
| `modulo_horas.py` | `/horas`, `/horas/proyecto/<id>`, `/mis-horas`, `/horas/estudiante/<id>` | `proyectos_sociales`, `inscripciones_sociales`, `horas_registradas` |
| `modulo_certificados.py` | `/certificados`, `/certificados/<codigo>`, `/verificar` (pública) | `certificados` |
| `modulo_orientacion.py` | `/orientacion`, `/orientacion/estudiante/<id>`, `/orientacion/remitir`, `/piar`, `/piar/<id>` | `atenciones_orientacion`, `remisiones_docentes`, `piar`, `piar_ajustes` |
| `modulo_gobierno.py` | `/elecciones`, `/elecciones/<id>/votar`, `/elecciones/<id>` | `elecciones`, `candidatos`, `votantes`, `votos` |
| `modulo_tesoreria.py` | `/tesoreria`, `/tesoreria/conceptos`, `/tesoreria/generar`, `/tesoreria/estudiante/<id>`, `/tesoreria/recibo/<n>`, `/tesoreria/paz-y-salvo/<id>`, `/tesoreria/cartera`, `/mis-pagos` | `conceptos_cobro`, `cobros`, `pagos`, `descuentos`, `parametros_tesoreria` |
| `modulo_servicios.py` | `/biblioteca`, `/enfermeria`, `/mi-ficha-salud`, `/porteria`, `/autorizados` | `libros`, `prestamos`, `fichas_salud`, `atenciones_enfermeria`, `autorizados_recoger`, `salidas`, `ingresos_visitantes` |
| `modulo_admin.py` | `/admin`, `/admin/colegio`, `/admin/sedes`, `/admin/periodos`, `/admin/materias`, `/admin/grupos`, `/admin/usuarios`, `/admin/cargue`, `/admin/registro` | (núcleo) |

Reglas de privacidad que no se deben romper:
- Orientación: las atenciones solo las ve el rol `orientador`; rectoría y coordinación ven cifras sin nombres.
- Enfermería: las fichas de salud solo las ven `enfermeria` y los acudientes del estudiante. Nunca poner datos de salud en el registro de accesos.
- Convivencia: casos tipo II y III y anotaciones confidenciales solo para coordinación, rectoría, orientación y su autor; familias y estudiantes solo ven que hay un caso en manejo.
- Elecciones: la tabla `votos` no guarda quién votó y `votantes` no guarda por quién; los votos se cuentan y muestran solo al cerrar la votación.
- Administración: la secretaría no gestiona usuarios con roles directivos ni con datos sensibles (`ROLES_SOLO_ADMINISTRADOR`).
- Tesorería: solo tesorería, administración, rectoría y los acudientes del estudiante ven datos de pagos.

Las pruebas de cada módulo fijan la fecha (`nucleo.hoy`) para no depender del reloj. Varias funciones de ayuda (`fecha_valida`, `entero`, etc.) están repetidas en varios módulos: pasarlas a `nucleo.py` es una limpieza pendiente.

## Tablas del núcleo

`colegios` (datos y escala), `sedes`, `grados` (Transición a Once, con `orden`), `usuarios` (clave cifrada, `activo`, `debe_cambiar_clave`), `roles_usuario` (varios roles por persona), `grupos` (por año, con director), `matriculas` (estudiante en grupo por año, `activa` o `retirada`), `acudientes` (acudiente ↔ estudiante con parentesco), `materias`, `asignaciones` (grupo + materia + docente + horas), `periodos` (fechas, porcentaje, abierto o cerrado), `notas` (año, estudiante, materia, período, valor; `NULL` = pendiente), `registro_accesos`.

## Roles

`administrador`, `rector`, `coordinador`, `docente`, `secretaria`, `orientador`, `estudiante`, `acudiente`, `tesoreria`, `bibliotecario`, `enfermeria`, `porteria`. `director` no se guarda: se agrega solo cuando el docente dirige un grupo del año. Una persona puede tener varios roles.

Usuarios de prueba (contraseña `pijao2026`, `CLAVE_PRUEBA` en `datos.py`): `admin`, `rectora`, `coordinadora`, `h.aguirre` (director de 10-A, Sociales y Filosofía), `c.munoz` (Matemáticas), `s.grajales` (directora de 11-A), `secretaria`, `orientadora`, `melany.osorio` y 9 estudiantes más en 10-A, `esteban.ramirez` y 5 más en 11-A, acudientes `gloria.cardenas` (madre de Melany), `jorge.restrepo`, `olga.gomez`, y `tesoreria`, `biblioteca`, `enfermeria`, `porteria`.

Los botones de acceso rápido solo aparecen en modo pruebas: sin la variable `CLAVE_SECRETA`, o con `MODO_PRUEBAS=1`.

## Reglas de las notas

- Escala por colegio (en `colegios`): por defecto de 1.0 a 5.0. Desempeño (escala nacional del Decreto 1290 de 2009): Bajo menos de 3.0, Básico desde 3.0, Alto desde 4.0, Superior desde 4.6, Pendiente si no hay nota.
- Nota final de una materia: promedio ponderado por el porcentaje de cada período, solo con los períodos que tienen nota.
- Promedio general: promedio de las materias. Puesto: 1 + compañeros con mejor promedio (los empates comparten puesto).
- Los docentes solo cambian notas de períodos abiertos.

## Dónde se usa cada tema de clase

- Secuenciales: `datos.py`.
- `while`: `enlaces_internos` en `generar_demo.py`, `ordenar_de_mayor_a_menor` en `modulo_tablero.py`, la generación de usuarios y códigos únicos (administración, certificados, recibos).
- `if` / `elif` / `else`: `desempeno`, el login, los permisos de cada ruta, el mensaje del boletín.
- `for`: promedios, puestos, alertas, resúmenes, guardar notas, sembrar datos.
- Funciones: un archivo `modulo_*.py` por módulo, con una función por consulta y por ruta.

## Diseño

- Colores: azul `#1E3A5F`, azul oscuro `#122844`, verde cafetero `#3F6B4A`, verde oscuro `#2C4E35`, terracota `#BD5B2E`, dorado `#C98A2B`, crema `#FBF8F2`.
- Fuentes: Fraunces (títulos) e Inter (texto), desde Google Fonts.
- Montañas del Paisaje Cultural Cafetero en el login y franja bajo la barra superior.
- Gráficas de indicadores (`static/tablero.css`): niveles Bajo `#B4532A`, Básico `#D29A2E`, Alto `#53A86E`, Superior `#1B7444`, Pendiente `#D9D3C7` (paleta validada para daltonismo), barras de máximo 24 px, separación de 2 px, leyenda y tabla de datos.

## Publicación

- Demo en GitHub Pages: carpeta `docs/` de la rama `main` (páginas fijas; no se inicia sesión de verdad ni se guarda nada).
- Plataforma en internet: Vercel (conectado al repositorio de GitHub) con la base de datos en Supabase. Supabase: proyecto "App notas" (región us-west-2); Vercel corre en `pdx1` (Portland) para estar al lado. Variables en Vercel: `URL_BASE_DATOS` (cadena de conexión de Supabase) o `POSTGRES_URL` (la crea sola la integración Supabase ↔ Vercel; `base_datos.limpiar_url` le quita los parámetros que PostgreSQL no entiende), `CLAVE_SECRETA`, `MODO_PRUEBAS=1` solo para demos y `AVISO_DEMO` (texto de la franja de aviso). Sin `URL_BASE_DATOS`, en Vercel la base va a `/tmp` y se borra sola. Alternativa: PythonAnywhere (pasos en `README.md`).
- Arranque en PostgreSQL: la creación de tablas va en fila (bloqueo de transacción) y solo el primer servidor que se apunta en `control_siembra` carga los datos de prueba (`nucleo.SEMBRAR`). Los módulos siembran con `if SEMBRAR:`.
- Hora: `nucleo.hoy()` y `nucleo.ahora()` usan siempre la hora de Colombia (UTC-5), aunque el servidor esté en otro país.
- `/privacidad`: política de tratamiento de datos (borrador para revisión de un abogado).

## Estado

Fases 1, 2, 3, 5 y 6 construidas con pruebas (13 pruebas, más de 1.000 revisiones). Fase 4: seguridad, política de datos (borrador), modo real y `crear_colegio.py` listos; falta publicar en PythonAnywhere y la revisión legal. Fase 7: app instalable y aviso sin conexión listos; falta el modo sin conexión para asistencia y notas, y los avisos por WhatsApp y correo. Ver la sección "Avance" del plan maestro y los pendientes del dueño en `PENDIENTES.md`.
