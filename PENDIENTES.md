# Pendientes del dueño del proyecto

Cosas que solo puede hacer el dueño del proyecto (necesitan su cuenta, su firma o hablar con otras personas). Están en orden de prioridad.

## Ya mismo

- [x] **Supabase unido con Vercel.** La plataforma guarda los datos en el proyecto "App notas" de Supabase (50 tablas, con seguridad por filas).
- [ ] **Dominio propio** (cuando lo compres): Vercel → app-notas → **Settings → Domains → Add**.
- [ ] **Activar GitHub Pages.** Entra a https://github.com/santiagonzaleznieto-pixel/App-notas/settings/pages. En **Source** elige **Deploy from a branch**, en **Branch** elige **main** y la carpeta **/docs**, y oprime **Save**. La demo queda en https://santiagonzaleznieto-pixel.github.io/App-notas/
- [ ] **Preguntar al instructor del SENA** quién es dueño del código hecho en el proyecto de formación, antes de venderlo.

## Antes de usar datos reales del colegio piloto

- [ ] **Carta del Instituto Pijao** aceptando ser colegio piloto, con permiso para usar su nombre y su escudo.
- [ ] **Abogado:** revisar la política de datos (`/privacidad`), la autorización de los acudientes y el contrato de transmisión de datos entre el colegio (responsable) y la plataforma (encargada).
- [ ] **Datos reales del colegio:** código DANE, sedes, jornadas, fechas de los períodos, materias por grado y docentes. Se cargan desde Administración.
- [ ] **Publicar sin datos de prueba** (`DATOS_DE_EJEMPLO = "0"`), crear el colegio con `crear_colegio.py` y entregar a cada persona su usuario con clave temporal.

## Antes de vender

- [ ] **Nombre de la plataforma** (que no lleve el nombre de ningún colegio) y logo propio.
- [ ] **Validar los precios** del plan maestro hablando con al menos cinco rectores.
- [ ] **Crear la empresa** (por ejemplo una SAS) y sacar el RUT.
- [ ] **Registrar el software** en la Dirección Nacional de Derecho de Autor y la marca en la Superintendencia de Industria y Comercio.
- [ ] **Contador:** confirmar si los colegios privados deben emitir factura electrónica por las pensiones y cómo facturará la plataforma.
- [ ] **Pasarela de pagos** (por ejemplo PSE o Nequi) para el módulo de tesorería: requiere contrato con la empresa de pagos.
- [ ] **WhatsApp Business y correo** para los avisos automáticos: requieren cuentas propias de la empresa.

## Decisiones para revisar con el colegio piloto

Los módulos se construyeron con estas reglas. Conviene confirmarlas con la rectora y la coordinadora:

- [ ] La alerta de inasistencia continua cuenta días calendario y avisa a los 10, 20 y 30 días (la Resolución 5862 de 2024 ordena retirar del SIMAT después de 30 días sin justificar).
- [ ] La administración del colegio no ve anotaciones confidenciales de convivencia; solo coordinación, rectoría y orientación.
- [ ] Un estudiante no puede registrar más de 8 horas sociales en un mismo día.
- [ ] Las votaciones se abren y se cierran a mano; mientras están abiertas nadie ve el conteo.
- [ ] La cartera y el paz y salvo cuentan las deudas de todos los años.
- [ ] La enfermera también puede crear y actualizar fichas de salud; el acudiente debe marcar la autorización de datos para guardarla.
