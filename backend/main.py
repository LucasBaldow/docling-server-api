import io
import json
import logging
import tempfile
import zipfile, rarfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from backend.converter import converter_arquivo, processar_pasta

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
        background_tasks.add_task(_remove_file, tmp_input.name)         # Limpeza em background :contentReference[oaicite:7]{index=7}
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

    """
    Recebe um ZIP, extrai em memória, aplica processar_pasta() e devolve
    todos os resultados em um ZIP gerado em memória.
    """
    try:
        # 1) Extrair ZIP recebido em dir temporário
        temp_dir = tempfile.TemporaryDirectory()
        with zipfile.ZipFile(zip_file.file, "r") as zf:
            zf.extractall(temp_dir.name)

        # 2) Converter cada arquivo da pasta
        resultados = processar_pasta(temp_dir.name)

        # 3) Criar ZIP de saída em memória
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf_out:  # compresslevel opcional :contentReference[oaicite:8]{index=8}
            for rel, conteudo in resultados.items():
                arcname = f"{Path(rel).stem}.json"
                zf_out.writestr(arcname, json.dumps(conteudo, ensure_ascii=False))

        buffer.seek(0)

        # 4) Retornar StreamingResponse com ZIP
        return StreamingResponse(
            buffer,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="resultados.zip"'}
        )

    except Exception as e:
        logger.error("Erro em /upload-zip/: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

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
            with rarfile.RarFile(buffer_in) as rf:                   # → RarFile :contentReference[oaicite:3]{index=3}
                rf.extractall(path=temp_dir.name)
    except zipfile.BadZipFile:
        raise HTTPException(400, detail="ZIP inválido ou corrompido")
    except rarfile.BadRarFile:
        raise HTTPException(400, detail="RAR inválido ou corrompido")  # erro específico :contentReference[oaicite:4]{index=4}
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
        return JSONResponse(content=resultado)                           # JSON direto sem I/O :contentReference[oaicite:9]{index=9}
    except Exception as e:
        logger.error("Erro em /process-url/: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
