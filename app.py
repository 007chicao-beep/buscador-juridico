import os
import zipfile
import gdown
import pandas as pd
import streamlit as st
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# =====================================================================
# 1. CONFIGURAÇÃO VISUAL E BANNER CORPORATIVO (IMPECÁVEL EM 4K)
# =====================================================================
st.set_page_config(page_title="Ediciones Olejnik - Buscador IA", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }
        div[data-testid="stExpander"] {
            border: 1px solid #E5E7EB !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
            border-radius: 6px !important;
            margin-bottom: 10px !important;
        }
        .banner-corporativo {
            width: 100%;
            height: 140px;
            background: linear-gradient(rgba(26, 26, 26, 0.75), rgba(26, 26, 26, 0.75)), 
                        url('https://unsplash.com');
            background-size: cover;
            background-position: center;
            border-radius: 8px;
            display: flex;
            align-items: center;
            padding-left: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 25px;
            border: 1px solid #333;
        }
        .caixa-logo {
            width: 120px;
            height: 95px;
            background: linear-gradient(140deg, #ffffff 50%, #1a1a1a 50%);
            border: 1px solid #1a1a1a;
            position: relative;
            font-family: 'Century Gothic', 'Segoe UI', Arial, sans-serif;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            flex-shrink: 0;
        }
        .texto-ed {
            position: absolute;
            top: 25px;
            left: 10px;
            color: #1a1a1a;
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 0.5px;
        }
        .texto-ol {
            position: absolute;
            bottom: 12px;
            right: 10px;
            color: #ffffff;
            font-size: 19px;
            font-style: italic;
            letter-spacing: 0.5px;
        }
        .bloco-titulos {
            margin-left: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .titulo-principal {
            color: #ffffff;
            margin: 0;
            font-size: 26px;
            font-weight: 600;
            letter-spacing: 1.5px;
        }
        .sub-principal {
            color: #9CA3AF;
            margin: 4px 0 0 0;
            font-size: 14px;
            letter-spacing: 0.5px;
        }
    </style>
    <div class='banner-corporativo'>
        <div class='caixa-logo'>
            <span class='texto-ed'>Ediciones</span>
            <span class='texto-ol'>Olejnik</span>
        </div>
        <div class='bloco-titulos'>
            <h1 class='titulo-principal'>Ediciones Olejnik</h1>
            <p class='sub-principal'>Buscador Bibliográfico Cognitivo para Ciencias Jurídicas</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# =====================================================================
# 2. CARREGAMENTO DAS IMAGENS E PROCESSAMENTO DE DADOS (COM CACHE)
# =====================================================================
@st.cache_resource
def inicializar_sistema_completo():
    ID_CAPAS_DRIVE = "1CnfjblNWOhWWFNuq4gCs6XGKwMWW9bex"
    arquivo_capas_zip = "capas.zip"
    pasta_destino_capas = "capas"
    
    if not os.path.exists(pasta_destino_capas):
        try:
            url_drive = f'https://google.com{ID_CAPAS_DRIVE}'
            gdown.download(url_drive, arquivo_capas_zip, quiet=True, fuzzy=True)
            
            if os.path.exists(arquivo_capas_zip):
                with zipfile.ZipFile(arquivo_capas_zip, 'r') as zip_ref:
                    zip_ref.extractall(pasta_destino_capas)
                os.remove(arquivo_capas_zip)
        except Exception as e:
            pass

    caminho_excel = None
    for arquivo in os.listdir('.'):
        if arquivo.lower().endswith(('.xlsx', '.xls', '.csv')) and not arquivo.startswith('~$'):
            caminho_excel = arquivo
            break
            
    if not caminho_excel:
        return None, None, "❌ Erro: Planilha Excel não localizada na raiz do seu GitHub."

    df_base = pd.read_excel(caminho_excel, header=0)
    df_base.columns = [str(c).strip() for c in df_base.columns]

    documents = []
    lista_obras_atualizada = []

    for idx, row in df_base.iterrows():
        titulo_obra = str(row.get('Titulo - Sub.titulo', row.get('Título', 'Sem Título'))).strip()
        autor_obra = str(row.get('Autor', 'Autor Desconhecido')).strip()
        
        raw_isbn = str(row.get('ISBN-EAN', '')).strip().replace('.0', '')
        isbn_limpo = "".join([c for c in raw_isbn if c.isdigit()])
        if not isbn_limpo: 
            continue
            
        txt_resenha = str(row.get('Reseña', 'Reseña técnica disponible bajo consulta en la Editorial.')).strip()
        txt_indice = str(row.get('Indice_Completo', 'Índice detalhado disponible bajo consulta.')).strip()
        
        if txt_resenha.lower() == 'nan' or not txt_resenha:
            txt_resenha = "Reseña técnica disponible bajo consulta en la Editorial."
        if txt_indice.lower() == 'nan' or not txt_indice:
            txt_indice = "Índice detalhado disponible bajo consulta en la Editorial."

        obra_dict = row.to_dict()
        obra_dict['ISBN_Chave'] = isbn_limpo
        obra_dict['Titulo_Fixo'] = titulo_obra
        obra_dict['Autor_Fixo'] = autor_obra
        obra_dict['Reseña_Fixa'] = txt_resenha
        obra_dict['Indice_Fixo'] = txt_indice
        lista_obras_atualizada.append(obra_dict)
        
        materia_direito = str(row.get('Materia Derecho', ''))
        sub_materia = str(row.get('Sub. Materia', ''))
        
        texto_indexado_ia = f"Livro: {titulo_obra} | Autor: {autor_obra} | Matéria: {materia_direito} {sub_materia} | Resumo: {txt_resenha} | Índice: {txt_indice}"
        
        metadados_ia = {
            "isbn_chave": isbn_limpo, "isbn_original": raw_isbn, "titulo": titulo_obra, 
            "autor": autor_obra, "resumo": txt_resenha, "indice": txt_indice
        }
        documents.append(Document(page_content=texto_indexado_ia, metadata=metadados_ia))
        
    df_processado = pd.DataFrame(lista_obras_atualizada)
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(documents, embeddings)
    retriever_ia = vectorstore.as_retriever(search_kwargs={"k": 4})
    
    return retriever_ia, df_processado, f"✅ {len(df_processado)} livros do catálogo Olejnik integrados e operacionais!"

with st.spinner("Inicializando o motor de IA e carregando o catálogo da Ediciones Olejnik..."):
    retriever, df_dados, mensagem_sistema = inicializar_sistema_completo()

if retriever is None:
    st.error(mensagem_sistema)
    st.stop()

st.sidebar.markdown("<h2 style='color: #1A1A1A; font-size: 20px;'>📊 Status do Sistema</h2>", unsafe_allow_html=True)
st.sidebar.success(mensagem_sistema)
st.sidebar.markdown("### 🛠️ Guia de Trabalho")
st.sidebar.info("A **Pesquisa Cognitiva** faz uma varredura inteligente por IA em toda a doutrina. Os **Filtros** localizam termos e autores exatos.")

# =====================================================================
# 3. INTERFACE DE MÚLTIPLAS ABAS DE BUSCA
# =====================================================================
aba_ia, aba_tradicional = st.tabs(["🧠 Pesquisa Cognitiva por IA (Casos e Temas)", "🔍 Filtros Tradicionais (Autor / Palavra-Chave)"])

obras_localizadas = []

with aba_ia:
    pergunta_advogado = st.text_input("Descreva o caso jurídico, tese ou área que você deseja consultar (PT / ES):", 
                                     placeholder="Ex: Carga de la prueba en el processo... ", key="busca_ia")
    if pergunta_advogado:
        with st.spinner("IA executando varredura pelos Índices e Resenhas..."):
            documentos_ia = retriever.invoke(pergunta_advogado)
            for doc in documentos_ia:
                obras_localizadas.append(doc.metadata)

with aba_tradicional:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        autores_planilha = sorted(df_dados['Autor_Fixo'].dropna().unique())
        autor_sel = st.selectbox("Selecione um Autor específico do catálogo:", [""] + autores_planilha)
    with col_f2:
        termo_planilha = st.text_input("Buscar por termo exato no Título ou Matéria:")
        
    if autor_sel or termo_planilha:
        df_filtrado = df_dados.copy()
        if autor_sel:
            df_filtrado = df_filtrado[df_filtrado['Autor_Fixo'] == autor_sel]
        if termo_planilha:
            condicao_titulo = df_filtrado['Titulo_Fixo'].str.contains(termo_planilha, case=False, na=False)
            if 'Materia Derecho' in df_filtrado.columns:
                condicao_materia = df_filtrado['Materia Derecho'].astype(str).str.contains(termo_planilha, case=False, na=False)
                df_filtrado = df_filtrado[condicao_titulo | condicao_materia]
            else:
                df_filtrado = df_filtrado[condicao_titulo]
            
        for _, r in df_filtrado.iterrows():
            obras_localizadas.append({
                "isbn_original": r.get('ISBN-EAN', r['ISBN_Chave']),
                "isbn_chave": r['ISBN_Chave'],
                "titulo": r['Titulo_Fixo'],
                "autor": r['Autor_Fixo'],
                "resumo": r['Reseña_Fixa'],
                "indice": r['Indice_Fixo']
            })

# =====================================================================
4. EXIBIÇÃO DIAGRAMADA EM FORMATO APP / VITRINE CORPORATIVA PREMIUM
# =====================================================================
if obras_localizadas:
st.write("")
st.markdown(f"### 📋 Resultados Encontrados ({len(obras_localizadas)})")
st.write("---")
vistos = set()
obras_unicas = []
for obra in obras_localizadas:
if obra['isbn_chave'] not in vistos:
vistos.add(obra['isbn_chave'])
obras_unicas.append(obra)
for item in obras_unicas:
isbn_alvo = item['isbn_chave']
caminho_foto_png = os.path.join("capas", f"{isbn_alvo}.png")
caminho_foto_jpg = os.path.join("capas", f"{isbn_alvo}.jpg")
imagem_final = "unsplash.com"
if os.path.exists(caminho_foto_png):
imagem_final = caminho_foto_png
elif os.path.exists(caminho_foto_jpg):
imagem_final = caminho_foto_jpg
col_capa, col_conteudo = st.columns([1, 4])
with col_capa:
st.image(imagem_final, use_container_width=True)
st.markdown(f"ISBN: {item['isbn_original']}", unsafe_allow_html=True)
with col_conteudo:
st.markdown(f"{item['titulo']}", unsafe_allow_html=True)
st.markdown(f"👤 Autor: {item['autor']}", unsafe_allow_html=True)
with st.expander("📝 Ver Resumen Técnico / Reseña"):
st.markdown(f"{item['resumo']}", unsafe_allow_html=True)
with st.expander("📖 Ver Sumário / Índice Detalhado"):
st.markdown(f"{item['indice']}", unsafe_allow_html=True)
st.markdown("", unsafe_allow_html=True)
else:
if pergunta_advogado or autor_sel or termo_planilha:
st.warning("⚠️ Nenhum livro correspondente foi localizado no catálogo da Ediciones Olejnik. Tente refinar sua busca por IA ou filtros.")
