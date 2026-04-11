from __future__ import annotations

from typing import Any

from app.core.config import DEFAULT_MODALIDADES_SCAN, MODALIDADES, MODO_DISPUTA, NICHOS_PRONTOS
from app.core.utils import compact_keywords, fold_text, human_days_to_deadline, normalize_text, score_from_value, summarize_object


SINONIMOS = {
    'combustivel': ['gasolina', 'diesel', 'etanol', 'lubrificante'],
    'merenda': ['generos alimenticios', 'alimento', 'alimentacao escolar'],
    'grafica': ['grafico', 'impressao', 'banner', 'plotagem'],
    'limpeza': ['higiene', 'saneante', 'descartavel'],
    'software': ['licenca', 'informatica', 'sistema', 'ti'],
    'obra': ['engenharia', 'reforma', 'pavimentacao', 'construcao'],
}


def infer_nichos(objeto: str) -> list[str]:
    text = fold_text(objeto)
    hits: list[str] = []
    for nome, termos in NICHOS_PRONTOS.items():
        if any(t in text for t in termos):
            hits.append(nome)
    return hits



def expand_query(termo: str) -> str:
    text = fold_text(termo)
    tokens = [text]
    for base, synonyms in SINONIMOS.items():
        if base in text:
            tokens.extend(synonyms)
    return ' '.join(dict.fromkeys(tokens))



def compute_scores(row: dict[str, Any]) -> dict[str, float]:
    days = human_days_to_deadline(row.get('data_encerramento_proposta'))
    if days is None:
        urgencia = 25.0
    elif days < 0:
        urgencia = 0.0
    elif days <= 1:
        urgencia = 100.0
    elif days <= 3:
        urgencia = 85.0
    elif days <= 7:
        urgencia = 65.0
    elif days <= 15:
        urgencia = 40.0
    else:
        urgencia = 20.0

    valor = score_from_value(row.get('valor_total_estimado'))
    nichos = infer_nichos(row.get('objeto_compra') or '')
    aderencia = 40.0 + min(45.0, len(nichos) * 15.0)
    if row.get('modalidade_codigo') in (6, 4, 8):
        aderencia += 10.0
    aderencia = min(100.0, aderencia)

    risco = 10.0
    if not row.get('link_sistema_origem'):
        risco += 20.0
    if not row.get('orgao_razao_social'):
        risco += 20.0
    if row.get('valor_total_estimado') in (None, 0, 0.0):
        risco += 15.0
    risco = min(100.0, risco)

    oportunidade = round((urgencia * 0.35) + (valor * 0.30) + (aderencia * 0.30) - (risco * 0.15), 1)
    return {
        'oportunidade_score': max(0.0, min(100.0, oportunidade)),
        'urgencia_score': urgencia,
        'aderencia_score': aderencia,
        'valor_score': valor,
        'risco_score': risco,
    }



def normalize_summary_item(item: dict[str, Any], endpoint: str, fonte_data_referencia: str) -> dict[str, Any]:
    orgao = item.get('orgaoEntidade') or {}
    unidade = item.get('unidadeOrgao') or {}
    objeto = normalize_text(item.get('objetoCompra'))
    modalidade_codigo = item.get('modalidadeCompraCodigo') or item.get('modalidadeContratacaoCodigo') or item.get('modalidadeCodigo') or item.get('codigoModalidadeContratacao')
    modo_disputa_codigo = item.get('modoDisputaCodigo')
    row = {
        'numero_controle_pncp': normalize_text(item.get('numeroControlePNCP') or item.get('numeroControlePncp')),
        'numero_compra': normalize_text(item.get('numeroCompra')),
        'ano_compra': item.get('anoCompra'),
        'sequencial_compra': item.get('sequencialCompra'),
        'processo': normalize_text(item.get('processo')),
        'objeto_compra': objeto,
        'resumo_objeto': summarize_object(objeto),
        'orgao_cnpj': normalize_text(orgao.get('cnpj')),
        'orgao_razao_social': normalize_text(orgao.get('razaoSocial')),
        'poder_id': normalize_text(orgao.get('poderId')),
        'esfera_id': normalize_text(orgao.get('esferaId')),
        'unidade_codigo': normalize_text(unidade.get('codigoUnidade')),
        'unidade_nome': normalize_text(unidade.get('nomeUnidade')),
        'municipio_nome': normalize_text(unidade.get('municipioNome')),
        'uf_sigla': normalize_text(unidade.get('ufSigla')),
        'codigo_ibge': normalize_text(unidade.get('codigoIbge')),
        'modalidade_codigo': modalidade_codigo,
        'modalidade_nome': MODALIDADES.get(int(modalidade_codigo), '') if modalidade_codigo else '',
        'modo_disputa_codigo': modo_disputa_codigo,
        'modo_disputa_nome': MODO_DISPUTA.get(int(modo_disputa_codigo), '') if modo_disputa_codigo else '',
        'tipo_instrumento_codigo': item.get('tipoInstrumentoConvocatorioCodigo'),
        'data_publicacao_pncp': normalize_text(item.get('dataPublicacaoPncp'))[:10],
        'data_abertura_proposta': normalize_text(item.get('dataAberturaProposta'))[:10],
        'data_encerramento_proposta': normalize_text(item.get('dataEncerramentoProposta'))[:10],
        'valor_total_estimado': item.get('valorTotalEstimado') or 0,
        'valor_total_homologado': item.get('valorTotalHomologado') or 0,
        'link_sistema_origem': normalize_text(item.get('linkSistemaOrigem')),
        'link_processo_eletronico': normalize_text(item.get('linkProcessoEletronico')),
        'fonte_tipo': 'pncp_api',
        'fonte_endpoint': endpoint,
        'fonte_data_referencia': fonte_data_referencia,
        'is_open_proposal': 1 if endpoint == 'proposta' else 0,
        'search_blob': '',
    }
    row['search_blob'] = compact_keywords(
        row['objeto_compra'],
        row['resumo_objeto'],
        row['orgao_razao_social'],
        row['municipio_nome'],
        row['uf_sigla'],
        row['modalidade_nome'],
        ' '.join(infer_nichos(objeto)),
    )
    row.update(compute_scores(row))
    return row



def apply_detail(summary_row: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    row = dict(summary_row)
    for src_key, dst_key in {
        'valorTotalEstimado': 'valor_total_estimado',
        'valorTotalHomologado': 'valor_total_homologado',
        'linkSistemaOrigem': 'link_sistema_origem',
        'linkProcessoEletronico': 'link_processo_eletronico',
        'objetoCompra': 'objeto_compra',
        'processo': 'processo',
    }.items():
        value = detail.get(src_key)
        if value not in (None, ''):
            row[dst_key] = value if not isinstance(value, str) else normalize_text(value)
    row['resumo_objeto'] = summarize_object(row.get('objeto_compra'))
    row['search_blob'] = compact_keywords(
        row.get('objeto_compra'),
        row.get('resumo_objeto'),
        row.get('orgao_razao_social'),
        row.get('municipio_nome'),
        row.get('uf_sigla'),
        row.get('modalidade_nome'),
    )
    row.update(compute_scores(row))
    return row
