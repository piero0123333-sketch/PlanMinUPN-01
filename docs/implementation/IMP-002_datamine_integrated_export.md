# IMP-002 — Salida integrada compatible con Datamine

## 1. Identificación

- **Implementation ID:** IMP-002
- **Module:** M01 — Exportación integrada para Datamine
- **Date:** 2026-09-26
- **Status:** IN_PROGRESS

## 2. Problema minero

Facilitar el intercambio de intervalos de sondaje entre el proyecto y
Datamine mediante una tabla integrada con las cabeceras esperadas por la
visualización de taladros, sin modificar las fuentes observadas.

## 3. Objetivo

Generar una salida CSV con las cabeceras `DH` y añadir atributos de tablas
auxiliares solamente cuando la fuente tenga registros y el atributo contenga
datos.

## 4. Inputs y unidades

| Fuente | Variables principales | Unidad |
|---|---|---|
| `assay_xyz.csv` | intervalos, Cu, coordenadas de punto medio | m, % |
| `collar.csv` | profundidad final, azimut, dip | m, grados |
| `lithology.csv` | código litológico por intervalo | código |
| `density.csv` | densidad de muestras | t/m3 |
| `alteration.csv` | código e intensidad de alteración | código/texto |

## 5. Lógica y supuestos

- `BHID = hole_id`, `FROM = from_m`, `TO = to_m`.
- `ENDDEPTH` proviene de `collar.final_depth_m`.
- `X`, `Y`, `Z` son las coordenadas `x_mid`, `y_mid`, `z_mid`.
- `A0` es el azimut del collar.
- `B0 = abs(dip_deg)`, porque Datamine trabaja con la magnitud positiva
  después de aplicar la convención de signo.
- `RADIUS = 1` es un parámetro visual, no un diámetro físico.
- Una tabla auxiliar se asocia al intervalo base por sondaje y punto medio.
- Si una tabla auxiliar está vacía, sus columnas no se generan.
- Si un intervalo auxiliar coincide de forma ambigua con un intervalo base, la
  exportación falla explícitamente en lugar de seleccionar silenciosamente.

## 6. Output

`outputs/datamine/drillholes_datamine.csv`, con las 16 cabeceras base DH y
atributos auxiliares activos, actualmente `density_sample_id` y
`density_t_m3`. Las columnas de alteración no se incluyen porque
`alteration.csv` no tiene registros.

## 7. Visualización y estabilidad geométrica

El visualizador 3D ahora agrupa los intervalos por `LITH_CODE`, asigna una
leyenda y color por litología y muestra en el cursor sondaje, FROM/TO, Cu, Mo,
Au, densidad y coordenadas XYZ. Las tablas auxiliares se leen sin modificar
`data/raw/`; sus atributos solo se muestran cuando existen.

La figura HTML incorpora controles para alternar entre capas de litología,
leyes de Cu clasificadas en baja/media/alta, densidades clasificadas en
baja/media/alta y alteración cuando existen registros. Los valores de
densidad se normalizan a texto numérico o vacío antes de mostrarse, evitando
que una unidad o etiqueta textual sea interpretada como el atributo.

La interfaz de la figura separa el control de la vista **3D** del control de
**Leyendas**. Las leyendas de leyes y densidades incluyen los límites numéricos
de cada intervalo (`Baja`, `Media` y `Alta`), calculados con el mínimo y máximo
observados de cada variable y divididos mediante `Equal Interval`, como en
Datamine. Los límites se muestran con dos decimales, mientras la clasificación
usa los valores completos para evitar errores por redondeo. También se puede
mostrar u ocultar el panel de leyendas sin ocultar la geometría.

Para densidad se mantiene una única representación visible: el rango numérico
(`mínimo – máximo t/m³`). La densidad puntual original se utiliza internamente
para clasificar los intervalos, pero no se duplica en la leyenda ni en el
cursor.

La capa de leyes de Cu utiliza una escala continua `Viridis` con límites fijos
en los percentiles 1 y 99 de los valores disponibles, reduciendo la influencia
visual de valores extremos sin eliminarlos de los datos. El dashboard HTML
también incluye un histograma de distribución de leyes y perfiles down-hole de
Cu frente a la profundidad media de cada intervalo. El código de litología
por intervalo proviene de `data/raw/lithology.csv`, por lo que la leyenda
categórica, el toggle de litología y el hover enriquecido se encuentran
habilitados.

Se corrigió además el tratamiento numérico de tramos con curvatura
prácticamente nula. El ángulo obtenido por redondeo de punto flotante podía
ser pequeño pero no cero, provocando inestabilidad en la fórmula de arco y
coordenadas repetidas. Esos tramos ahora usan la solución lineal estable.
Los archivos derivados se regeneran para evitar conservar resultados
obsoletos después de una corrección geométrica.

## 8. Archivos modificados

- `src/m01/exporter.py`
- `main.py`
- `tests/test_exporter.py`
- `src/m01/desurvey.py`
- `src/m01/positioning.py`
- `src/m01/visualizer.py`
- `tests/test_positioning.py`
- `tests/test_visualizer.py`
- `docs/implementation/IMP-002_datamine_integrated_export.md`

## 9. Validación

`pytest`: 13 tests passed.

La comparación contra `SG.csv` produjo 3,181 intervalos comunes, con
diferencia máxima de `9.1e-9 m`, diferencia media de `4.8e-9 m` y cero
intervalos con diferencia mayor a 1 m.

Las fuentes de `data/raw/` permanecieron sin cambios.

## 10. Limitaciones

La salida mantiene una fila por intervalo de ensayo. Si una fuente auxiliar
tiene varios registros dentro del mismo intervalo base, se considera una
ambigüedad y no se resume ni duplica automáticamente.
