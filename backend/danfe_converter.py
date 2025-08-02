import logging
import json
import re
from pathlib import Path
from docling.document_converter import DocumentConverter
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
_CONVERTER = DocumentConverter()  # Reuso da instância


def converter_danfe(source: str) -> Dict[str, Any]:
    """
    Converte DANFE extraindo key-value pairs estruturados.
    Retorna apenas: texts, tables, metadata e key_value_pairs.
    """
    try:
        # Converter documento
        doc = _CONVERTER.convert(source).document
        doc_dict = doc.export_to_dict()

        # 1) Textos limpos
        texts = [
            itm["text"].strip()
            for itm in doc_dict.get("texts", [])
            if itm.get("text", "").strip()
        ]

        # 2) Tabelas
        tables = []
        for table in doc.tables:
            df = table.export_to_dataframe()
            records = df.to_dict(orient="records")
            tables.append({
                "sheet_name": getattr(table, "name", None),
                "data": records
            })

        # 3) Metadados
        metadata = doc_dict.get("metadata", {})

        # 4) Textos estruturados como key-value pairs para DANFE
        structured_texts = extract_danfe_key_values(doc_dict.get("texts", []))

        return {
            "texts": structured_texts,  # Agora são os pares chave-valor estruturados
            "tables": tables, 
            "metadata": metadata
        }

    except Exception as e:
        logger.error("Falha ao processar DANFE %s: %s", source, e)
        return {"error": f"Não foi possível processar '{source}': {e}"}


def extract_danfe_key_values(texts_raw: List[Dict]) -> List[Dict]:
    """
    Extrai pares chave-valor específicos de DANFE dos textos brutos.
    """
    # Labels conhecidos em DANFE
    label_patterns = [
        r'INSCRI[ÇC][ÃA]O ESTADUAL',
        r'C\.?N\.?P\.?J\.?',
        r'C\.?P\.?F\.?',
        r'CEP',
        r'UF',
        r'NOME.*RAZ[ÃA]O SOCIAL',
        r'ENDERE[ÇC]O',
        r'MUNIC[ÍI]PIO',
        r'FONE.*FAX',
        r'DATA.*EMISS[ÃA]O',
        r'DATA.*SA[ÍI]DA',
        r'HORA.*SA[ÍI]DA',
        r'VALOR.*TOTAL',
        r'BASE.*C[ÁA]LCULO',
        r'CHAVE.*ACESSO',
        r'PROTOCOLO.*AUTORIZA[ÇC][ÃA]O',
        r'S[ÉE]RIE',
        r'N[ÚU]MERO.*NF',
        r'NATUREZA.*OPERA[ÇC][ÃA]O',
        r'PLACA.*VE[ÍI]CULO',
        r'C[ÓO]DIGO ANTT'
    ]
    
    kv_pairs = []
    
    for i, text_item in enumerate(texts_raw):
        text_content = text_item.get("text", "").strip()
        
        # Verificar se é um label conhecido
        if _is_danfe_label(text_content, label_patterns):
            # Procurar valor próximo
            value = _find_value_nearby(texts_raw, i)
            
            if value:
                kv_pairs.append({
                    "label": text_content,
                    "value": value,
                    "category": _categorize_danfe_field(text_content)
                })
    
    return kv_pairs


def _is_danfe_label(text: str, patterns: List[str]) -> bool:
    """Verifica se texto é um label conhecido de DANFE."""
    if not text or len(text) < 3 or len(text) > 60:
        return False
    
    text_clean = text.upper().replace(".", "").replace(":", "").replace("/", "")
    
    # Verificar padrões específicos
    for pattern in patterns:
        if re.search(pattern, text_clean):
            return True
    
    # Padrões gerais de labels
    if (text.endswith(":") or 
        text.endswith("ˆO") or  # OCR de AÇÃO, ÇÃO
        text.endswith("˙O") or  # OCR variante
        (text.isupper() and " " in text and len(text.split()) <= 4)):
        return True
    
    return False


def _find_value_nearby(texts: List[Dict], label_index: int) -> str:
    """Encontra valor próximo ao label."""
    # Procurar nos próximos 5 textos
    for i in range(label_index + 1, min(label_index + 6, len(texts))):
        candidate_text = texts[i].get("text", "").strip()
        
        # Pular candidatos vazios ou muito longos
        if not candidate_text or len(candidate_text) > 100:
            continue
        
        # Pular se parecer outro label
        if _looks_like_label(candidate_text):
            continue
        
        return candidate_text
    
    return ""


def _looks_like_label(text: str) -> bool:
    """Verifica se texto parece ser outro label."""
    text_upper = text.upper()
    label_keywords = [
        "CNPJ", "CPF", "INSCRICAO", "CEP", "UF", "ENDERECO", 
        "MUNICIPIO", "FONE", "DATA", "HORA", "VALOR", "SERIE", 
        "NUMERO", "CHAVE", "PROTOCOLO", "NATUREZA", "CODIGO"
    ]
    
    return any(keyword in text_upper for keyword in label_keywords)


def _categorize_danfe_field(label: str) -> str:
    """Categoriza campo de DANFE."""
    label_upper = label.upper()
    
    if any(word in label_upper for word in ["CNPJ", "CPF", "INSCRICAO", "ESTADUAL"]):
        return "identificacao"
    elif any(word in label_upper for word in ["ENDERECO", "CEP", "UF", "MUNICIPIO", "FONE"]):
        return "endereco"
    elif any(word in label_upper for word in ["DATA", "HORA", "EMISSAO", "SAIDA"]):
        return "temporal"
    elif any(word in label_upper for word in ["VALOR", "TOTAL", "BASE", "CALCULO", "ICMS", "IPI"]):
        return "financeiro"
    elif any(word in label_upper for word in ["CHAVE", "PROTOCOLO", "SERIE", "NUMERO"]):
        return "fiscal"
    elif any(word in label_upper for word in ["NOME", "RAZAO", "SOCIAL"]):
        return "entidade"
    elif any(word in label_upper for word in ["NATUREZA", "OPERACAO", "CODIGO", "PLACA"]):
        return "operacional"
    else:
        return "outros"


def _calculate_confidence(label: str, value: str) -> float:
    """Calcula confiança da associação label-value."""
    label_upper = label.upper()
    
    # Padrões específicos com alta confiança
    if "CNPJ" in label_upper and re.match(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", value):
        return 0.95
    elif "CPF" in label_upper and re.match(r"\d{3}\.\d{3}\.\d{3}-\d{2}", value):
        return 0.95
    elif "CEP" in label_upper and re.match(r"\d{5}-\d{3}", value):
        return 0.9
    elif "UF" in label_upper and re.match(r"^[A-Z]{2}$", value):
        return 0.9
    elif "DATA" in label_upper and re.match(r"\d{2}/\d{2}/\d{4}", value):
        return 0.9
    elif "HORA" in label_upper and re.match(r"\d{2}:\d{2}", value):
        return 0.85
    elif "VALOR" in label_upper and re.match(r"\d{1,3}(?:\.\d{3})*,\d{2}", value):
        return 0.85
    elif "CHAVE" in label_upper and len(value.replace(" ", "")) == 44:
        return 0.9
    else:
        return 0.7


def test_danfe():
    """Função de teste rápido."""
    pdf_file = "DANFE_312057.PDF"
    
    print("🚀 Testando extração de DANFE...")
    result = converter_danfe(pdf_file)
    
    if "error" in result:
        print(f"❌ Erro: {result['error']}")
        return
    
    # Salvar resultado
    with open("danfe_clean_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    # Mostrar resumo
    print(f"📊 RESUMO:")
    print(f"Textos estruturados: {len(result['texts'])}")
    print(f"Tabelas: {len(result['tables'])}")
    
    # Mostrar textos estruturados por categoria
    texts = result['texts']
    by_category = {}
    for text in texts:
        cat = text['category']
        by_category[cat] = by_category.get(cat, 0) + 1
    
    print(f"\n📋 TEXTOS POR CATEGORIA:")
    for cat, count in by_category.items():
        print(f"  {cat}: {count} campos")
    
    # Mostrar alguns exemplos
    print(f"\n🔍 EXEMPLOS (primeiros 10):")
    for text in texts[:10]:
        print(f"  {text['category']}: {text['label']} → {text['value']}")
    
    print(f"\n✅ Resultado salvo: danfe_clean_result.json")


if __name__ == "__main__":
    test_danfe()