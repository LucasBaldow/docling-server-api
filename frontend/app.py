import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("📥 EVA Desk API Client")

st.header("1) Upload único")
file = st.file_uploader("PDF, XLSX, PPTX", type=["pdf","xlsx","pptx"])
if file and st.button("Enviar arquivo"):
    fd = {"file": (file.name, file, file.type)}
    r = requests.post(f"{API_URL}/upload-file/", files=fd)
    if r.ok:
        st.download_button("Baixar JSON", r.content, f"{file.name}.json", "application/json")
    else:
        st.error(r.text)

st.markdown("---")
st.header("2) Upload de ZIP")
zipf = st.file_uploader("Arquivo ZIP", type=["zip"], key="zip")
if zipf and st.button("Enviar ZIP"):
    fd = {"zip_file": (zipf.name, zipf, zipf.type)}
    r = requests.post(f"{API_URL}/upload-zip/", files=fd)
    if r.ok:
        st.download_button("Baixar ZIP de JSONs", r.content, "resultados_json.zip", "application/zip")
    else:
        st.error(r.text)

st.markdown("---")
st.header("3) Processar URL")
url = st.text_input("URL")
if url and st.button("Processar URL"):
    r = requests.post(f"{API_URL}/process-url/", json={"url": url})
    if r.ok:
        dispo = r.headers.get("content-disposition","")
        fname = dispo.split("filename=")[-1] if "filename=" in dispo else "output.json"
        st.download_button("Baixar JSON", r.content, fname, "application/json")
    else:
        st.error(r.text)
