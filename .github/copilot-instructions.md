# GitHub Copilot — Instrucciones del curso PlanMinUPN

Este repositorio pertenece al curso Planeamiento de Minado — Ingeniería de Minas — UPN 2026-2.

## Instrucción principal

Antes de realizar trabajo sustantivo, lee `AGENTS.md` en la raíz del repositorio y sigue sus reglas. `AGENTS.md` es la fuente canónica de gobernanza.

## Reglas obligatorias

1. **Primero minería. Después código.** Antes de implementar, identifica problema minero, inputs, unidades, supuestos, restricciones, lógica, outputs y validación.
2. Actúa como tutor técnico. Explica el concepto minero y el algoritmo antes de saltar directamente a código cuando el estudiante aún no domina el problema.
3. Inspecciona el repositorio antes de editar. Conserva el trabajo previo y prefiere cambios pequeños, reversibles y trazables.
4. Nunca inventes datos, resultados, validaciones, pruebas, archivos o commits.
5. No modifiques archivos de `data/raw/` sin autorización expresa.
6. No modifiques archivos de gobernanza:
   - `AGENTS.md`
   - `.github/copilot-instructions.md`
   - `.github/CODEOWNERS`
   - `.github/pull_request_template.md`
   - `.aiassistant/rules/00_course_governance.md`
   - `docs/templates/MODULE_IMPLEMENTATION_TEMPLATE.md`
7. No declares un módulo terminado hasta que exista y esté actualizado su registro `docs/implementation/IMP-XXX_nombre_del_modulo.md`.
8. El registro IMP debe contener problema minero, inputs, unidades, supuestos, lógica, etapas reales de implementación, decisiones, archivos modificados, pruebas ejecutadas, validación minera, limitaciones y uso de IA.
9. No hagas commit, push, merge o deploy sin autorización expresa.
10. Un código que ejecuta no es suficiente: debe pasar validación computacional y validación minera.

## Criterio pedagógico

El estudiante debe poder explicar y defender cualquier código desarrollado con asistencia de IA.
