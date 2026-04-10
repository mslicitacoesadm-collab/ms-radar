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
                    oportunidade_score REAL DEFAULT 0,
                    urgencia_score REAL DEFAULT 0,
                    aderencia_score REAL DEFAULT 0,
                    valor_score REAL DEFAULT 0,
                    risco_score REAL DEFAULT 0,
                    search_blob TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_opportunities_pub ON opportunities(data_publicacao_pncp);
                CREATE INDEX IF NOT EXISTS idx_opportunities_end ON opportunities(data_encerramento_proposta);
                CREATE INDEX IF NOT EXISTS idx_opportunities_city ON opportunities(uf_sigla, municipio_nome);
                CREATE INDEX IF NOT EXISTS idx_opportunities_modalidade ON opportunities(modalidade_codigo);
                CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(oportunidade_score DESC);

                CREATE VIRTUAL TABLE IF NOT EXISTS opportunities_fts USING fts5(
                    numero_controle_pncp UNINDEXED,
                    objeto_compra,
                    resumo_objeto,
                    orgao_razao_social,
                    municipio_nome,
                    modalidade_nome,
                    search_blob,
                    content='opportunities',
                    content_rowid='rowid'
                );

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

                CREATE TABLE IF NOT EXISTS alert_hits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_profile_id INTEGER NOT NULL,
                    numero_controle_pncp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(alert_profile_id, numero_controle_pncp)
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

    def rebuild_fts(self) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO opportunities_fts(opportunities_fts) VALUES ('rebuild')")

    def upsert_opportunities(self, rows: Iterable[dict[str, Any]]) -> tuple[int, int]:
        now = datetime.utcnow().isoformat()
        inserted = 0
        updated = 0
        with self.connect() as conn:
            for row in rows:
                current = conn.execute(
                    'SELECT numero_controle_pncp FROM opportunities WHERE numero_controle_pncp = ?',
                    (row['numero_controle_pncp'],),
                ).fetchone()
                payload = {
                    **row,
                    'created_at': current['numero_controle_pncp'] if False else now,
                    'updated_at': now,
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
                            search_blob, created_at, updated_at
                        ) VALUES (
                            :numero_controle_pncp, :numero_compra, :ano_compra, :sequencial_compra, :processo,
                            :objeto_compra, :resumo_objeto, :orgao_cnpj, :orgao_razao_social, :poder_id, :esfera_id,
                            :unidade_codigo, :unidade_nome, :municipio_nome, :uf_sigla, :codigo_ibge,
                            :modalidade_codigo, :modalidade_nome, :modo_disputa_codigo, :modo_disputa_nome,
                            :tipo_instrumento_codigo, :data_publicacao_pncp, :data_abertura_proposta,
                            :data_encerramento_proposta, :valor_total_estimado, :valor_total_homologado,
                            :link_sistema_origem, :link_processo_eletronico, :fonte_tipo, :fonte_data_referencia,
                            :oportunidade_score, :urgencia_score, :aderencia_score, :valor_score, :risco_score,
                            :search_blob, :created_at, :updated_at
                        )
                        """,
                        payload,
                    )
            conn.execute("INSERT INTO opportunities_fts(opportunities_fts) VALUES ('rebuild')")
        return inserted, updated

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
            return {
                'total': total,
                'latest': latest,
                'open_now': open_now,
                'urgent': urgent,
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
