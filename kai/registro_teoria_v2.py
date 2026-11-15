#!/usr/bin/env python3
"""Continuidad del recorrido TEÓRICO E1/S11/S12, aislada del registro V1.

No estima propiedades mineras ni valida semánticamente respuestas. El tutor
valora la evidencia; SQLite conserva esa valoración y Excel es una vista.
La interfaz de tutoría usa JSON como datos y un comando constante.
"""
from __future__ import annotations

import datetime as dt
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import uuid

import xlsx_simple as legado

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / '.kai_local'
SOLICITUD = RAIZ / '.kai_solicitud_teoria_v2.json'
CONFIG = json.loads((RAIZ / 'kai/config_teoria_v2.json').read_text(encoding='utf-8'))
ROUTE_ID = CONFIG['route_id']
VERSION = CONFIG['route_version']
ETAPAS = ['E1', 'S11', 'S12']
RUTA = json.loads((RAIZ / CONFIG['ruta_inicial']).read_text(encoding='utf-8'))
MISIONES = json.loads((RAIZ / CONFIG['misiones']).read_text(encoding='utf-8'))
ACTIVIDADES = RUTA['actividades'] + MISIONES['S11'] + MISIONES['S12']
POR_ID = {a['id']: a for a in ACTIVIDADES}
if len(POR_ID) != len(ACTIVIDADES):
    raise ValueError('Identificadores de contenido duplicados')
ALIAS_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{2,39}$')
ESTADOS = {'DEMOSTRADO', 'EN_DESARROLLO', 'REQUIERE_REFUERZO'}
ACCIONES = {'PREGUNTAR_PENDIENTE', 'REFORZAR', 'COMPROBAR_TRANSFERENCIA'}
GENERICAS = {'si', 'sí', 'no', 'listo', 'entiendo', 'entendido', 'ok', 'ya', 'de acuerdo', 'no sé', 'no se'}
COMUNES = {'operacion', 'alumno', 'route_id', 'route_version'}
CAMPOS = {
    'estado': set(), 'verificar': set(),
    'perfil': {'consentimiento', 'nombre', 'kai'},
    'iniciar_etapa': {'etapa', 'base'},
    'registrar': {'actividad', 'estado', 'respuesta', 'criterio_observado', 'tipo_evidencia',
                  'observacion_visor'},
    'checkpoint': {'actividad', 'comprension_parcial', 'pregunta_respondida',
                   'pregunta_pendiente', 'dificultad_pendiente', 'proxima_accion',
                   'evidencia_estudiante'},
}


def texto(value, campo, maximo=3500, vacio=False):
    if not isinstance(value, str) or (not vacio and not value.strip()):
        raise ValueError(f'{campo}: se requiere texto')
    if len(value) > maximo or any(ord(c) < 32 and c not in '\n\r\t' for c in value):
        raise ValueError(f'{campo}: longitud o caracteres no admitidos')
    return value


def normalizar(value):
    return re.sub(r'\s+', ' ', value.strip().casefold()).strip(' .!¡?¿')


def carpeta(alias):
    if not isinstance(alias, str) or not ALIAS_RE.fullmatch(alias):
        raise ValueError('Alias inválido: use 3–40 caracteres, letras, números, _ o -')
    destino = DATA / alias
    if destino.resolve().parent != DATA.resolve():
        raise ValueError('La carpeta individual queda fuera del registro local')
    return destino


def abrir(alias):
    destino = carpeta(alias)
    destino.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(destino / 'teoria_v2.sqlite', timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout=10000')
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS eventos_v2 (
            id TEXT PRIMARY KEY, fecha TEXT NOT NULL, route_id TEXT NOT NULL,
            route_version INTEGER NOT NULL, etapa TEXT NOT NULL,
            actividad TEXT NOT NULL, estado TEXT NOT NULL
                CHECK(estado IN ('DEMOSTRADO','EN_DESARROLLO','REQUIERE_REFUERZO')),
            respuesta TEXT NOT NULL, criterio_observado TEXT NOT NULL,
            tipo_evidencia TEXT NOT NULL, huella TEXT UNIQUE NOT NULL,
            observacion_visor TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS checkpoints_v2 (
            id TEXT PRIMARY KEY, fecha TEXT NOT NULL, route_id TEXT NOT NULL,
            route_version INTEGER NOT NULL, etapa TEXT NOT NULL, actividad TEXT NOT NULL,
            comprension_parcial TEXT NOT NULL, pregunta_respondida TEXT NOT NULL,
            pregunta_pendiente TEXT NOT NULL, dificultad_pendiente TEXT NOT NULL,
            proxima_accion TEXT NOT NULL, evidencia_estudiante TEXT NOT NULL,
            huella TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS inicios_v2 (
            fecha TEXT NOT NULL, route_id TEXT NOT NULL, route_version INTEGER NOT NULL,
            etapa TEXT NOT NULL, base TEXT NOT NULL,
            PRIMARY KEY(route_id,route_version,etapa));
        CREATE TABLE IF NOT EXISTS perfil_v2 (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
    ''')
    # Bases V2 anteriores conservan sus eventos; el campo nuevo queda vacío.
    columnas = {r[1] for r in conn.execute('PRAGMA table_info(eventos_v2)')}
    if 'observacion_visor' not in columnas:
        conn.execute("ALTER TABLE eventos_v2 ADD COLUMN observacion_visor TEXT NOT NULL DEFAULT ''")
    conn.commit()
    return conn


def filas(conn, tabla):
    # Los nombres provienen únicamente de constantes del módulo.
    if tabla not in {'eventos_v2', 'checkpoints_v2', 'inicios_v2'}:
        raise ValueError('Tabla no permitida')
    return [dict(r) for r in conn.execute(
        f'SELECT * FROM {tabla} WHERE route_id=? AND route_version=? ORDER BY rowid',
        (ROUTE_ID, VERSION))]


def historia_v1(alias):
    """Solo lectura: no invoca estado V1 ni regenera su Excel."""
    path = carpeta(alias) / 'events.sqlite'
    result = {'presente': path.is_file(), 'eventos': 0, 'perfil': {},
              'pasos_demostrados': [], 'equivalencias_automaticas': False}
    if not path.is_file():
        return result
    if path.resolve().parent != carpeta(alias).resolve():
        raise ValueError('El historial V1 queda fuera de la carpeta individual')
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as old:
        tablas = {r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'eventos' in tablas:
            result['eventos'] = old.execute('SELECT count(*) FROM eventos').fetchone()[0]
            result['pasos_demostrados'] = [r[0] for r in old.execute(
                "SELECT DISTINCT paso FROM eventos WHERE estado='DEMOSTRADO' ORDER BY paso")]
        if 'perfil' in tablas:
            result['perfil'] = dict(old.execute('SELECT clave,valor FROM perfil'))
    return result


def estado(conn, alias):
    eventos = filas(conn, 'eventos_v2')
    checks = filas(conn, 'checkpoints_v2')
    inicios = {r['etapa']: r for r in filas(conn, 'inicios_v2')}
    estados = {a['id']: 'NO_INICIADO' for a in ACTIVIDADES}
    for row in eventos:
        if row['actividad'] not in estados:
            raise ValueError('Evento de actividad ajena a esta versión de ruta')
        if estados[row['actividad']] != 'DEMOSTRADO':
            estados[row['actividad']] = row['estado']
    for row in checks:
        if row['actividad'] not in estados:
            raise ValueError('Checkpoint de actividad ajena a esta versión de ruta')
        if estados[row['actividad']] == 'NO_INICIADO':
            estados[row['actividad']] = 'EN_DESARROLLO'
    actual = next((a for a in ACTIVIDADES if estados[a['id']] != 'DEMOSTRADO'), None)
    etapas = {}
    for etapa in ETAPAS:
        ids = [a['id'] for a in ACTIVIDADES if a['etapa'] == etapa]
        completa = all(estados[k] == 'DEMOSTRADO' for k in ids)
        etapas[etapa] = (f'{etapa}_COMPRENSION_REGISTRADA' if completa else
                        f'{etapa}_EN_CURSO' if etapa in inicios else f'{etapa}_NO_INICIADA')
    puede_preguntar = actual is not None and (actual['etapa'] == 'E1' or actual['etapa'] in inicios)
    checkpoint = next((r for r in reversed(checks) if actual and r['actividad'] == actual['id']), None)
    objetivo = ('RECORRIDO_TEORICO_REGISTRADO' if actual is None else
                f'INICIAR_{actual["etapa"]}' if not puede_preguntar else 'CONTINUAR_CONCEPTO')
    historial = historia_v1(alias)
    perfil = {**historial['perfil'], **dict(conn.execute('SELECT clave,valor FROM perfil_v2'))}
    return {'alumno': alias, 'route_id': ROUTE_ID, 'route_version': VERSION,
            'alcance': 'TEORIA_CON_EJEMPLOS_ACADEMICOS', 'perfil': perfil,
            'etapas': etapas, 'estados': estados, 'eventos': len(eventos),
            'actividad_actual': actual['id'] if actual else None,
            'actividad': actual if puede_preguntar else None,
            'checkpoint': checkpoint, 'objetivo_siguiente': objetivo,
            'esperar_inicio_etapa': actual is not None and not puede_preguntar,
            'base_s12': inicios.get('S12', {}).get('base'),
            'historial_v1': historial,
            'comprension_registrada': actual is None,
            'aceptacion_conversacional_humana': 'NO_ACREDITADA_POR_EL_SCRIPT',
            'productos_grupales': {'S11': 'NO_VERIFICADO_EN_ESTA_RUTA_TEORICA',
                                  'S12': 'NO_VERIFICADO_EN_ESTA_RUTA_TEORICA'},
            'evaluacion_formal': False, 'recursos_reservas_profesionales': False}


def exportar(conn, alias, info):
    eventos = filas(conn, 'eventos_v2')
    checks = filas(conn, 'checkpoints_v2')
    resumen = [['Ruta', 'Versión', 'Etapa', 'Actividad', 'Concepto', 'Comprensión registrada']]
    resumen += [[ROUTE_ID, VERSION, a['etapa'], a['id'], a['titulo'], info['estados'][a['id']]]
                for a in ACTIVIDADES]
    evidencias = [['Fecha UTC', 'Ruta', 'Versión', 'Etapa', 'Actividad', 'Estado',
                   'Respuesta del estudiante', 'Criterio observado por tutor', 'Tipo', 'ID',
                   'Observación literal del visor']]
    evidencias += [[r[k] for k in ('fecha', 'route_id', 'route_version', 'etapa', 'actividad',
                                  'estado', 'respuesta', 'criterio_observado', 'tipo_evidencia',
                                  'id', 'observacion_visor')]
                   for r in eventos]
    checkpoints = [['Fecha UTC', 'Ruta', 'Versión', 'Etapa', 'Actividad', 'Comprensión parcial',
                    'Pregunta respondida', 'Pregunta pendiente', 'Dificultad', 'Próxima acción',
                    'Evidencia del estudiante']]
    checkpoints += [[r[k] for k in ('fecha', 'route_id', 'route_version', 'etapa', 'actividad',
                                    'comprension_parcial', 'pregunta_respondida', 'pregunta_pendiente',
                                    'dificultad_pendiente', 'proxima_accion', 'evidencia_estudiante')]
                   for r in checks]
    ultimos = {}
    observaciones = {}
    for row in eventos:
        ultimos[row['actividad']] = ('evento', row)
        if row['observacion_visor'].strip():
            observaciones[row['actividad']] = row['observacion_visor']
    for row in checks:
        actual = ultimos.get(row['actividad'])
        if actual is None or row['fecha'] > actual[1]['fecha']:
            ultimos[row['actividad']] = ('checkpoint', row)
    individual = [['Ruta', 'Versión', 'Alias', 'Etapa', 'Actividad', 'Tema',
                   'Pantalla o guía', 'Acción visual propuesta', 'Última observación literal del visor',
                   'Respuesta literal del alumno', 'Criterio o comprensión parcial',
                   'Estado de comprensión', 'Pregunta pendiente', 'Fecha UTC', 'ID evidencia']]
    for a in ACTIVIDADES:
        visita = a.get('visor', {})
        clase, ultima = ultimos.get(a['id'], (None, {}))
        demostrado = info['estados'][a['id']] == 'DEMOSTRADO'
        individual.append([ROUTE_ID, VERSION, alias, a['etapa'], a['id'], a['titulo'],
                           visita.get('url', a['recurso']), visita.get('accion', ''),
                           observaciones.get(a['id'], ''),
                           ultima.get('respuesta', '') if clase == 'evento' else
                           ultima.get('evidencia_estudiante', ''),
                           ultima.get('criterio_observado', '') if clase == 'evento' else
                           ultima.get('comprension_parcial', ''), info['estados'][a['id']],
                           ultima.get('pregunta_pendiente', '') if clase == 'checkpoint' and not demostrado else '',
                           ultima.get('fecha', ''), ultima.get('id', '')])
    contexto = [['Campo', 'Valor'], ['Alias individual', alias], ['Ruta', ROUTE_ID], ['Versión', VERSION],
                ['Alcance', info['alcance']], ['Objetivo siguiente', info['objetivo_siguiente']],
                ['S11 grupal', info['productos_grupales']['S11']],
                ['S12 grupal', info['productos_grupales']['S12']],
                ['Base de S12', info['base_s12'] or 'NO_INICIADA'],
                ['Historial V1', 'Separado; sin equivalencias automáticas'],
                ['Evaluación formal', 'No'], ['Aceptación humana', 'No acreditada por el script']]
    path = carpeta(alias) / 'Progreso_Kai_G01_Teoria_V2.xlsx'
    legado.escribir_xlsx(path, [('Resumen', resumen, [28, 10, 12, 23, 44, 30]),
                               ('Evidencias', evidencias, [25, 28, 10, 12, 23, 24, 65, 65, 28, 40, 65]),
                               ('Checkpoints', checkpoints, [25, 28, 10, 12, 23, 60, 60, 60, 45, 30, 65]),
                               ('Contexto', contexto, [33, 70]),
                               ('Bitacora individual', individual,
                                [28, 10, 19, 12, 23, 36, 46, 65, 65, 75, 65, 27, 65, 27, 40])])
    return str(path)


def validar_solicitud(s):
    if not isinstance(s, dict) or not isinstance(s.get('operacion'), str) or s['operacion'] not in CAMPOS:
        raise ValueError('Operación V2 no permitida')
    if set(s) - COMUNES - CAMPOS[s['operacion']]:
        raise ValueError('Campo no permitido para esta operación V2')
    if s.get('route_id') != ROUTE_ID or type(s.get('route_version')) is not int or s['route_version'] != VERSION:
        raise ValueError('La identidad de ruta y versión debe coincidir con V2')
    carpeta(s.get('alumno'))


def procesar(s):
    validar_solicitud(s)
    alias, op = s['alumno'], s['operacion']
    fecha = dt.datetime.now(dt.timezone.utc).isoformat(timespec='microseconds')
    huella = hashlib.sha256(json.dumps(s, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':')).encode('utf-8')).hexdigest()
    duplicado = False
    with closing(abrir(alias)) as conn:
        conn.execute('BEGIN IMMEDIATE')
        info = estado(conn, alias)
        if op == 'perfil':
            if s.get('consentimiento') is not True:
                raise ValueError('Guardar memoria social requiere consentimiento explícito')
            for field, key in [('nombre', 'nombre_elegido'), ('kai', 'nombre_kai')]:
                if field in s:
                    value = texto(s[field], field, 80)
                    conn.execute('INSERT INTO perfil_v2 VALUES (?,?) ON CONFLICT(clave) '
                                 'DO UPDATE SET valor=excluded.valor', (key, value))
        elif op == 'iniciar_etapa':
            etapa = s.get('etapa')
            if etapa not in ETAPAS:
                raise ValueError('Etapa inexistente')
            previas = ETAPAS[:ETAPAS.index(etapa)]
            if any(info['estados'][a['id']] != 'DEMOSTRADO' for a in ACTIVIDADES if a['etapa'] in previas):
                raise ValueError('Primero debe completar la comprensión de la etapa anterior')
            base = s.get('base', 'TEORIA_G01')
            if etapa == 'S12' and base != 'EJEMPLO_CONCEPTUAL_SIN_PRODUCTO':
                raise ValueError('S12 teórica usa solo un ejemplo conceptual; no acredita un producto grupal')
            if etapa != 'S12' and base != 'TEORIA_G01':
                raise ValueError('Base conceptual no permitida para esta etapa')
            previo = conn.execute('SELECT base FROM inicios_v2 WHERE route_id=? AND '
                                  'route_version=? AND etapa=?', (ROUTE_ID, VERSION, etapa)).fetchone()
            if previo and previo['base'] != base:
                raise ValueError('La base de una etapa iniciada no se cambia retrospectivamente')
            duplicado = previo is not None
            conn.execute('INSERT OR IGNORE INTO inicios_v2 VALUES (?,?,?,?,?)',
                         (fecha, ROUTE_ID, VERSION, etapa, base))
        elif op in {'registrar', 'checkpoint'}:
            tabla = 'eventos_v2' if op == 'registrar' else 'checkpoints_v2'
            duplicado = conn.execute(f'SELECT 1 FROM {tabla} WHERE huella=?', (huella,)).fetchone() is not None
            actividad = s.get('actividad')
            if not isinstance(actividad, str) or actividad not in POR_ID:
                raise ValueError('Actividad inexistente en esta versión')
            a = POR_ID[actividad]
            if not duplicado:
                if actividad != info['actividad_actual']:
                    raise ValueError('La evidencia debe corresponder a la actividad pendiente; no se saltan conceptos')
                if info['esperar_inicio_etapa']:
                    raise ValueError('Debe iniciar la nueva etapa antes de registrar su contenido')
                if a['etapa'] == 'E1':
                    conn.execute('INSERT OR IGNORE INTO inicios_v2 VALUES (?,?,?,?,?)',
                                 (fecha, ROUTE_ID, VERSION, 'E1', 'TEORIA_G01'))
                if op == 'registrar':
                    estado_nuevo = s.get('estado')
                    if not isinstance(estado_nuevo, str) or estado_nuevo not in ESTADOS:
                        raise ValueError('Estado de comprensión no permitido')
                    respuesta = texto(s.get('respuesta'), 'respuesta')
                    criterio = texto(s.get('criterio_observado'), 'criterio_observado')
                    tipo = s.get('tipo_evidencia')
                    if not isinstance(tipo, str) or tipo not in {'RAZONAMIENTO_PROPIO', 'RECONOCIMIENTO', 'ERROR_O_DUDA'}:
                        raise ValueError('Tipo de evidencia no permitido')
                    if estado_nuevo == 'DEMOSTRADO' and (tipo != 'RAZONAMIENTO_PROPIO' or normalizar(respuesta) in GENERICAS):
                        raise ValueError('Una aceptación o reconocimiento no acredita razonamiento propio')
                    observacion = texto(s['observacion_visor'], 'observacion_visor', vacio=True) if 'observacion_visor' in s else ''
                    if observacion.strip() and 'visor' not in a:
                        raise ValueError('Esta actividad no tiene una visita al visor definida')
                    conn.execute('''INSERT INTO eventos_v2
                        (id,fecha,route_id,route_version,etapa,actividad,estado,respuesta,
                         criterio_observado,tipo_evidencia,huella,observacion_visor)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                                 (str(uuid.uuid4()), fecha, ROUTE_ID, VERSION, a['etapa'], actividad,
                                  estado_nuevo, respuesta, criterio, tipo, huella, observacion))
                else:
                    keys = ['comprension_parcial', 'pregunta_respondida', 'pregunta_pendiente',
                            'dificultad_pendiente', 'proxima_accion', 'evidencia_estudiante']
                    values = [texto(s.get(k), k, vacio=k in {'comprension_parcial', 'dificultad_pendiente'})
                              for k in keys]
                    if s['proxima_accion'] not in ACCIONES:
                        raise ValueError('Próxima acción no permitida')
                    if normalizar(s['pregunta_pendiente']) == normalizar(s['pregunta_respondida']):
                        raise ValueError('No repetir la pregunta ya respondida como pregunta pendiente')
                    conn.execute('INSERT INTO checkpoints_v2 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                 (str(uuid.uuid4()), fecha, ROUTE_ID, VERSION, a['etapa'], actividad,
                                  *values, huella))
        integridad = conn.execute('PRAGMA integrity_check').fetchone()[0] if op == 'verificar' else None
        if integridad is not None and integridad != 'ok':
            raise ValueError('Falló la integridad del registro V2')
        conn.commit()
        info = estado(conn, alias)
        xlsx = exportar(conn, alias, info)
        return {'ok': True, **info, 'duplicado': duplicado, 'xlsx': xlsx,
                **({'integridad_sqlite': integridad} if integridad is not None else {})}


def objeto_sin_duplicados(pares):
    result = {}
    for key, value in pares:
        if key in result:
            raise ValueError(f'Campo JSON duplicado: {key}')
        result[key] = value
    return result


def main():
    if sys.argv[1:] != ['procesar-pendiente']:
        raise ValueError('Use el comando constante: python kai/registro_teoria_v2.py procesar-pendiente')
    raw = SOLICITUD.read_bytes()
    if len(raw) > 65536:
        raise ValueError('La solicitud V2 supera el tamaño permitido')
    solicitud = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=objeto_sin_duplicados)
    result = procesar(solicitud)
    # Un fallo de Excel deja la solicitud para reintentar sin duplicar eventos.
    SOLICITUD.unlink()
    # ASCII de transporte: JSON recupera Unicode sin depender de la consola Windows.
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc),
                          'solicitud_conservada': SOLICITUD.exists()}, ensure_ascii=True), file=sys.stderr)
        sys.exit(2)
