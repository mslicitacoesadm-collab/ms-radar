from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from app.core.config import DB_PATH
from app.core.search_engine import expand_query


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
                    fonte_endpoint TEXT,
                    fonte_data_referencia TEXT,
                    is_open_proposal INTEGER DEFAULT 0,
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

                CREATE INDEX IF NOT EXISTS idx_opportunities_data_encerramento ON opportunities(data_encerramento_proposta);
                CREATE INDEX IF NOT EXISTS idx_opportunities_uf ON opportunities(uf_sigla);
                CREATE INDEX IF NOT EXISTS idx_opportunities_municipio ON opportunities(municipio_nome);
                CREATE INDEX IF NOT EXISTS idx_opportunities_modalidade ON opportunities(modalidade_codigo);
                CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(oportunidade_score DESC);
                CREATE INDEX IF NOT EXISTS idx_opportunities_detail_status ON opportunities(detail_status);
                CREATE INDEX IF NOT EXISTS idx_opportunities_open ON opportunities(is_open_proposal);

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

                CREATE TABLE IF NOT EXISTS app_state (
                    state_key TEXT PRIMARY KEY,
                    state_value TEXT,
                    updated_at TEXT NOT NULL
                );
                """
            )
            for col, ddl in {
                'fonte_endpoint': 'ALTER TABLE opportunities ADD COLUMN fonte_endpoint TEXT',
                'is_open_proposal': 'ALTER TABLE opportunities ADD COLUMN is_open_proposal INTEGER DEFAULT 0',
            }.items():
                existing = {r['name'] for r in conn.execute('PRAGMA table_info(opportunities)').fetchall()}
                if col not in existing:
                    conn.execute(ddl)

    def rebuild_fts(self) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO opportunities_fts(opportunities_fts) VALUES ('rebuild')")

    def stats(self) -> dict[str, int]:
        with self.connect() as conn:
            total = conn.execute('SELECT COUNT(*) FROM opportunities').fetchone()[0]
            open_now = conn.execute("SELECT COUNT(*) FROM opportunities WHERE is_open_proposal = 1 AND date(COALESCE(data_encerramento_proposta,'')) >= date('now')").fetchone()[0]
            urgent = conn.execute("SELECT COUNT(*) FROM opportunities WHERE date(COALESCE(data_encerramento_proposta,'')) BETWEEN date('now') AND date('now', '+2 day')").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM opportunities WHERE detail_status IN ('summary', 'retry')").fetchone()[0]
            detailed = conn.execute("SELECT COUNT(*) FROM opportunities WHERE detail_status = 'done'").fetchone()[0]
        return {'total': total, 'open_now': open_now, 'urgent': urgent, 'pending_details': pending, 'detailed': detailed}

    def distinct_values(self, field: str) -> list[str]:
        if field not in {'uf_sigla', 'municipio_nome', 'modalidade_nome'}:
            return []
        with self.connect() as conn:
            rows = conn.execute(f"SELECT DISTINCT {field} FROM opportunities WHERE COALESCE({field}, '') <> '' ORDER BY {field}").fetchall()
        return [r[0] for r in rows]

    def export_rows(self, sql: str, params: tuple[Any, ...] = ()):
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def recent_sync_runs(self, limit: int = 20):
        with self.connect() as conn:
            return conn.execute('SELECT * FROM sync_runs ORDER BY id DESC LIMIT ?', (limit,)).fetchall()

    def create_sync_run(self, source: str, details: str = '') -> int:
        now = datetime.utcnow().isoformat()
        with self.connect() as conn:
            cur = conn.execute(
                'INSERT INTO sync_runs(started_at, status, source, details) VALUES (?, ?, ?, ?)',
                (now, 'running', source, details),
            )
            return int(cur.lastrowid)

    def finish_sync_run(self, run_id: int, status: str, total_imported: int, total_updated: int, total_seen: int, details: str = '') -> None:
        with self.connect() as conn:
            conn.execute(
                'UPDATE sync_runs SET finished_at = ?, status = ?, total_imported = ?, total_updated = ?, total_seen = ?, details = ? WHERE id = ?',
                (datetime.utcnow().isoformat(), status, total_imported, total_updated, total_seen, details, run_id),
            )

    def set_state(self, key: str, value: str) -> None:
        now = datetime.utcnow().isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO app_state(state_key, state_value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET state_value = excluded.state_value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )

    def get_state(self, key: str, default: str = '') -> str:
        with self.connect() as conn:
            row = conn.execute('SELECT state_value FROM app_state WHERE state_key = ?', (key,)).fetchone()
        return row['state_value'] if row else default

    def upsert_opportunities(self, rows: Iterable[dict[str, Any]], detail_status: str = 'summary') -> tuple[int, int]:
        inserted = updated = 0
        now = datetime.utcnow().isoformat()
        columns = [
            'numero_controle_pncp', 'numero_compra', 'ano_compra', 'sequencial_compra', 'processo',
            'objeto_compra', 'resumo_objeto', 'orgao_cnpj', 'orgao_razao_social', 'poder_id', 'esfera_id',
            'unidade_codigo', 'unidade_nome', 'municipio_nome', 'uf_sigla', 'codigo_ibge', 'modalidade_codigo',
            'modalidade_nome', 'modo_disputa_codigo', 'modo_disputa_nome', 'tipo_instrumento_codigo',
            'data_publicacao_pncp', 'data_abertura_proposta', 'data_encerramento_proposta',
            'valor_total_estimado', 'valor_total_homologado', 'link_sistema_origem', 'link_processo_eletronico',
            'fonte_tipo', 'fonte_endpoint', 'fonte_data_referencia', 'is_open_proposal', 'oportunidade_score',
            'urgencia_score', 'aderencia_score', 'valor_score', 'risco_score', 'search_blob',
            'detail_status', 'last_detail_attempt', 'last_detail_error', 'created_at', 'updated_at'
        ]
        with self.connect() as conn:
            for row in rows:
                current = conn.execute('SELECT numero_controle_pncp, created_at, detail_status, is_open_proposal FROM opportunities WHERE numero_controle_pncp = ?', (row['numero_controle_pncp'],)).fetchone()
                payload = dict(row)
                payload['created_at'] = current['created_at'] if current else now
                payload['updated_at'] = now
                payload['detail_status'] = current['detail_status'] if current and current['detail_status'] == 'done' else detail_status
                payload['last_detail_attempt'] = None
                payload['last_detail_error'] = None
                payload['is_open_proposal'] = max(int(payload.get('is_open_proposal') or 0), int(current['is_open_proposal']) if current else 0)
                values = [payload.get(col) for col in columns]
                placeholders = ', '.join(['?'] * len(columns))
                updates = ', '.join([f'{c}=excluded.{c}' for c in columns if c not in ('numero_controle_pncp', 'created_at')])
                conn.execute(
                    f"INSERT INTO opportunities({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT(numero_controle_pncp) DO UPDATE SET {updates}",
                    values,
                )
                if current:
                    updated += 1
                else:
                    inserted += 1
        return inserted, updated

    def pending_detail_candidates(self, limit: int = 20):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM opportunities
                WHERE detail_status IN ('summary', 'retry')
                  AND COALESCE(orgao_cnpj, '') <> ''
                  AND ano_compra IS NOT NULL
                  AND sequencial_compra IS NOT NULL
                ORDER BY COALESCE(last_detail_attempt, '') ASC, oportunidade_score DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def update_detail_payload(self, numero_controle_pncp: str, merged: dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE opportunities
                SET processo = ?, objeto_compra = ?, resumo_objeto = ?, valor_total_estimado = ?, valor_total_homologado = ?,
                    link_sistema_origem = ?, link_processo_eletronico = ?, oportunidade_score = ?, urgencia_score = ?,
                    aderencia_score = ?, valor_score = ?, risco_score = ?, search_blob = ?, detail_status = 'done',
                    last_detail_attempt = ?, last_detail_error = NULL, updated_at = ?
                WHERE numero_controle_pncp = ?
                """,
                (
                    merged.get('processo'), merged.get('objeto_compra'), merged.get('resumo_objeto'), merged.get('valor_total_estimado'),
                    merged.get('valor_total_homologado'), merged.get('link_sistema_origem'), merged.get('link_processo_eletronico'),
                    merged.get('oportunidade_score'), merged.get('urgencia_score'), merged.get('aderencia_score'), merged.get('valor_score'),
                    merged.get('risco_score'), merged.get('search_blob'), now, now, numero_controle_pncp,
                ),
            )

    def mark_detail_status(self, numero_controle_pncp: str, status: str, error: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                'UPDATE opportunities SET detail_status = ?, last_detail_attempt = ?, last_detail_error = ?, updated_at = ? WHERE numero_controle_pncp = ?',
                (status, datetime.utcnow().isoformat(), error, datetime.utcnow().isoformat(), numero_controle_pncp),
            )

    def save_alert_profile(self, payload: dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO alert_profiles(nome, termos, uf_sigla, municipio_nome, modalidade_codigo, valor_min, valor_max, somente_abertas, canal_email, ativo, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    payload['nome'], payload['termos'], payload.get('uf_sigla'), payload.get('municipio_nome'), payload.get('modalidade_codigo'),
                    payload.get('valor_min'), payload.get('valor_max'), 1 if payload.get('somente_abertas', True) else 0,
                    payload.get('canal_email'), now, now,
                ),
            )

    def list_alert_profiles(self):
        with self.connect() as conn:
            return conn.execute('SELECT * FROM alert_profiles WHERE ativo = 1 ORDER BY id DESC').fetchall()

    def search_opportunities(
        self,
        *,
        query: str = '',
        uf: str = '',
        municipio: str = '',
        modalidade_codigo: int | None = None,
        only_open: bool = True,
        valor_min: float | None = None,
        valor_max: float | None = None,
        sort_by: str = 'score',
        limit: int = 50,
    ):
        where: list[str] = []
        params: list[Any] = []
        join = ''
        order = 'o.oportunidade_score DESC, o.data_encerramento_proposta ASC'

        if query.strip():
            expanded = expand_query(query)
            join = 'JOIN opportunities_fts fts ON fts.rowid = o.rowid'
            where.append('fts.opportunities_fts MATCH ?')
            params.append(' OR '.join(token + '*' for token in expanded.split() if token))
        if uf:
            where.append('o.uf_sigla = ?')
            params.append(uf)
        if municipio:
            where.append('o.municipio_nome = ?')
            params.append(municipio)
        if modalidade_codigo:
            where.append('o.modalidade_codigo = ?')
            params.append(modalidade_codigo)
        if only_open:
            where.append("o.is_open_proposal = 1 AND date(COALESCE(o.data_encerramento_proposta,'')) >= date('now')")
        if valor_min and valor_min > 0:
            where.append('COALESCE(o.valor_total_estimado, 0) >= ?')
            params.append(valor_min)
        if valor_max and valor_max > 0:
            where.append('COALESCE(o.valor_total_estimado, 0) <= ?')
            params.append(valor_max)

        if sort_by == 'prazo':
            order = 'o.data_encerramento_proposta ASC, o.oportunidade_score DESC'
        elif sort_by == 'valor':
            order = 'o.valor_total_estimado DESC, o.oportunidade_score DESC'
        elif sort_by == 'recentes':
            order = 'o.updated_at DESC'

        sql = 'SELECT o.* FROM opportunities o '
        if join:
            sql += join + ' '
        if where:
            sql += 'WHERE ' + ' AND '.join(where) + ' '
        sql += f'ORDER BY {order} LIMIT ?'
        params.append(limit)
        return self.export_rows(sql, tuple(params))
