# Kai Planeamiento · recorrido teórico G01

![DrillStone](../assets/L1.png)

**Proyecto:** Cerro Azul. **Datos publicados:** DS01/EXP03. **Alcance de esta rama:** E1 → S11 → S12 como comprensión conceptual con registro local por alias. Las actividades se identifican en `kai/ruta_teoria_v2.json` y `kai/misiones_teoria_v2.json`.

Esta guía no entrega cifras del modelo de Santa Elena. En G01 no se ha integrado ni validado una corrida cuantitativa S11/S12 bajo IMP-008. El registro de teoría no genera leyes, densidades, tonelajes, candidatos, escenarios, recursos o reservas del grupo. Tampoco genera la ficha E1 de 21 datos, la aplicación de 26 datos ni el ZIP individual completo; esos instrumentos requieren la adaptación y comprobación de los productos propios de G01.

## Secuencia del tutor

Kai explica el concepto, indica la fuente realmente disponible, plantea **una decisión y su razón por turno**, espera la respuesta, valora lo que el estudiante dijo y registra `DEMOSTRADO` solo con razonamiento propio. Un error o «no sé» recibe una pista y otra oportunidad. `registrar` controla estructura y orden, pero la valoración semántica corresponde al tutor; el Excel es una vista de SQLite. El alias es pseudónimo local, no autenticación institucional.

E1 comprende exploración, logueo, collar, survey, assay, compositación, geometría y modelo preliminar. Para hechos propios de G01, consultar `data/raw/release_manifest.json`, `docs/DATA.md` y los productos M01 del repositorio. Si aún falta un modelo preliminar, enseñarlo como concepto sin atribuirle resultados al grupo.

S11 contiene diez unidades de métodos y seis de aplicación conceptual. Vecino más cercano toma una observación elegible; IDW pondera varias por cercanía; un variograma estudia continuidad en distancia y dirección; kriging necesita continuidad y supuestos de media defendibles; cokriging exige relación espacial con una variable secundaria; la simulación condicional explora variabilidad entre realizaciones. Ninguno de esos nombres acredita una estimación propia. La elección del método y sus parámetros para G01 requieren la decisión académica y datos del grupo; el tutor no cambia reglas por conversación.

En una futura cuantificación, ley y densidad necesitan soporte propio, el tonelaje requiere volumen de roca y densidad compatibles, los faltantes quedan visibles y un radio de búsqueda más amplio no prueba calidad. Una imagen 3D no reemplaza el CSV completo ni la validación minera.

S12 usa **solo un microcaso conceptual identificado** hasta contar con S11 propio verificado. Un candidato a mineral necesita ley y tonelaje respaldados y criterios explícitos; sin clasificación no significa desmonte. Mina y planta tienen capacidades diferentes; tiempos de ciclo afectan flota; CAPEX y OPEX describen conceptos distintos; accesos, precedencias y estabilidad condicionan extracción. Comparar A/B no produce por sí solo un plan físico ni reservas profesionales.

## Fuentes y límites de G01

- Release: `data/raw/release_manifest.json` (DS01/EXP03).
- Datos M01: `data/raw/`, `data/processed/` y `outputs/` existentes en el repositorio; revisar su estado antes de citarlos.
- No se publica `.kai_local`, SQLite, Excel individual ni conversaciones.
- Para S11/S12 propios faltan integración científica, verificación por corrida y adaptación de visores e instrumentos de aplicación. No se rellenan campos con números de G05.
- La aceptación conversacional real en Copilot/PyCharm y la verificación visual interactiva siguen pendientes.

![DrillStone · símbolo](../assets/L3.png)
