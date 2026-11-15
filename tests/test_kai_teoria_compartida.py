"""Comprueba persistencia conceptual sin generar resultados mineros."""
from __future__ import annotations
import importlib
import json
from pathlib import Path
import sys
import zipfile
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'kai'))
controller = importlib.import_module('recorrido_academico')
theory = importlib.import_module('registro_teoria_v2')

def test_identidad_y_contrato(tmp_path,monkeypatch):
    monkeypatch.setattr(theory,'DATA',tmp_path/'private')
    state=controller.process({'operacion':'estado','alumno':'AlumnoDemo'})
    assert state['actividad_actual']=='E1.01'
    assert state['eventos']==0
    assert state['controller_scope']=='SOLO_TEORIA_CONCEPTUAL'
    assert state['productos_grupales']=={'S11':'NO_VERIFICADO','S12':'NO_VERIFICADO'}
    assert state['entrega_final_lista'] is False
    assert len(theory.ACTIVIDADES)==30
    assert [sum(a['etapa']==k for a in theory.ACTIVIDADES) for k in ('E1','S11','S12')]==[8,16,6]
    assert not any('G05' in json.dumps(a,ensure_ascii=False) or 'Santa Elena' in json.dumps(a,ensure_ascii=False) for a in theory.ACTIVIDADES)

def test_rechazo_recuperacion_y_excel(tmp_path,monkeypatch):
    monkeypatch.setattr(theory,'DATA',tmp_path/'private')
    alias='AlumnoDemo'
    base={'alumno':alias,'operacion':'registrar','actividad':'E1.01','estado':'DEMOSTRADO',
          'tipo_evidencia':'RAZONAMIENTO_PROPIO','criterio_observado':'Razón espacial propia'}
    with pytest.raises(ValueError):
        controller.process(dict(base,respuesta='Sí'))
    with pytest.raises(ValueError):
        controller.process({'operacion':'iniciar_etapa','alumno':alias,'etapa':'S11'})
    state=controller.process(dict(base,respuesta='No extendería una muestra a todo el depósito porque solo representa su ubicación.'))
    assert state['actividad_actual']=='E1.02' and state['eventos']==1
    reload=controller.process({'operacion':'estado','alumno':alias})
    assert reload['actividad_actual']=='E1.02' and reload['eventos']==1
    assert controller.process(dict(base,respuesta='No extendería una muestra a todo el depósito porque solo representa su ubicación.'))['duplicado'] is True
    other=controller.process({'operacion':'estado','alumno':'OtraPersona'})
    assert other['eventos']==0 and other['actividad_actual']=='E1.01'
    with zipfile.ZipFile(state['xlsx']) as z:
        assert z.testzip() is None and 'xl/workbook.xml' in z.namelist()
    assert controller.process({'operacion':'verificar','alumno':alias})['integridad_sqlite']=='ok'
    with pytest.raises(ValueError):
        controller.process({'operacion':'entregar_individual','alumno':alias})
