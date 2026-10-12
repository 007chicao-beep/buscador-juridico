import streamlit as st
import os
import zipfile
import urllib.request
import pandas as pd
from docx import Document as DocxReader
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
# CARREGAMENTO INTELIGENTE DIRETO DO GOOGLE DRIVE (COM CACHE)
# =====================================================================
@st.cache_resource
def inicializar_sistema_por_link():
    # ID de compartilhamento do seu link real do Google Drive
    id_drive = "1mM8fdfF8QQEkaHeFhmlyc8mYtd5SK2v6"
    link_download_direto = f"https://google.com{id_drive}"
    
    arquivo_local_zip = "aplicativo_nuvem.zip"
    pasta_extracao = "extracao_total"
    
    # Faz o download automático do ZIP pesado direto para o servidor web da aplicação
    if not os.path.exists(arquivo_local_zip):
        try:
            urllib.request.urlretrieve(link_download_direto, arquivo_local_zip)
        except Exception as e:
            return None, f"❌ Erro ao puxar a base de dados do Google Drive: {e}"
            
    # Descompacta os arquivos na memória do servidor
    if not os.path.exists(pasta_extracao):
        with zipfile.ZipFile(arquivo_local_zip, 'r') as zip_ref:
            zip_ref.extractall(pasta_extracao)
            
    # Procura a planilha Excel de forma dinâmica
    caminho_excel = None
    arquivos_na_pasta = []
    for raiz, _, arquivos in os.walk(pasta_extracao):
        for arq in arquivos:
            caminho_completo = os.path.join(raiz, arq)
            if arq.lower().endswith(('.xlsx', '.xls')) and not arq.startswith('~$'):
                caminho_excel = caminho_completo
            else:
                arquivos_na_pasta.append(caminho_completo)
                
    if not caminho_excel:
        return None, "❌ Erro: Planilha Excel não localizada dentro da estrutura do ZIP."
        
    # Localiza automaticamente a linha do cabeçalho real
    linha_cabecalho = 0
    df_teste = pd.read_excel(caminho_excel, nrows=15, header=None)
    for i, row in df_teste.iterrows():
        texto_linha = " ".join([str(val).upper() for val in row.values if pd.notna(val)])
        if any(termo in texto_linha for termo in ['ISBN', 'CODIGO', 'TITULO', 'AUTOR']):
            linha_cabecalho = i
            break
            
    df = pd.read_excel(caminho_excel, header=linha_cabecalho)
    
    # Indexação instantânea dos nomes dos arquivos Word e Capas por ISBN
    mapa_capas, mapa_indices, mapa_resenhas = {}, {}, {}
    for cam in arquivos_na_pasta:
        nome_arq = os.path.basename(cam)
        isbn = "".join([c for c in nome_arq if c.isdigit()])
        if not isbn: continue
        if "INDICE" in nome_arq.upper(): mapa_indices[isbn] = cam
        elif "RESEÑA" in nome_arq.upper() or "RESENA" in nome_arq.upper(): mapa_resenhas[isbn] = cam
        elif nome_arq.lower().endswith(('.jpg', '.jpeg', '.png')): mapa_capas[isbn] = cam

    def ler_docx(caminho):
        try:
            return "\n".join([p.text for p in DocxReader(caminho).paragraphs if p.text.strip() != ""])
        except: return ""

    # Identificação flexível de colunas
    col_isbn = next((c for c in df.columns if any(t in str(c).upper() for t in ['ISBN', 'COD'])), df.columns[0])
    col_tit = next((c for c in df.columns if any(t in str(c).upper() for t in ['TIT', 'NOM'])), df.columns[1])
    col_aut = next((c for c in df.columns if 'AUT' in str(c).upper()), 'Desconhecido')
    col_pre = next((c for c in df.columns if any(t in str(c).upper() for t in ['PRE', 'VAL'])), 'Sob consulta')

    documents = []
    for _, row in df.iterrows():
        raw_isbn = str(row.get(col_isbn, '')).strip().replace('.0', '')
        isbn_livro = "".join([c for c in raw_isbn if c.isdigit()])
        if not isbn_livro or len(isbn_livro) < 5: continue
        
        c_capa = mapa_capas.get(isbn_livro, None)
        c_ind = mapa_indices.get(isbn_livro, None)
        c_res = mapa_resenhas.get(isbn_livro, None)
        
        txt_ind = ler_docx(c_ind) if c_ind else "Índice completo não cadastrado no sistema."
        txt_res = ler_docx(c_res) if c_res else "Resumo detalhado não cadastrado no sistema."
        
        texto_busca = f"Livro: {row.get(col_tit, '')} | Autor: {row.get(col_aut, '')} | Resumo: {txt_res} | Índice: {txt_ind}"
        
        metadados = {
            "isbn": raw_isbn, "titulo": str(row.get(col_tit, 'Sem Título')), "autor": str(row.get(col_aut, 'Desconhecido')),
            "capa": c_capa, "indice": txt_ind, "resumo": txt_res, "preco": str(row.get(col_pre, 'Sob consulta'))
        }
        documents.append(Document(page_content=texto_busca, metadata=metadados))
        
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(documents, embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 2}), f"✅ {len(documents)} livros jurídicos Olejnik carregados com sucesso!"

# Inicializa o processador inteligente de busca semântica
with st.spinner("Conectando ao Google Drive e inicializando o catálogo da Editora (Aguarde)..."):
    retriever, mensagem = inicializar_sistema_por_link()

if retriever is None:
    st.error(mensagem)
    st.stop()

# =====================================================================
# TELA DE PESQUISA DO ADVOGADO
# =====================================================================
st.sidebar.success(mensagem)
st.sidebar.markdown("### Informações do Sistema")
st.sidebar.info("Buscador oficial conectado com a nuvem da Ediciones Olejnik. Pesquise teses, conceitos jurídicos ou nomes de institutos.")

pergunta = st.text_input("🔍 Descreva o caso jurídico ou tema que você está trabalhando:", 
                        placeholder="Ex: Responsabilidade civil por erro médico ou crimes cibernéticos no direito penal...")

if pergunta:
    with st.spinner("Buscando correlações doutrinárias..."):
        resultados = retriever.invoke(pergunta)
        
    st.subheader("📚 Obras Sugeridas:")
    st.write("---")
    
    for idx, livro in enumerate(resultados):
        m = livro.metadata
        col_img, col_dados = st.columns([1, 4])
        
        with col_img:
            if m['capa']:
                st.image(m['capa'], width=150)
            else:
                st.image("https://placeholder.com", width=150)
                
        with col_dados:
            st.markdown(f"### {m['titulo']}")
            st.markdown(f"**Autor:** {m['autor']} | **ISBN:** {m['isbn']} | **Preço:** R$ {m['preco']}")
            
            # Abas interativas ocultas por padrão (só se abrem quando clicadas)
            with st.expander("📖 Ver Sumário / Índice Completo"):
                st.write(m['indice'])
                
            with st.expander("📝 Ver Resumo Técnico / Resenha"):
                st.write(m['resumo'])
                
            link_compra = "https://edicionesolejnik.com.br"
            st.markdown(f"<a href='{link_compra}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;'>🛒 Comprar no Site Oficial</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)
