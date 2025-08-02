import io
import json
import logging
import tempfile
import zipfile, rarfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from backend.converter import converter_arquivo, processar_pasta
from backend.danfe_converter import converter_danfe

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI()

def _remove_file(path: str):
    try:
        Path(path).unlink()
    except Exception as e:
        logger.warning("Erro ao remover %s: %s", path, e)
        

@app.post("/upload-file/")
def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
    
):
    """
    Recebe um UploadFile, salva temporariamente, converte e devolve
    o JSON resultante como arquivo, limpando temporários após a resposta.
    """
    try:
        # 1) Salvar arquivo recebido em temp file
        suffix = Path(file.filename).suffix or ""
        tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp_input.write(file.file.read())                              # I/O em disco controlado
        tmp_input.flush()
        tmp_input.close()

        # 2) Converter documento
        resultado = converter_arquivo(tmp_input.name)

        # 3) Gravar JSON em arquivo temporário
        tmp_json = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp_json.write(json.dumps(resultado, ensure_ascii=False).encode())
        tmp_json.flush()
        tmp_json.close()

        # 4) Agendar limpeza dos temporários
        background_tasks.add_task(_remove_file, tmp_input.name)         # Limpeza em background
        background_tasks.add_task(_remove_file, tmp_json.name)

        # 5) Retornar JSON como FileResponse
        return FileResponse(
            path=tmp_json.name,
            media_type="application/json",
            filename=f"{Path(file.filename).stem}.json"
        )

    except Exception as e:
        logger.error("Erro em /upload-file/: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/upload-danfe/")
def upload_danfe(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Recebe um arquivo DANFE (PDF), processa com extração de key-value pairs
    e retorna JSON estruturado com texts, tables e metadata.
    """
    try:
        # Validar se é PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Arquivo deve ser um PDF")
        
        # 1) Salvar arquivo recebido em temp file
        suffix = Path(file.filename).suffix or ""
        tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp_input.write(file.file.read())
        tmp_input.flush()
        tmp_input.close()

        # 2) Converter DANFE com extração específica
        resultado = converter_danfe(tmp_input.name)

        # 3) Verificar se houve erro no processamento
        if "error" in resultado:
            background_tasks.add_task(_remove_file, tmp_input.name)
            raise HTTPException(status_code=400, detail=resultado["error"])

        # 4) Gravar JSON em arquivo temporário
        tmp_json = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp_json.write(json.dumps(resultado, ensure_ascii=False).encode())
        tmp_json.flush()
        tmp_json.close()

        # 5) Agendar limpeza dos temporários
        background_tasks.add_task(_remove_file, tmp_input.name)
        background_tasks.add_task(_remove_file, tmp_json.name)

        # 6) Retornar JSON como FileResponse
        return FileResponse(
            path=tmp_json.name,
            media_type="application/json",
            filename=f"{Path(file.filename).stem}_danfe.json"
        )

    except HTTPException:
        # Re-raise HTTPException para manter status code
        raise
    except Exception as e:
        logger.error("Erro em /upload-danfe/: %s", e)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

   
@app.post("/upload-archive/")
async def upload_archive(file: UploadFile = File(...)):
    """
    Recebe um arquivo .zip ou .rar, extrai,
    processa com processar_pasta() e retorna um ZIP de JSONs.
    """
    filename = Path(file.filename)
    suffix = filename.suffix.lower()

    # 1) Validar extensão
    if suffix not in {".zip", ".rar"}:
        raise HTTPException(400, detail="Arquivo deve ser .zip ou .rar")

    # 2) Ler conteúdo em memória
    content = await file.read()
    buffer_in = io.BytesIO(content)

    # 3) Extrair segundo o tipo de arquivo
    temp_dir = tempfile.TemporaryDirectory()
    try:
        if suffix == ".zip":
            with zipfile.ZipFile(buffer_in) as zf:
                zf.extractall(temp_dir.name)
        else:  # .rar
            with rarfile.RarFile(buffer_in) as rf:
                rf.extractall(path=temp_dir.name)
    except zipfile.BadZipFile:
        raise HTTPException(400, detail="ZIP inválido ou corrompido")
    except rarfile.BadRarFile:
        raise HTTPException(400, detail="RAR inválido ou corrompido")
    except Exception as e:
        raise HTTPException(400, detail=f"Falha ao extrair arquivo: {e}")

    # 4) Processar todos os arquivos da pasta extraída
    resultados = processar_pasta(temp_dir.name)

    # 5) Empacotar resultados em um ZIP em memória
    buffer_out = io.BytesIO()
    with zipfile.ZipFile(buffer_out, "w", zipfile.ZIP_DEFLATED) as zf_out:
        for rel, conteudo in resultados.items():
            arcname = f"{Path(rel).stem}.json"
            zf_out.writestr(arcname, json.dumps(conteudo, ensure_ascii=False))

    buffer_out.seek(0)
    temp_dir.cleanup()  # limpa a pasta temporária

    # 6) Retornar o ZIP final
    return StreamingResponse(
        buffer_out,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="resultados.zip"'}
    )


@app.post("/process-url/")
def process_url(url: str):
    """
    Converte diretamente uma URL e devolve o JSON como resposta.
    """
    try:
        resultado = converter_arquivo(url)
        return JSONResponse(content=resultado)
    except Exception as e:
        logger.error("Erro em /process-url/: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

