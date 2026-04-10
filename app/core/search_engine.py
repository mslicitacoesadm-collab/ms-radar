from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.core.config import MODALIDADES, MODO_DISPUTA
from app.core.utils import clean_text, compact_keywords, parse_datetime, unique_words


NICHO_KEYWORDS = {
    'saúde': ['medicamento', 'hospitalar', 'saúde', 'odontológico', 'enfermagem', 'laboratorial'],
    'alimentação': ['merenda', 'gêneros alimentícios', 'alimentação', 'hortifruti', 'cestas básicas'],
    'combustível': ['combustível', 'diesel', 'gasolina', 'lubrificante', 'etanol'],
    'limpeza': ['limpeza', 'higiene', 'saneante', 'descartável', 'material de limpeza'],
    'obras': ['obra', 'engenharia', 'reforma', 'pavimentação', 'construção'],
    't.i.c.': ['software', 'licença', 'computador', 'tic', 'informatica', 'tecnologia'],
}


def infer_nicho(text: str) -> str:
    lower = text.lower()
    best_name = 'geral'
    best_hits = 0
    for name, words in NICHO_KEYWORDS.items():
        hits = sum(1 for word in words if word in lower)
        if hits > best_hits:
            best_hits = hits
            best_name = name
    return best_name


def summarize_object(text: str, max_len: int = 180) -> str:
    text = clean_text(text)
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(' ', 1)[0]
    return f'{cut}…'


def compute_scores(row: dict[str, Any]) -> dict[str, float]:
    objeto = clean_text(row.get('objeto_compra'))
    valor = float(row.get('valor_total_estimado') or 0)

    encerramento = parse_datetime(row.get('data_encerramento_proposta'))
    urgencia = 20.0
    if encerramento:
        days = (encerramento.date() - date.today()).days
        if days < 0:
            urgencia = 0.0
        elif days <= 1:
            urgencia = 100.0
        elif days <= 3:
            urgencia = 85.0
        elif days <= 7:
            urgencia = 70.0
        elif days <= 15:
            urgencia = 50.0
        else:
            urgencia = 25.0

    valor_score = 0.0
    if valor > 0:
        if valor >= 1_000_000:
            valor_score = 100.0
        elif valor >= 300_000:
            valor_score = 80.0
        elif valor >= 100_000:
            valor_score = 60.0
        elif valor >= 30_000:
            valor_score = 40.0
        else:
            valor_score = 20.0

    aderencia = 25.0
    niche = infer_nicho(objeto)
    if niche != 'geral':
        aderencia = 80.0
    if 'registro de preços' in objeto.lower():
        aderencia += 5.0
    if 'serviço continuado' in objeto.lower() or 'continuada' in objeto.lower():
        aderencia += 5.0
    aderencia = min(100.0, aderencia)

    risco = 15.0
    if not row.get('link_processo_eletronico'):
        risco += 20.0
    if not row.get('link_sistema_origem'):
        risco += 20.0
    if row.get('modalidade_codigo') in (5, 7):
        risco += 15.0
    if row.get('valor_total_estimado') in (None, 0):
        risco += 10.0
    risco = min(100.0, risco)

    oportunidade = round((urgencia * 0.35) + (aderencia * 0.35) + (valor_score * 0.30), 2)

    return {
        'oportunidade_score': oportunidade,
        'urgencia_score': round(urgencia, 2),
        'aderencia_score': round(aderencia, 2),
        'valor_score': round(valor_score, 2),
        'risco_score': round(risco, 2),
    }


def normalize_summary_item(item: dict[str, Any], fonte_tipo: str, fonte_data_referencia: str) -> dict[str, Any]:
    orgao = item.get('orgaoEntidade') or {}
    unidade = item.get('unidadeOrgao') or {}
    objeto = clean_text(item.get('objetoCompra'))
    modalidade_codigo = item.get('modalidadeId') or item.get('modalidadeCompraCodigo') or item.get('codigoModalidadeContratacao')
    modo_disputa_codigo = item.get('modoDisputaId') or item.get('modoDisputaCodigo')

    row = {
        'numero_controle_pncp': item.get('numeroControlePNCP') or item.get('numeroControlePncp') or '',
        'numero_compra': clean_text(item.get('numeroCompra')),
        'ano_compra': item.get('anoCompra'),
        'sequencial_compra': item.get('sequencialCompra'),
        'processo': clean_text(item.get('processo')),
        'objeto_compra': objeto,
        'resumo_objeto': summarize_object(objeto),
        'orgao_cnpj': clean_text(orgao.get('cnpj')),
        'orgao_razao_social': clean_text(orgao.get('razaoSocial')),
        'poder_id': clean_text(orgao.get('poderId')),
        'esfera_id': clean_text(orgao.get('esferaId')),
        'unidade_codigo': clean_text(unidade.get('codigoUnidade')),
        'unidade_nome': clean_text(unidade.get('nomeUnidade')),
        'municipio_nome': clean_text(unidade.get('municipioNome')),
        'uf_sigla': clean_text(unidade.get('ufSigla')),
        'codigo_ibge': clean_text(unidade.get('codigoIbge')),
        'modalidade_codigo': modalidade_codigo,
        'modalidade_nome': MODALIDADES.get(int(modalidade_codigo), clean_text(item.get('modalidadeNome'))) if modalidade_codigo else clean_text(item.get('modalidadeNome')),
        'modo_disputa_codigo': modo_disputa_codigo,
        'modo_disputa_nome': MODO_DISPUTA.get(int(modo_disputa_codigo), clean_text(item.get('modoDisputaNome'))) if modo_disputa_codigo else clean_text(item.get('modoDisputaNome')),
        'tipo_instrumento_codigo': item.get('tipoInstrumentoConvocatorioCodigo'),
        'data_publicacao_pncp': clean_text(item.get('dataPublicacaoPncp')),
        'data_abertura_proposta': clean_text(item.get('dataAberturaProposta')),
        'data_encerramento_proposta': clean_text(item.get('dataEncerramentoProposta')),
        'valor_total_estimado': item.get('valorTotalEstimado') or 0,
        'valor_total_homologado': item.get('valorTotalHomologado') or 0,
        'link_sistema_origem': clean_text(item.get('linkSistemaOrigem')),
        'link_processo_eletronico': clean_text(item.get('linkProcessoEletronico')),
        'fonte_tipo': fonte_tipo,
        'fonte_data_referencia': fonte_data_referencia,
        'search_blob': '',
    }
    row['search_blob'] = compact_keywords(
        row['objeto_compra'],
        row['resumo_objeto'],
        row['orgao_razao_social'],
        row['municipio_nome'],
        row['modalidade_nome'],
        infer_nicho(objeto),
        ' '.join(unique_words([objeto])),
    )
    row.update(compute_scores(row))
    return row


def apply_detail(summary_row: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    row = dict(summary_row)
    row['valor_total_estimado'] = detail.get('valorTotalEstimado') or row.get('valor_total_estimado')
    row['valor_total_homologado'] = detail.get('valorTotalHomologado') or row.get('valor_total_homologado')
    row['link_sistema_origem'] = clean_text(detail.get('linkSistemaOrigem')) or row.get('link_sistema_origem')
    row['link_processo_eletronico'] = clean_text(detail.get('linkProcessoEletronico')) or row.get('link_processo_eletronico')
    row.update(compute_scores(row))
    return row
