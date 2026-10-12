import os
import zipfile
import gdown
import pandas as pd
from docx import Document as DocxReader
import streamlit as st
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Configuração visual da aba do navegador
st.set_page_config(page_title="Ediciones Olejnik - Buscador IA", page_icon="⚖️", layout="wide")

# Cabeçalho com a identidade da Editora
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚖️ Ediciones Olejnik</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Buscador Bibliográfico Cognitivo para Ciências Jurídicas</h3>", unsafe_allow_html=True)
st.markdown("---")

# =====================================================================
# CARREGAMENTO INTELIGENTE INTEGRADO DO GOOGLE DRIVE (COM CACHE)
# =====================================================================
@st.cache_resource
def inicializar_sistema_completo():
    # IDs de compartilhamento reais do Google Drive
    ID_TEXTOS_DRIVE = "1mM8fdfF8QQEkaHeFhmlyc8mYtd5SK2v6"
    ID_CAPAS_DRIVE = "1CnfjblNWOhWWFNuq4gCs6XGKwMWW9bex"
    
    arquivo_textos_zip = "aplicativo_nuvem.zip"
    arquivo_capas_zip = "capas.zip"
    
    pasta_extracao_textos = "extracao_total"
    pasta_destino_capas = "capas"
    
    # 1. DOWNLOAD E EXTRAÇÃO DOS TEXTOS / PLANILHA
    if not os.path.exists(pasta_extracao_textos):
        try:
            url_textos = f'https://google.com{ID_TEXTOS_DRIVE}'
            gdown.download(url_textos, arquivo_textos_zip, quiet=True)
            if os.path.exists(arquivo_textos_zip):
                with zipfile.ZipFile(arquivo_textos_zip, 'r') as zip_ref:
                    zip_ref.extractall(pasta_extracao_textos)
                os.remove(arquivo_textos_zip)
        except Exception as e:
            return None, None, f"❌ Erro ao baixar base de textos: {e}"

    # 2. DOWNLOAD E EXTRAÇÃO DAS 1.890 CAPAS
    if not os.path.exists(pasta_destino_capas):
        try:
            url_capas = f'https://google.com{ID_CAPAS_DRIVE}'
            gdown.download(url_capas, arquivo_capas_zip, quiet=True)
            if os.path.exists(arquivo_capas_zip):
                with zipfile.ZipFile(arquivo_capas_zip, 'r') as zip_ref:
                    zip_ref.extractall(pasta_destino_capas)
                os.remove(arquivo_capas_zip)
        except Exception as e:
            st.warning(f"⚠️ Aviso: Não foi possível carregar as imagens de capa ({e})")

    # Mapeia todos os arquivos descompactados na memória do servidor
    arquivos_na_pasta = []
    for raiz, _, arquivos in os.walk(pasta_extracao_textos):
        for arq in arquivos:
            arquivos_na_pasta.append(os.path.join(raiz, arq))
            
    caminho_excel = next((c for c in arquivos_na_pasta if c.lower().endswith(('.xlsx', '.xls')) and not os.path.basename(c).startswith('~$')), None)
    
    if not caminho_excel:
        return None, None, "❌ Erro: Planilha Excel não localizada dentro da estrutura do ZIP de textos."
        
    # Localiza automaticamente a linha do cabeçalho real da tabela
    linha_cabecalho = 0
    df_teste = pd.read_excel(caminho_excel, nrows=15, header=None)
    for i, row in df_teste.iterrows():
        texto_linha = " ".join([str(val).upper() for val in row.values if pd.notna(val)])
        if any(termo in texto_linha for termo in ['ISBN', 'CODIGO', 'TITULO', 'AUTOR']):
            linha_cabecalho = i
            break
            
    df = pd.read_excel(caminho_excel, header=linha_cabecalho)
    
    # Indexação de arquivos Word (.docx) por ISBN
    mapa_indices, mapa_resenhas = {}, {}
    for cam in arquivos_na_pasta:
        nome_arq = os.path.basename(cam).upper()
        isbn = "".join([c for c in nome_arq if c.isdigit()])
        if not isbn or len(isbn) < 5: continue
        if "INDICE" in nome_arq or "SUMARIO" in nome_arq: 
            mapa_indices[isbn] = cam
        elif "RESEÑA" in nome_arq or "RESENA" in nome_arq or "RESUMO" in nome_arq: 
            mapa_resenhas[isbn] = cam

    def ler_docx(caminho):
        try:
            return "\n".join([p.text for p in DocxReader(caminho).paragraphs if p.text.strip() != ""])
        except: return ""

    # Identificação flexível de colunas do Excel
    col_isbn = next((c for c in df.columns if any(t in str(c).upper() for t in ['ISBN', 'COD'])), df.columns[0])
    col_tit = next((c for c in df.columns if any(t in str(c).upper() for t in ['TIT', 'NOM'])), df.columns[1])
    col_aut = next((c for c in df.columns if 'AUT' in str(c).upper()), 'Desconhecido')
    col_pre = next((c for c in df.columns if any(t in str(c).upper() for t in ['PRE', 'VAL'])), 'Sob consulta')

    documents = []
    lista_df_atualizada = []

    # Loop para construir a planilha rica com textos associados dos arquivos Word
    for idx, row in df.iterrows():
        raw_isbn = str(row.get(col_isbn, '')).strip().replace('.0', '')
        isbn_livro = "".join([c for c in raw_isbn if c.isdigit()])
        if not isbn_livro: continue
        
        c_ind = mapa_indices.get(isbn_livro, None)
        c_res = mapa_resenhas.get(isbn_livro, None)
        
        # Faz a leitura do Word ou herda o texto existente na tabela
        txt_ind = ler_docx(c_ind) if c_ind else "Índice detalhado disponível sob consulta na secretaria da Editorial."
        txt_res = ler_docx(c_res) if c_res else str(row.get('Reseña', 'Reseña técnica disponible bajo consulta na Editorial.'))
        
        if not txt_res or txt_res.lower() == 'nan' or txt_res.strip() == "":
            txt_res = "Reseña técnica disponible bajo consulta en la Editorial."

        # Atualiza a linha da tabela na memória para busca manual
        row_dict = row.to_dict()
        row_dict['ISBN_Limpo'] = isbn_livro
        row_dict['Reseña_Completa'] = txt_res
        row_dict['Indice_Completo'] = txt_ind
        row_dict['Titulo_Normalizado'] = str(row.get(col_tit, 'Sem Título'))
        row_dict['Autor_Normalizado'] = str(row.get(col_aut, 'Desconhecido'))
        row_dict['Preco_Normalizado'] = str(row.get(col_pre, 'Sob consulta'))
        lista_df_atualizada.append(row_dict)
        
        # Documento para a IA Semântica
        texto_busca = f"Livro: {row.get(col_tit, '')} | Autor: {row.get(col_aut, '')} | Resumo: {txt_res} | Índice: {txt_ind}"
        metadados = {
            "isbn": raw_isbn, "isbn_limpo": isbn_livro, "titulo": str(row.get(col_tit, 'Sem Título')), 
            "autor": str(row.get(col_aut, 'Desconhecido')), "indice": txt_ind, "resumo": txt_res, "preco": str(row.get(col_pre, 'Sob consulta'))
        }
        documents.append(Document(page_content=texto_busca, metadata=metadados))
        
    df_processado = pd.DataFrame(lista_df_atualizada)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(documents, embeddings)
    retriever_ia = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    return retriever_ia, df_processado, f"✅ {len(df_processado)} obras processadas e associadas com sucesso!"

# Inicialização segura
with st.spinner("Conectando aos servidores seguros e integrando banco de dados... (Aguarde)"):
    retriever, df_dados, mensagem = inicializar_sistema_completo()

if retriever is None:
    st.error(mensagem)
    st.stop()

# Painel Lateral Informativo
st.sidebar.success(mensagem)
st.sidebar.markdown("### Configurações do Mecanismo")
st.sidebar.info("As buscas por IA analisam o contexto jurídico integral das teses. Os filtros tradicionais localizam termos exatos na planilha.")

# =====================================================================
# SISTEMA DE ABAS: RETORNANDO AS OPÇÕES QUE VOCÊ TINHA
# =====================================================================
aba_ia, aba_tradicional = st.tabs(["🧠 Pesquisa Cognitiva por IA (Doutrina)", "🔍 Consulta por Filtros (Autor / Tema)"])

resultados_exibicao = [] # Lista unificada de metadados para renderizar na tela

with aba_ia:
    pergunta = st.text_input("Descreva o caso jurídico ou conceito doutrinário que está trabalhando:", 
                            placeholder="Ex: Responsabilidade civil por erro médico ou crimes cibernéticos...", key="busca_ia")
    if pergunta:
        with st.spinner("Analisando correlações doutrinárias de IA..."):
            docs_ia = retriever.invoke(pergunta)
            for doc in docs_ia:
                resultados_exibicao.append(doc.metadata)

with aba_tradicional:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        autores_disponiveis = sorted(df_dados['Autor_Normalizado'].dropna().unique())
        autor_sel = st.selectbox("Filtrar por Autor específico:", [""] + autores_disponiveis)
    with col_f2:
        palavra_chave = st.text_input("Filtrar por Título, Matéria ou Palavra-Chave:")
        
    if autor_sel or palavra_chave:
        df_filtrado = df_dados.copy()
        if autor_sel:
            df_filtrado = df_filtrado[df_filtrado['Autor_Normalizado'] == autor_sel]
        if palavra_chave:
            df_filtrado = df_filtrado[
                df_filtrado['Titulo_Normalizado'].str.contains(palavra_chave, case=False, na=False) |
                df_filtrado['Reseña_Completa'].str.contains(palavra_chave, case=False, na=False)
            ]
            
        for _, r in df_filtrado.iterrows():
            resultados_exibicao.append({
                "isbn": r['ISBN-EAN'] if 'ISBN-EAN' in r else r['ISBN_Limpo'],
                "isbn_limpo": r['ISBN_Limpo'],
                "titulo": r['Titulo_Normalizado'],
                "autor": r['Autor_Normalizado'],
                "resumo": r['Reseña_Completa'],
                "indice": r['Indice_Completo'],
                "preco": r['Preco_Normalizado']
            })

# =====================================================================
# MÓDULO RENDERIZADOR DE LIVROS E CAPAS LOCALIZADAS
