# IMP-001 — Arquitectura mínima de M01

## 1. Identificación

- **Implementation ID:** IMP-001
- **Module:** M01 — PlanMinUPN
- **Date:** 2026-09-25
- **Group:** No especificado
- **Participants:** No especificados
- **Status:** IN_PROGRESS

---

## 2. Problema minero

Definir una arquitectura mínima y modular para trabajar con datos de
exploración de collar, survey, assay, lithology y density, manteniendo
separadas las responsabilidades de carga, validación, desurvey, positioning,
visualización y exportación antes de implementar lógica computacional.

---

## 3. Objetivo

Dejar preparado el esqueleto de M01 para que cada responsabilidad minera
pueda implementarse y validarse de forma independiente después de la
aprobación de esta etapa. `main.py` actuará únicamente como orquestador.

---

## 4. Inputs

| Variable | Significado | Unidad | Origen | Obligatorio | Validación |
|---|---|---|---|---|---|
| collar | Datos observados de collar | Según diccionario de datos | `data/raw/collar.csv` | Sí | Según plan de validación de Etapa 3 |
| survey | Mediciones downhole | Según diccionario de datos | `data/raw/survey.csv` | Sí | Según plan de validación de Etapa 3 |
| assay | Intervalos observados de ensayo | Según diccionario de datos | `data/raw/assay.csv` | Sí | Según plan de validación de Etapa 3 |
| lithology | Intervalos observados de litología | Según diccionario de datos | `data/raw/lithology.csv` | Sí | Según plan de validación de Etapa 3 |
| density | Observaciones de densidad | Según diccionario de datos | `data/raw/density.csv` | Sí | Según plan de validación de Etapa 3 |
| plan de validación | Criterios aprobados para controles computacionales | No aplica | Evidencia de Etapa 3 | Sí | Aprobado previamente |

No se fijan aquí unidades específicas no confirmadas en esta etapa; deberán
tomarse del diccionario de datos y del plan de validación aprobados.

---

## 5. Outputs

| Variable / resultado | Significado | Unidad | Destino |
|---|---|---|---|
| datos cargados | Fuentes observadas estructuradas para el flujo de M01 | Según fuente | Flujo interno hacia `validator.py` |
| resultado de validación | Controles, hallazgos y estado de aptitud | No aplica | Flujo interno y trazabilidad de M01 |
| trayectoria XYZ | Resultado de DESURVEY a partir de MD + azimuth + dip | Coordenadas según convenciones aprobadas | `data/processed/` mediante `exporter.py` |
| intervalos posicionados | Resultado de POSITIONING a partir de FROM/TO sobre una trayectoria | Coordenadas según convenciones aprobadas | `data/processed/` mediante `exporter.py` |
| visualizaciones | Representaciones de datos observados o derivados | No aplica | `outputs/` mediante `visualizer.py` |

Los formatos finales de los resultados derivados se definirán en las etapas
correspondientes y no se anticipan en esta arquitectura.

---

## 6. Supuestos

Las fuentes de `data/raw/` se consideran inmutables. Las convenciones de
DESURVEY, la autoridad en MD=0 y el método Minimum Curvature fueron aprobados
en Etapa 6; no se agregan supuestos geométricos adicionales.

---

## 7. Lógica minera

La arquitectura distingue explícitamente dos responsabilidades espaciales:

- **DESURVEY:** transforma `MD + azimuth + dip` de `survey`, junto con la
  referencia de `collar`, en una trayectoria XYZ del sondaje. El método,
  convenciones y reglas de cálculo no se deciden en IMP-001.
- **POSITIONING:** utiliza una trayectoria XYZ ya disponible para ubicar
  espacialmente intervalos definidos por `FROM/TO` de assay, lithology,
  density u otras fuentes confirmadas. No convierte mediciones de survey en
  trayectoria.

Las funciones de carga, validación, visualización y exportación se mantienen
separadas de esas transformaciones.

---

## 8. Diseño computacional

### Módulos / archivos

- `main.py`: orquestación, sin cálculo, validación ni dibujo.
- `src/m01/loader.py`: carga de fuentes observadas desde `data/raw/`.
- `src/m01/validator.py`: aplicación del plan de validación aprobado.
- `src/m01/desurvey.py`: contrato futuro para trayectoria XYZ.
- `src/m01/positioning.py`: contrato futuro para ubicar intervalos FROM/TO.
- `src/m01/visualizer.py`: contrato futuro para figuras o representaciones.
- `src/m01/exporter.py`: contrato futuro para persistencia de derivados y
  entregables.
- `tests/test_loader.py`: firmas de pruebas del cargador.
- `tests/test_validator.py`: firmas de pruebas del validador.

### Funciones / clases principales

En esta etapa solo se dejan firmas de funciones y docstrings de contrato.
No se implementa lógica funcional.

### Dependencias relevantes

No se agregan dependencias ni decisiones de librerías en IMP-001.

---

## 9. Etapas de implementación

### Etapa 1 — Inventario

- Objetivo: identificar las fuentes y evidencia disponibles.
- Trabajo realizado: inventario aprobado por el equipo.
- Resultado: fuentes reales disponibles en `data/raw/` y evidencia de
  auditoría disponible en `outputs/tables/T1_audit_summary_DS01_EXP03.xlsx`.
- Pendiente: ninguno dentro de esta etapa.

### Etapa 2 — Modelo conceptual

- Objetivo: definir el modelo conceptual de M01.
- Trabajo realizado: modelo conceptual aprobado por el equipo.
- Resultado: responsabilidades mineras separadas para el flujo de M01.
- Pendiente: traducir el modelo a contratos de módulos.

### Etapa 3 — Plan de validación

- Objetivo: definir los controles requeridos antes de avanzar.
- Trabajo realizado: plan de validación aprobado por el equipo.
- Resultado: base para `validator.py` y para las pruebas computacionales.
- Pendiente: implementación en Etapa 5.

### Etapa 4 — Arquitectura mínima

- Objetivo: crear la estructura exacta del repositorio y contratos de
  responsabilidad, input y output.
- Trabajo realizado: creación de stubs y firmas previstas, sin lógica real.
- Resultado: estructura preparada para revisión del equipo.
- Pendiente: aprobación del equipo y posterior Etapa 5.

### Etapa 5 — Carga y validación reproducible

- Objetivo: implementar `loader.py` y `validator.py` respetando los contratos
  aprobados.
- Trabajo realizado: `loader.py` lee las cinco fuentes requeridas mediante
  `csv.DictReader`, conserva los nombres y valores como texto, y no escribe
  en `data/raw/`. `validator.py` aplica los controles representados en la
  evidencia T1 para esquema, datos faltantes, relaciones por `hole_id`,
  intervalos y survey, y devuelve findings estructurados con severidad,
  tabla, fila, campo y valor observado.
- Resultado: carga completa reproducible; el dataset real produjo 0 findings
  `ERROR`, 0 `WARNING` y 0 `INFO` sobre 4,244 registros revisados.
- Pendiente: revisión y aprobación del Gate 5; no se inicia DESURVEY.

### Etapa 6 — Convenciones geométricas

- Objetivo: cerrar MD/Z, azimuth, dip, autoridad en MD=0 y método de
  desurvey.
- Trabajo realizado: se aprobó MINIMUM CURVATURE, se fijó survey en MD=0
  como autoridad de orientación y se resolvieron tres fixtures numéricos.
- Resultado: convenciones listas para implementación y trazabilidad.
- Pendiente: ninguno dentro de las decisiones geométricas aprobadas.

### Etapa 7 — DESURVEY y POSITIONING

- Objetivo: traducir las convenciones aprobadas a cálculo numpy vectorizado.
- Trabajo realizado: implementación de trayectoria Minimum Curvature, Ratio
  Factor con límite `beta ≈ 0` y posicionamiento curvo de FROM/MID/TO.
- Resultado: tests de fixtures y dataset real aprobados.
- Pendiente: revisión y aprobación del Gate 7; no iniciar visualizador ni
  exportador.

### Etapa 8 — Visualizador y exportador

- Objetivo: generar evidencia 3D interactiva, captura PNG automatizada y
  paquete CSV trazable para Datamine.
- Trabajo realizado: implementación de `visualizer.py` con Plotly, de
  `exporter.py` con Kaleido headless y de la orquestación en `main.py`.
  Cuando los derivados procesados no existían, `main.py` los generó una vez
  desde los módulos aprobados; visualizer.py y exporter.py solo leyeron los
  resultados ya escritos para producir sus salidas.
- Resultado: HTML, PNG y cuatro archivos Datamine generados para `DS01_EXP03`.
- Pendiente: revisión del equipo; no se ejecuta ningún commit o push.

---

## 10. Decisiones técnicas

### DECISION-01 — Separación de responsabilidades

**Responsabilidad:** `main.py` coordina el flujo; `loader.py` carga fuentes
observadas; `validator.py` aplica el plan de validación; `desurvey.py`
transforma mediciones downhole a trayectoria; `positioning.py` ubica
intervalos; `visualizer.py` representa resultados; `exporter.py` persiste
derivados y entregables.

**Input:** datos observados de collar, survey, assay, lithology y density en
`data/raw/`, más el plan de validación aprobado en Etapa 3.

**Output:** datos cargados, resultado estructurado de validación, trayectoria
XYZ, intervalos posicionados, visualizaciones y archivos derivados según el
contrato de cada módulo.

**Decisión:** mantener un módulo por responsabilidad y un `main.py` limitado
a orquestación. En Etapa 5 se implementaron `loader.py` y `validator.py`; en
Etapa 7 se implementaron únicamente `desurvey.py` y `positioning.py`.
Visualización y exportación permanecen como stubs.

### DECISION-02 — Distinción DESURVEY / POSITIONING

**Responsabilidad de DESURVEY:** convertir `MD + azimuth + dip` y la
referencia de `collar` en una trayectoria XYZ del sondaje mediante Minimum
Curvature y las convenciones aprobadas en Etapa 6.

**Responsabilidad de POSITIONING:** utilizar la trayectoria XYZ disponible
para asignar coordenadas XYZ a intervalos identificados mediante `FROM/TO`.
No convierte mediciones `MD + azimuth + dip` en trayectoria.

**Input:** `desurvey.py` recibe collar y survey validados; `positioning.py`
recibe la trayectoria y los intervalos FROM/TO de las fuentes observadas.

**Output:** `desurvey.py` entrega una trayectoria XYZ; `positioning.py`
entrega intervalos espacialmente posicionados, ambos con trazabilidad al
sondaje y a sus datos de origen.

### DECISION-03 — Límites de datos y etapas

`data/raw/` permanece como fuente inmutable. Los datos derivados se dirigirán
a `data/processed/` y los entregables a `outputs/`. `loader.py` y
`validator.py` se implementaron en Etapa 5; las convenciones y el método de
DESURVEY se cerraron en Etapa 6 y se implementaron en Etapa 7.

### DECISION-04 — Representación de datos cargados

`loader.py` devuelve un diccionario de tablas, donde cada tabla es una lista
de diccionarios producidos por `csv.DictReader`. Los nombres de columnas y
los valores permanecen como aparecen en los CSV; la conversión numérica se
realiza solo localmente dentro de `validator.py` para evaluar controles y no
para corregir o reemplazar los datos cargados.

### DECISION-05 — Alcance de reglas de Etapa 5

Se implementaron únicamente los controles observables en
`T1_audit_summary_DS01_EXP03.xlsx`: esquema, datos faltantes, relaciones
`hole_id`, orden/no negatividad/longitud/profundidad final/duplicados/solapes
de intervalos y controles de survey sobre inicio en cero, duplicados,
profundidad negativa/excedida y orientación a profundidad cero. Los controles
que la evidencia marca como `NOT_IMPLEMENTED`, como rangos de azimuth/dip y
gaps, no se agregaron.

### DECISION-06 — Convenciones geométricas de DESURVEY

MD es la distancia medida a lo largo del eje real del sondaje desde el
collar, mientras que Z es la coordenada vertical de elevación positiva hacia
arriba; MD representa longitud recorrida y Z representa posición vertical, por
lo que no son equivalentes salvo en un sondaje estrictamente vertical.

El sistema es `X = Easting`, `Y = Northing` y `Z = elevación positiva hacia
arriba`. El azimuth se mide desde el Norte en sentido horario:
`0° = Norte`, `90° = Este`, `180° = Sur`, `270° = Oeste`. El dip se mide
respecto de la horizontal: `0° = horizontal` y `-90° = vertical hacia abajo`.

### DECISION-07 — Autoridad en MD=0

El primer registro de survey con `MD = 0` es la autoridad geométrica para
azimuth y dip. El collar es la autoridad para la posición inicial
`(X₀, Y₀, Z₀)` y se utiliza como control de consistencia de la orientación.
Una discrepancia no se corrige silenciosamente: debe reportarse y revisarse.
Elegir una orientación incorrecta puede invertir el sentido vertical o
desplazar la trayectoria a otro cuadrante, acumulando errores en X, Y y Z.
T1 confirma estación survey en cero y coincidencia de orientación para los
32 sondajes del dataset.

### DECISION-08 — Minimum Curvature y Ratio Factor

Para cada par de estaciones se convierten azimuth y dip a vectores unitarios
`u_i = (E_i, N_i, V_i)`:

```text
E = cos(dip) * sin(azimuth)
N = cos(dip) * cos(azimuth)
V = sin(dip)
```

El dogleg se obtiene mediante el producto punto vectorizado:

```text
beta = arccos(clip(sum(u_i * u_{i+1}), -1, 1))
```

El Ratio Factor se calcula sin condicional por fila:

```text
RF = 1                                      si beta ≈ 0
     (2 / beta) * tan(beta / 2)             en otro caso
```

La implementación utiliza arrays completos, `np.einsum`, `np.where`,
`np.isclose`, trigonometría numpy y acumulación vectorizada por sondaje. No
usa bucles para calcular estación por estación o sondaje por sondaje.

### DECISION-09 — Posicionamiento dentro de un tramo curvo

Para `FROM`, `MID` y `TO`, `MID = (FROM + TO) / 2`. Cuando un MD cae dentro de
un tramo entre estaciones, no se interpola linealmente entre XYZ. Se usa la
forma de arco equivalente de Minimum Curvature: interpolación esférica de los
vectores unitarios de los extremos y su integración analítica sobre el
ángulo parcial. En el extremo completo, esta expresión reproduce exactamente
el incremento de Minimum Curvature con el mismo `RF`; para `beta > 0`, el
punto parcial no cae en la cuerda lineal. Cuando `beta ≈ 0`, se usa el límite
rectilíneo.

### DECISION-10 — Fixtures numéricos de control

Se conservaron los tres valores aprobados en Etapa 6 con
`(X₀, Y₀, Z₀) = (1000, 1000, 4000)`, `ΔMD = 10 m` y `atol = 1e-6`:

| Caso | Azimuth | Dip | XYZ esperado en MD=10 |
|---|---:|---:|---|
| Vertical | cualquiera | -90° | `(1000.000000, 1000.000000, 3990.000000)` |
| Horizontal Este | 90° | 0° | `(1010.000000, 1000.000000, 4000.000000)` |
| Inclinado Este | 90° | -45° | `(1007.071067812, 1000.000000, 3992.928932188)` |

### DECISION-11 — Visualización y exportación de Etapa 8

Se utiliza Plotly para la visualización 3D interactiva y Kaleido para la
exportación PNG headless. Plotly genera un HTML autocontenido con las capas
de collars, trayectorias y assay posicionado, ejes locales X/Y/Z, unidades y
leyenda. Kaleido se ejecuta en un proceso separado con timeout explícito para
evitar bloquear un pipeline sin pantalla; si falta o falla el backend, se
reporta un error explícito.

La figura utiliza resultados procesados y la referencia de collars para
dibujar; no recalcula desurvey ni positioning. Las coordenadas se presentan
exclusivamente como sistema cartesiano local, sin basemaps, latitud/longitud
ni afirmaciones de georreferenciación.

El paquete Datamine contiene `collar.csv`, `survey.csv`, `assay_xyz.csv` y
`field_mapping.csv`, con los campos de salida documentados explícitamente.

---

## 11. Archivos creados o modificados

```text
main.py
src/m01/loader.py
src/m01/validator.py
src/m01/desurvey.py
src/m01/positioning.py
tests/test_loader.py
tests/test_validator.py
tests/test_desurvey.py
tests/test_positioning.py
tests/test_visualizer.py
tests/test_exporter.py
requirements.txt
docs/implementation/IMP-001_m01_architecture.md
```

No se modificaron `loader.py`, `validator.py`, `desurvey.py`, `positioning.py`
ni `data/raw/` durante Etapa 8.

---

## 12. Pruebas realizadas

### Comandos ejecutados

```text
C:\PM\.venv\Scripts\python.exe -m pytest C:\PM\PlanMinUPN-01\tests\test_loader.py C:\PM\PlanMinUPN-01\tests\test_validator.py -q
C:\PM\.venv\Scripts\python.exe -m pytest C:\PM\PlanMinUPN-01\tests\test_desurvey.py C:\PM\PlanMinUPN-01\tests\test_positioning.py -q
C:\PM\.venv\Scripts\python.exe -m pytest C:\PM\PlanMinUPN-01\tests\test_visualizer.py C:\PM\PlanMinUPN-01\tests\test_exporter.py -q
C:\PM\.venv\Scripts\python.exe -m pytest C:\PM\PlanMinUPN-01\tests -q
C:\PM\.venv\Scripts\python.exe C:\PM\PlanMinUPN-01\main.py
```

### Resultado real

- **Status:** PASS
- **Tests passed:** 4
- **Tests failed:** 0

La suite espacial pasó con 6 tests y la suite completa pasó con 10 tests. La
validación adicional del dataset completo reportó 208 estaciones, 32
sondajes y 3,619 intervalos posicionados; MD fue monótono dentro de cada
sondaje, todas las estaciones quedaron dentro de `final_depth_m`, XYZ fue
finito y `MID = (FROM + TO) / 2`. Se instalaron `numpy` y `pytest` en el
entorno virtual porque no estaban disponibles; `numpy` quedó declarado en
`requirements.txt`.

La primera ejecución histórica falló por `ModuleNotFoundError: No module named 'src'`
al invocar pytest desde `C:\PM`; se corrigió el descubrimiento de la raíz del
repositorio en los propios archivos de prueba y la segunda ejecución pasó.
También se ejecutó `py_compile` sobre los archivos espaciales y sus pruebas,
con resultado exitoso.

La suite de visualización/exportación pasó con 2 tests y la suite completa
posterior pasó con 12 tests. El pipeline completo terminó con código de
salida 0 y generó:

```text
data/processed/drillhole_trajectory.csv
data/processed/assay_xyz.csv
outputs/figures/m01_drillholes_3d_DS01_EXP03.html
outputs/figures/m01_drillholes_3d_DS01_EXP03.png
outputs/datamine/collar.csv
outputs/datamine/survey.csv
outputs/datamine/assay_xyz.csv
outputs/datamine/field_mapping.csv
```

El PNG se produjo mediante Kaleido en un proceso headless separado con
timeout de 30 segundos; no requirió interacción ni pantalla.

---

## 13. Validación minera

- [x] Unidades consistentes para los controles implementados según el
  diccionario y T1.
- [ ] Signos económicos correctos cuando corresponda.
- [ ] Magnitudes razonables.
- [ ] Restricciones operacionales respetadas.
- [ ] Casos extremos revisados.
- [ ] Caso manual independiente revisado cuando es posible.

### Evidencia / comentario

La validación del dataset completo no produjo findings. Los valores numéricos
originales no se modifican; se convierten temporalmente solo para comparar
intervalos y profundidades. Las reglas de azimuth/dip no implementadas en T1
siguen pendientes de una decisión aprobada.

---

## 14. Limitaciones y pendientes

### LIMITATION-01

No existe fuente topográfica confirmada en `data/raw/` o `data/processed/`;
por ello se omitió explícitamente esa capa. La figura incluye collars,
trayectorias y assay posicionado.

### FUTURE-01

El paquete Datamine es un contraste CSV trazable; su carga efectiva en
Datamine Studio requiere confirmación externa del equipo.

---

## 15. Uso del agente de IA

- [ ] Explicación conceptual.
- [x] Arquitectura.
- [ ] Algoritmo.
- [x] Implementación.
- [x] Pruebas.
- [ ] Depuración.
- [ ] Revisión de unidades.
- [x] Documentación.

Comentario:

Se utilizó IA para implementar la carga y validación, traducir
vectorizadamente Minimum Curvature y posicionamiento curvo, preparar fixtures
numéricos y pruebas sobre datos reales, implementar Plotly/Kaleido headless,
generar el paquete CSV trazable y documentar resultados. No se modificó
`data/raw/`, `loader.py` ni `validator.py` en Etapas 7 y 8.

---

## 16. Checklist de cierre

- [x] Problema minero documentado.
- [x] Inputs documentados.
- [x] Unidades verificadas.
- [x] Supuestos identificados.
- [x] Lógica minera documentada.
- [x] Implementación de Etapa 5 realizada.
- [x] Pruebas ejecutadas.
- [x] Validación computacional realizada.
- [x] Validación minera realizada para los invariantes geométricos cubiertos.
- [x] Archivos modificados registrados.
- [x] Limitaciones registradas.
- [x] Registro actualizado para la etapa de arquitectura.

El registro permanece en estado `IN_PROGRESS` hasta la revisión del equipo.
No se ejecuta commit, pull, rebase ni push sin autorización.
