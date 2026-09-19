from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from config import DB_PATH

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS assessments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 project_name TEXT NOT NULL,
 acronym TEXT,
 programme TEXT NOT NULL,
 call_id TEXT,
 topic TEXT,
 action_type TEXT,
 organisation TEXT,
 evaluator TEXT,
 status TEXT NOT NULL DEFAULT 'ROBOCZA',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assessment_versions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 assessment_id INTEGER NOT NULL,
 version_no INTEGER NOT NULL,
 label TEXT,
 created_at TEXT NOT NULL,
 overall_score REAL,
 UNIQUE(assessment_id, version_no),
 FOREIGN KEY(assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS indicator_scores(
 version_id INTEGER NOT NULL,
 indicator_id TEXT NOT NULL,
 score REAL NOT NULL DEFAULT 0,
 evidence TEXT,
 notes TEXT,
 PRIMARY KEY(version_id, indicator_id),
 FOREIGN KEY(version_id) REFERENCES assessment_versions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS version_analysis(
 version_id INTEGER PRIMARY KEY,
 call_text TEXT,
 objective_text TEXT,
 alignment_json TEXT,
 executive_summary TEXT,
 updated_at TEXT NOT NULL,
 FOREIGN KEY(version_id) REFERENCES assessment_versions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS documents(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 assessment_id INTEGER NOT NULL,
 kind TEXT NOT NULL,
 filename TEXT NOT NULL,
 stored_path TEXT NOT NULL,
 created_at TEXT NOT NULL,
 FOREIGN KEY(assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
);
'''

class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.initialize()
    @contextmanager
    def connect(self):
        con=sqlite3.connect(self.path); con.row_factory=sqlite3.Row; con.execute('PRAGMA foreign_keys=ON')
        try: yield con; con.commit()
        finally: con.close()
    def initialize(self):
        with self.connect() as con: con.executescript(SCHEMA)
    def create_assessment(self,data:dict[str,Any])->int:
        now=datetime.now().isoformat(timespec='seconds')
        vals=(data['project_name'].strip(),data.get('acronym','').strip(),data.get('programme','Horyzont Europa'),data.get('call_id','').strip(),data.get('topic','').strip(),data.get('action_type','RIA'),data.get('organisation','').strip(),data.get('evaluator','').strip(),'ROBOCZA',now,now)
        with self.connect() as con:
            cur=con.execute('INSERT INTO assessments(project_name,acronym,programme,call_id,topic,action_type,organisation,evaluator,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',vals)
            aid=int(cur.lastrowid)
            con.execute('INSERT INTO assessment_versions(assessment_id,version_no,label,created_at) VALUES(?,?,?,?)',(aid,1,'Wersja 1',now))
            return aid
    def list_assessments(self):
        with self.connect() as con: rows=con.execute('SELECT * FROM assessments ORDER BY updated_at DESC,id DESC').fetchall()
        return [dict(r) for r in rows]
    def get_assessment(self,aid:int):
        with self.connect() as con: r=con.execute('SELECT * FROM assessments WHERE id=?',(aid,)).fetchone()
        return dict(r) if r else None
    def delete_assessment(self,aid:int):
        with self.connect() as con: con.execute('DELETE FROM assessments WHERE id=?',(aid,))
    def list_versions(self,aid:int):
        with self.connect() as con: rows=con.execute('SELECT * FROM assessment_versions WHERE assessment_id=? ORDER BY version_no DESC',(aid,)).fetchall()
        return [dict(r) for r in rows]
    def create_version(self,aid:int,label:str=''):
        now=datetime.now().isoformat(timespec='seconds')
        with self.connect() as con:
            n=con.execute('SELECT COALESCE(MAX(version_no),0)+1 n FROM assessment_versions WHERE assessment_id=?',(aid,)).fetchone()['n']
            cur=con.execute('INSERT INTO assessment_versions(assessment_id,version_no,label,created_at) VALUES(?,?,?,?)',(aid,n,label or f'Wersja {n}',now))
            con.execute('UPDATE assessments SET updated_at=? WHERE id=?',(now,aid))
            return int(cur.lastrowid)
    def get_scores(self,vid:int):
        with self.connect() as con: rows=con.execute('SELECT * FROM indicator_scores WHERE version_id=?',(vid,)).fetchall()
        return {r['indicator_id']:dict(r) for r in rows}
    def save_score(self,vid:int,iid:str,score:float,evidence:str,notes:str):
        with self.connect() as con:
            con.execute('INSERT INTO indicator_scores(version_id,indicator_id,score,evidence,notes) VALUES(?,?,?,?,?) ON CONFLICT(version_id,indicator_id) DO UPDATE SET score=excluded.score,evidence=excluded.evidence,notes=excluded.notes',(vid,iid,score,evidence,notes))
    def save_scores_bulk(self,vid:int,scores:dict[str,float],evidence:dict[str,str],notes:dict[str,str]):
        with self.connect() as con:
            for iid, score in scores.items():
                con.execute('INSERT INTO indicator_scores(version_id,indicator_id,score,evidence,notes) VALUES(?,?,?,?,?) ON CONFLICT(version_id,indicator_id) DO UPDATE SET score=excluded.score,evidence=excluded.evidence,notes=excluded.notes',(vid,iid,float(score),evidence.get(iid,''),notes.get(iid,'')))
    def save_overall(self,vid:int,score:float):
        with self.connect() as con: con.execute('UPDATE assessment_versions SET overall_score=? WHERE id=?',(score,vid))
    def save_analysis(self,vid:int,call_text:str,objective_text:str,alignment:dict[str,Any],summary:str=''):
        now=datetime.now().isoformat(timespec='seconds')
        with self.connect() as con:
            con.execute('INSERT INTO version_analysis(version_id,call_text,objective_text,alignment_json,executive_summary,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(version_id) DO UPDATE SET call_text=excluded.call_text,objective_text=excluded.objective_text,alignment_json=excluded.alignment_json,executive_summary=excluded.executive_summary,updated_at=excluded.updated_at',(vid,call_text,objective_text,json.dumps(alignment,ensure_ascii=False),summary,now))
    def get_analysis(self,vid:int):
        with self.connect() as con: r=con.execute('SELECT * FROM version_analysis WHERE version_id=?',(vid,)).fetchone()
        if not r: return {'call_text':'','objective_text':'','alignment':{},'executive_summary':''}
        d=dict(r)
        try: d['alignment']=json.loads(d.pop('alignment_json') or '{}')
        except Exception: d['alignment']={}
        return d
    def add_document(self,aid:int,kind:str,filename:str,path:str):
        now=datetime.now().isoformat(timespec='seconds')
        with self.connect() as con: con.execute('INSERT INTO documents(assessment_id,kind,filename,stored_path,created_at) VALUES(?,?,?,?,?)',(aid,kind,filename,path,now))
    def list_documents(self,aid:int):
        with self.connect() as con: rows=con.execute('SELECT * FROM documents WHERE assessment_id=? ORDER BY created_at DESC',(aid,)).fetchall()
        return [dict(r) for r in rows]
