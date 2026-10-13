import os
import zipfile
import gdown
import pandas as pd
import streamlit as st
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# 1. CONFIGURAÇÃO VISUAL DA ABA DO NAVEGADOR
st.set_page_config(page_title="Ediciones Olejnik - Buscador IA", page_icon="⚖️", layout="wide")

# Cabeçalho com a identidade visual da Editora
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚖️ Ediciones Olejnik</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Buscador Bibliográfico Cognitivo para Ciências Jurídicas</h3>", unsafe_allow_html=True)
st.markdown("---")

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
            gdown.download(url_drive, arquivo_capas_zip, quiet=True)
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
        return None, None, "❌ Erro: Planilha Excel não localizada na raiz do seu GitHub. Garanta o upload do arquivo junto ao código!"

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

# Inicialização do sistema
with st.spinner("Inicializando o motor de IA e carregando o catálogo da Ediciones Olejnik..."):
    retriever, df_dados, mensagem_sistema = inicializar_sistema_completo()

if retriever is None:
    st.error(mensagem_sistema)
    st.stop()

# Painel Lateral Informativo
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
            df_filtrado = df_filtrado[
                df_filtrado['Titulo_Fixo'].str.contains(termo_planilha, case=False, na=False) |
                df_filtrado['Materia Derecho'].astype(str).str.contains(termo_planilha, case=False, na=False) if 'Materia Derecho' in df_filtrado.columns else False
            ]
            
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
# 4. EXIBIÇÃO ORGANIZADA E DIAGRAMADA DOS LIVROS
# =====================================================================
if obras_localizadas:
    st.subheader(f"📋 Resultados Encontrados ({len(obras_localizadas)}):")
    st.write("---")
    
    vistos = set()
    obras_unicas = []
    for obra in obras_localizadas:
        if obra['isbn_chave'] not in vistos:
            vistos.add(obra['isbn_chave'])
            obras_unicas.append(obra)
            
    for item in obras_unicas:
        isbn_alvo = item['isbn_chave']
        
        rotas_capas = [
            f"capas/{isbn_alvo}.jpg", f"capas/{isbn_alvo}.png", f"capas/{isbn_alvo}.jpeg",
            f"capas/capas/{isbn_alvo}.jpg", f"capas/capas/{isbn_alvo}.png"
        ]
        caminho_capa_final = next((c for c in rotas_capas if os.path.exists(c)), None)
        
        col_esq, col_dir = st.columns([1, 4])
        
        with col_esq:
            if caminho_capa_final:
                st.image(caminho_capa_final, width=165)
            else:
                # CORRIGIDO: String HTML direta sem o delimitador triplo para evitar erros de sintaxe
                card_azul_html = f"<div style='background-color: #1E3A8A; color: #FFFFFF; padding: 22px 12px; border-radius: 6px; text-align: center; min-height: 225px; display: flex; flex-direction: column; justify-content: space-between; align-items: center; border: 1px solid #1D4ED8; box-shadow: 2px 2px 8px rgba(0,0,0,0.15);'><div style='font-size: 11px; font-weight: bold; line-height: 1.3;'>{item['titulo']}</div><div style='background-color: #172554; padding: 4px 6px; border-radius: 4px; font-size: 10px; font-family: monospace; width: 100%;'>ISBN {item['isbn_original']}</div></div>"
                st.markdown(card_azul_html, unsafe_allow_html=True)
                
        with col_dir:
            st.markdown(f"### **{item['titulo']}**")
            st.markdown(f"👤 **Autor:** {item['autor']}  |  🆔 **ISBN do Livro:** {item['isbn_original']}")
            
            with st.expander("📝 Ver Resumen Técnico / Reseña Completa"):
                st.write(item['resumo'])
                
            with st.expander("📖 Ver Sumário / Índice Detalhado por Capítulos"):
                st.text(item['indice'])
                
            link_venda_oficial = "https://edicionesolejnik.com.br"
            st.markdown(f"<a href='{link_venda_oficial}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:10px 18px; border-radius:4px; cursor:pointer; font-weight:bold;'>🛒 Comprar no Site Oficial</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)
