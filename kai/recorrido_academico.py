"""Entrada local del recorrido conceptual E1/S11/S12 sin productos mineros."""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import sys
import registro_teoria_v2 as theory

ROOT = Path(__file__).resolve().parent.parent
REQUEST = ROOT / '.kai_solicitud_recorrido_academico.json'
ALLOWED = {'estado','verificar','perfil','registrar','checkpoint','iniciar_etapa'}

def process(request):
    if not isinstance(request, dict) or request.get('operacion') not in ALLOWED:
        raise ValueError('Operación conceptual no permitida; no hay entrega individual completa')
    payload = dict(request, route_id=theory.ROUTE_ID, route_version=theory.VERSION)
    if payload['operacion'] == 'iniciar_etapa' and payload.get('etapa') == 'S12':
        payload['base'] = 'EJEMPLO_CONCEPTUAL_SIN_PRODUCTO'
    result = theory.procesar(payload)
    result['controller_scope'] = 'SOLO_TEORIA_CONCEPTUAL'
    result['entrega_final_lista'] = False
    result['ficha_e1_21'] = 'NO_ADAPTADA'
    result['aplicacion_s11_s12_26'] = 'NO_ADAPTADA'
    result['productos_grupales'] = {'S11':'NO_VERIFICADO','S12':'NO_VERIFICADO'}
    return result

def main():
    if sys.argv[1:] != ['procesar-pendiente']:
        print('Uso: python kai/recorrido_academico.py procesar-pendiente',file=sys.stderr)
        return 2
    try:
        if REQUEST.stat().st_size > 65536:
            raise ValueError('Solicitud demasiado larga')
        request = json.loads(REQUEST.read_text(encoding='utf-8-sig'),
                             object_pairs_hook=theory.objeto_sin_duplicados)
        result = process(request)
        REQUEST.unlink()
        print(json.dumps(result,ensure_ascii=True))
        return 0
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error) as exc:
        print(json.dumps({'ok':False,'error':str(exc),'solicitud_conservada':REQUEST.exists()},ensure_ascii=True),file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
