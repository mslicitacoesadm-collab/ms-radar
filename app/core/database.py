from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from app.core.config import DB_PATH


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS opportunities (
                    numero_controle_pncp TEXT PRIMARY KEY,
                    numero_compra TEXT,
                    ano_compra INTEGER,
                    sequencial_compra INTEGER,
                    processo TEXT,
                    objeto_compra TEXT,
                    resumo_objeto TEXT,
                    orgao_cnpj TEXT,
                    orgao_razao_social TEXT,
                    poder_id TEXT,
                    esfera_id TEXT,
                    unidade_codigo TEXT,
                    unidade_nome TEXT,
                    municipio_nome TEXT,
                    uf_sigla TEXT,
                    codigo_ibge TEXT,
                    modalidade_codigo INTEGER,
                    modalidade_nome TEXT,
                    modo_disputa_codigo INTEGER,
                    modo_disputa_nome TEXT,
                    tipo_instrumento_codigo INTEGER,
                    data_publicacao_pncp TEXT,
                    data_abertura_proposta TEXT,
                    data_encerramento_proposta TEXT,
                    valor_total_estimado REAL,
                    valor_total_homologado REAL,
                    link_sistema_origem TEXT,
                    link_processo_eletronico TEXT,
                    fonte_tipo TEXT,
                    fonte_data_referencia TEXT,
                    oportunidade_score REAL,
                    urgencia_score REAL,
                    aderencia_score REAL,
                    valor_score REAL,
                    risco_score REAL,
                    search_blob TEXT,
                    detail_status TEXT DEFAULT 'summary',
                    last_detail_attempt TEXT,
                    last_detail_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS opportunities_fts USING fts5(
                    numero_controle_pncp,
                    resumo_objeto,
                    objeto_compra,
                    orgao_razao_social,
                    municipio_nome,
                    uf_sigla,
                    modalidade_nome,
                    content='opportunities',
                    content_rowid='rowid'
                );

                CREATE TRIGGER IF NOT EXISTS opportunities_ai AFTER INSERT ON opportunities BEGIN
                    INSERT INTO opportunities_fts(rowid, numero_controle_pncp, resumo_objeto, objeto_compra, orgao_razao_social, municipio_nome, uf_sigla, modalidade_nome)
                    VALUES (new.rowid, new.numero_controle_pncp, new.resumo_objeto, new.objeto_compra, new.orgao_razao_social, new.municipio_nome, new.uf_sigla, new.modalidade_nome);
                END;

                CREATE TRIGGER IF NOT EXISTS opportunities_ad AFTER DELETE ON opportunities BEGIN
                    INSERT INTO opportunities_fts(opportunities_fts, rowid, numero_controle_pncp, resumo_objeto, objeto_compra, orgao_razao_social, municipio_nome, uf_sigla, modalidade_nome)
                    VALUES('delete', old.rowid, old.numero_controle_pncp, old.resumo_objeto, old.objeto_compra, old.orgao_razao_social, old.municipio_nome, old.uf_sigla, old.modalidade_nome);
                END;

                CREATE TRIGGER IF NOT EXISTS opportunities_au AFTER UPDATE ON opportunities BEGIN
                    INSERT INTO opportunities_fts(opportunities_fts, rowid, numero_controle_pncp, resumo_objeto, objeto_compra, orgao_razao_social, municipio_nome, uf_sigla, modalidade_nome)
                    VALUES('delete', old.rowid, old.numero_controle_pncp, old.resumo_objeto, old.objeto_compra, old.orgao_razao_social, old.municipio_nome, old.uf_sigla, old.modalidade_nome);
                    INSERT INTO opportunities_fts(rowid, numero_controle_pncp, resumo_objeto, objeto_compra, orgao_razao_social, municipio_nome, uf_sigla, modalidade_nome)
                    VALUES (new.rowid, new.numero_controle_pncp, new.resumo_objeto, new.objeto_compra, new.orgao_razao_social, new.municipio_nome, new.uf_sigla, new.modalidade_nome);
                END;

                CREATE TABLE IF NOT EXISTS alert_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    termos TEXT NOT NULL,
                    uf_sigla TEXT,
                    municipio_nome TEXT,
                    modalidade_codigo INTEGER,
                    valor_min REAL,
                    valor_max REAL,
                    somente_abertas INTEGER DEFAULT 1,
                    canal_email TEXT,
                    canal_telegram_chat_id TEXT,
                    ativo INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sync_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    details TEXT,
                    total_imported INTEGER DEFAULT 0,
                    total_updated INTEGER DEFAULT 0,
                    total_seen INTEGER DEFAULT 0
                );
                """
            )
            existing_cols = {row['name'] for row in conn.execute("PRAGMA table_info(opportunities)").fetchall()}
            for col, ddl in {
                'detail_status': "ALTER TABLE opportunities ADD COLUMN detail_status TEXT DEFAULT 'summary'",
                'last_detail_attempt': "ALTER TABLE opportunities ADD COLUMN last_detail_attempt TEXT",
                'last_detail_error': "ALTER TABLE opportunities ADD COLUMN last_detail_error TEXT",
            }.items():
                if col not in existing_cols:
                    conn.execute(ddl)

    def rebuild_fts(self) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO opportunities_fts(opportunities_fts) VALUES ('rebuild')")

    def upsert_opportunities(self, rows: Iterable[dict[str, Any]], detail_status: str = 'summary') -> tuple[int, int]:
        now = datetime.utcnow().isoformat()
        inserted = 0
        updated = 0
        with self.connect() as conn:
            for row in rows:
                current = conn.execute(
                    'SELECT numero_controle_pncp, created_at, detail_status FROM opportunities WHERE numero_controle_pncp = ?',
                    (row['numero_controle_pncp'],),
                ).fetchone()
                payload = {
                    **row,
                    'created_at': current['created_at'] if current else now,
                    'updated_at': now,
                    'detail_status': current['detail_status'] if current and current['detail_status'] == 'done' else detail_status,
                    'last_detail_attempt': None,
                    'last_detail_error': None,
                }
                if current:
                    updated += 1
                    conn.execute(
                        """
                        UPDATE opportunities SET
                            numero_compra=:numero_compra,
                            ano_compra=:ano_compra,
                            sequencial_compra=:sequencial_compra,
                            processo=:processo,
                            objeto_compra=:objeto_compra,
                            resumo_objeto=:resumo_objeto,
                            orgao_cnpj=:orgao_cnpj,
                            orgao_razao_social=:orgao_razao_social,
                            poder_id=:poder_id,
                            esfera_id=:esfera_id,
                            unidade_codigo=:unidade_codigo,
                            unidade_nome=:unidade_nome,
                            municipio_nome=:municipio_nome,
                            uf_sigla=:uf_sigla,
                            codigo_ibge=:codigo_ibge,
                            modalidade_codigo=:modalidade_codigo,
                            modalidade_nome=:modalidade_nome,
                            modo_disputa_codigo=:modo_disputa_codigo,
                            modo_disputa_nome=:modo_disputa_nome,
                            tipo_instrumento_codigo=:tipo_instrumento_codigo,
                            data_publicacao_pncp=:data_publicacao_pncp,
                            data_abertura_proposta=:data_abertura_proposta,
                            data_encerramento_proposta=:data_encerramento_proposta,
                            valor_total_estimado=:valor_total_estimado,
                            valor_total_homologado=:valor_total_homologado,
                            link_sistema_origem=:link_sistema_origem,
                            link_processo_eletronico=:link_processo_eletronico,
                            fonte_tipo=:fonte_tipo,
                            fonte_data_referencia=:fonte_data_referencia,
                            oportunidade_score=:oportunidade_score,
                            urgencia_score=:urgencia_score,
                            aderencia_score=:aderencia_score,
                            valor_score=:valor_score,
                            risco_score=:risco_score,
                            search_blob=:search_blob,
                            detail_status=:detail_status,
                            updated_at=:updated_at
                        WHERE numero_controle_pncp=:numero_controle_pncp
                        """,
                        payload,
                    )
                else:
                    inserted += 1
                    conn.execute(
                        """
                        INSERT INTO opportunities (
                            numero_controle_pncp, numero_compra, ano_compra, sequencial_compra, processo,
                            objeto_compra, resumo_objeto, orgao_cnpj, orgao_razao_social, poder_id, esfera_id,
                            unidade_codigo, unidade_nome, municipio_nome, uf_sigla, codigo_ibge,
                            modalidade_codigo, modalidade_nome, modo_disputa_codigo, modo_disputa_nome,
                            tipo_instrumento_codigo, data_publicacao_pncp, data_abertura_proposta,
                            data_encerramento_proposta, valor_total_estimado, valor_total_homologado,
                            link_sistema_origem, link_processo_eletronico, fonte_tipo, fonte_data_referencia,
                            oportunidade_score, urgencia_score, aderencia_score, valor_score, risco_score,
                            search_blob, detail_status, last_detail_attempt, last_detail_error, created_at, updated_at
                        ) VALUES (
                            :numero_controle_pncp, :numero_compra, :ano_compra, :sequencial_compra, :processo,
                            :objeto_compra, :resumo_objeto, :orgao_cnpj, :orgao_razao_social, :poder_id, :esfera_id,
                            :unidade_codigo, :unidade_nome, :municipio_nome, :uf_sigla, :codigo_ibge,
                            :modalidade_codigo, :modalidade_nome, :modo_disputa_codigo, :modo_disputa_nome,
                            :tipo_instrumento_codigo, :data_publicacao_pncp, :data_abertura_proposta,
                            :data_encerramento_proposta, :valor_total_estimado, :valor_total_homologado,
                            :link_sistema_origem, :link_processo_eletronico, :fonte_tipo, :fonte_data_referencia,
                            :oportunidade_score, :urgencia_score, :aderencia_score, :valor_score, :risco_score,
                            :search_blob, :detail_status, :last_detail_attempt, :last_detail_error, :created_at, :updated_at
                        )
                        """,
                        payload,
                    )
            conn.execute("INSERT INTO opportunities_fts(opportunities_fts) VALUES ('rebuild')")
        return inserted, updated

    def update_detail_payload(self, numero_controle_pncp: str, payload: dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        data = {
            'numero_controle_pncp': numero_controle_pncp,
            'valor_total_estimado': payload['valor_total_estimado'],
            'valor_total_homologado': payload['valor_total_homologado'],
            'link_sistema_origem': payload['link_sistema_origem'],
            'link_processo_eletronico': payload['link_processo_eletronico'],
            'oportunidade_score': payload['oportunidade_score'],
            'urgencia_score': payload['urgencia_score'],
            'aderencia_score': payload['aderencia_score'],
            'valor_score': payload['valor_score'],
            'risco_score': payload['risco_score'],
            'last_detail_attempt': now,
            'updated_at': now,
        }
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE opportunities SET
                    valor_total_estimado=:valor_total_estimado,
                    valor_total_homologado=:valor_total_homologado,
                    link_sistema_origem=:link_sistema_origem,
                    link_processo_eletronico=:link_processo_eletronico,
                    oportunidade_score=:oportunidade_score,
                    urgencia_score=:urgencia_score,
                    aderencia_score=:aderencia_score,
                    valor_score=:valor_score,
                    risco_score=:risco_score,
                    detail_status='done',
                    last_detail_attempt=:last_detail_attempt,
                    last_detail_error=NULL,
                    updated_at=:updated_at
                WHERE numero_controle_pncp=:numero_controle_pncp
                """,
                data,
            )

    def mark_detail_status(self, numero_controle_pncp: str, status: str, error: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE opportunities SET detail_status=?, last_detail_attempt=?, last_detail_error=?, updated_at=? WHERE numero_controle_pncp=?",
                (status, datetime.utcnow().isoformat(), error, datetime.utcnow().isoformat(), numero_controle_pncp),
            )

    def pending_detail_candidates(self, limit: int = 50):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM opportunities
                WHERE detail_status IN ('summary', 'retry')
                  AND orgao_cnpj IS NOT NULL AND TRIM(orgao_cnpj) <> ''
                  AND ano_compra IS NOT NULL
                  AND sequencial_compra IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def create_sync_run(self, source: str, status: str = 'running', details: str = '') -> int:
        with self.connect() as conn:
            cur = conn.execute(
                'INSERT INTO sync_runs(started_at, status, source, details) VALUES (?, ?, ?, ?)',
                (datetime.utcnow().isoformat(), status, source, details),
            )
            return int(cur.lastrowid)

    def finish_sync_run(self, run_id: int, status: str, total_imported: int, total_updated: int, total_seen: int, details: str = '') -> None:
        with self.connect() as conn:
            conn.execute(
                '''
                UPDATE sync_runs
                SET finished_at=?, status=?, total_imported=?, total_updated=?, total_seen=?, details=?
                WHERE id=?
                ''',
                (datetime.utcnow().isoformat(), status, total_imported, total_updated, total_seen, details, run_id),
            )

    def recent_sync_runs(self, limit: int = 20):
        with self.connect() as conn:
            return conn.execute('SELECT * FROM sync_runs ORDER BY id DESC LIMIT ?', (limit,)).fetchall()

    def stats(self) -> dict[str, Any]:
        with self.connect() as conn:
            total = conn.execute('SELECT COUNT(*) AS n FROM opportunities').fetchone()['n']
            latest = conn.execute('SELECT MAX(updated_at) AS updated FROM opportunities').fetchone()['updated']
            open_now = conn.execute(
                """
                SELECT COUNT(*) AS n FROM opportunities
                WHERE data_encerramento_proposta IS NOT NULL
                  AND date(data_encerramento_proposta) >= date('now')
                """
            ).fetchone()['n']
            urgent = conn.execute(
                """
                SELECT COUNT(*) AS n FROM opportunities
                WHERE data_encerramento_proposta IS NOT NULL
                  AND date(data_encerramento_proposta) BETWEEN date('now') AND date('now', '+2 day')
                """
            ).fetchone()['n']
            pending_details = conn.execute(
                "SELECT COUNT(*) AS n FROM opportunities WHERE detail_status IN ('summary','retry')"
            ).fetchone()['n']
            detailed = conn.execute(
                "SELECT COUNT(*) AS n FROM opportunities WHERE detail_status='done'"
            ).fetchone()['n']
            return {
                'total': total,
                'latest': latest,
                'open_now': open_now,
                'urgent': urgent,
                'pending_details': pending_details,
                'detailed': detailed,
            }

    def distinct_values(self, column: str, table: str = 'opportunities'):
        allowed = {'uf_sigla', 'municipio_nome', 'modalidade_nome', 'orgao_razao_social'}
        if column not in allowed:
            raise ValueError('Coluna não permitida.')
        with self.connect() as conn:
            rows = conn.execute(
                f'SELECT DISTINCT {column} AS value FROM {table} WHERE {column} IS NOT NULL AND TRIM({column}) <> "" ORDER BY {column}'
            ).fetchall()
            return [r['value'] for r in rows]

    def save_alert_profile(self, payload: dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        with self.connect() as conn:
            conn.execute(
                '''
                INSERT INTO alert_profiles(
                    nome, termos, uf_sigla, municipio_nome, modalidade_codigo,
                    valor_min, valor_max, somente_abertas, canal_email,
                    canal_telegram_chat_id, ativo, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    payload['nome'], payload['termos'], payload.get('uf_sigla'), payload.get('municipio_nome'),
                    payload.get('modalidade_codigo'), payload.get('valor_min'), payload.get('valor_max'),
                    1 if payload.get('somente_abertas', True) else 0, payload.get('canal_email'),
                    payload.get('canal_telegram_chat_id'), 1, now, now,
                ),
            )

    def list_alert_profiles(self):
        with self.connect() as conn:
            return conn.execute('SELECT * FROM alert_profiles WHERE ativo = 1 ORDER BY id DESC').fetchall()

    def export_rows(self, query: str, params: tuple = ()): 
        with self.connect() as conn:
            return conn.execute(query, params).fetchall()
