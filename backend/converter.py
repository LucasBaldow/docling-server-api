import logging
import json
from pathlib import Path
from docling.document_converter import DocumentConverter
from typing import Dict, Any
import xmltodict

logger = logging.getLogger(__name__)
_CONVERTER = DocumentConverter()  # Reuso da instância para leve ganho de performance

def converter_arquivo(source: str) -> Dict[str, Any]:
    """
    Converte qualquer documento ou URL suportado pelo Docling para um dict JSON:
      - texts: blocos de texto extraídos
      - tables: cada tabela (sheet) como lista de registros
      - metadata: metadados extraídos (se houver)
      - xml: dicionário completo caso seja um arquivo .xml
    """
    try:
        # 1) Tratamento específico para XML
        if source.lower().endswith(".xml"):
            with open(source, encoding="utf-8") as f:
                xml_dict = xmltodict.parse(f.read(), process_namespaces=True)
            return {"xml": xml_dict}

        # 2) Para os demais formatos suportados pelo Docling
        doc = _CONVERTER.convert(source).document
        doc_dict = doc.export_to_dict()

        # 2.1) Extrai textos limpos
        texts = [
            itm["text"].strip()
            for itm in doc_dict.get("texts", [])
            if itm.get("text", "").strip()
        ]

        # 2.2) Extrai tabelas do documento
        tables = []
        for table in doc.tables:  # TableItem
            df = table.export_to_dataframe()            # → pandas.DataFrame
            records = df.to_dict(orient="records")      # → lista de dicionários
            tables.append({
                "sheet_name": getattr(table, "name", None),
                "data": records
            })

        # 2.3) Metadados (opcional)
        metadata = doc_dict.get("metadata", {})

        return {"texts": texts, "tables": tables, "metadata": metadata}

    except Exception as e:
        logger.error("Falha ao processar %s: %s", source, e)
        return {"error": f"Não foi possível processar '{source}': {e}"}


def processar_pasta(pasta_path: str) -> Dict[str, Dict]:
    """
    Aplica converter_arquivo() a todos os arquivos dentro de uma pasta (recursivamente).
    Retorna dict: { "subdir/arquivo.ext": resultado_dict, ... }.
    """
    resultados = {}
    base = Path(pasta_path)
    for arquivo in base.rglob("*"):
        if arquivo.is_file():
            rel = str(arquivo.relative_to(base))
            resultados[rel] = converter_arquivo(str(arquivo))
    return resultados
