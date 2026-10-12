import streamlit as st
import pandas as pd
import os
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Configuração visual e responsiva da aba do navegador
st.set_page_config(page_title="Ediciones Olejnik - Buscador IA", page_icon="⚖️", layout="wide")

# Elementos de Cabeçalho com a identidade da Editora
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚖️ Ediciones Olejnik</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Buscador Bibliográfico Cognitivo para Ciências Jurídicas</h3>", unsafe_allow_html=True)
st.markdown("---")

# =====================================================================
# LEITURA DA PLANILHA EXCEL REAL COM MAPEAMENTO EXATO DE COLUNAS
# =====================================================================
@st.cache_resource
def inicializar_sistema_real():
    caminho_excel = None
    for arquivo in os.listdir('.'):
        if arquivo.lower().endswith(('.xlsx', '.xls')) and not arquivo.startswith('~$'):
            caminho_excel = arquivo
            break
            
    if not caminho_excel:
        return None, [], "❌ Erro: Nenhuma planilha Excel (.xlsx) foi encontrada na pasta do projeto."
        
    try:
        # Abre o Excel na linha 2 (header=1), que é onde estão os títulos oficiais capturados no Colab
        df = pd.read_excel(caminho_excel, header=1)
        
        # FIXANDO AS COLUNAS REAIS DA EDICIONES OLEJNIK
        col_isbn = 'ISBN-EAN'
        col_tit = 'Título - sub.título'
        col_aut = 'Autor'
        
        # Busca flexível para Preço e Índice nas colunas restantes
        col_pre = next((c for c in df.columns if any(t in str(c).upper() for t in ['PRE', 'VAL', 'R$', 'PRIC', 'PRECIO'])), None)
        col_ind = next((c for c in df.columns if any(t in str(c).upper() for t in ['IND', 'SUM', 'SUMA', 'PAUTA', 'INDICE', 'ÍNDICE'])), None)

        documents = []
        lista_autores = set()
        
        for _, row in df.iterrows():
            # Captura e limpa o ISBN-EAN
            raw_isbn = str(row.get(col_isbn, '')).strip().split('.')
            isbn_livro = "".join([c for c in raw_isbn if c.isdigit()])
            if not isbn_livro or len(isbn_livro) < 5: 
                continue
                
            # Captura o Título e o Autor corretos por extenso
            titulo_livro = str(row.get(col_tit, 'Sem Título')).strip()
            autor_livro = str(row.get(col_aut, 'Desconhecido')).strip()
            
            # Se por erro de linha o título vier como número, pula para evitar falha visual
            if titulo_livro.replace('.','',1).isdigit():
                continue

            # Captura o Preço real da planilha
            preco_raw = str(row.get(col_pre, '')) .strip() if col_pre else ""
            if not preco_raw or preco_raw.lower() in ['nan', '0', '0.0', '']:
                preco_livro = "Sob consulta"
            else:
                preco_limpo = preco_raw.upper().replace('R$', '').replace('$', '').strip()
                preco_livro = f"R$ {preco_limpo}"
            
            # Puxa o resumo direto da coluna R (posição 18 da planilha = índice 17)
            txt_res = ""
            if len(row) >= 18:
                txt_res = str(row.iloc[17]).strip()
            
            if not txt_res or txt_res.lower() in ['nan', '']:
                txt_res = "Resumo detalhado disponível sob consulta na secretaria da Editora."
            
            # Puxa o Índice/Sumário da coluna correspondente
            txt_ind = str(row.get(col_ind, '')) if col_ind else ""
            if not txt_ind or txt_ind.lower() in ['nan', '']:
                txt_ind = "Índice completo disponível sob consulta na secretaria da Editora."
            
            if autor_livro and autor_livro.lower() != 'nan' and autor_livro != 'Desconhecido':
                lista_autores.add(autor_livro)
                
            texto_busca = f"Livro: {titulo_livro} | Autor: {autor_livro} | Resumo: {txt_res} | Índice: {txt_ind}"
            
            metadados = {
                "isbn": isbn_livro, 
                "titulo": titulo_livro, 
                "autor": autor_livro,
                "indice": txt_ind, 
                "resumo": txt_res, 
                "preco": preco_livro
            }
            documents.append(Document(page_content=texto_busca, metadata=metadados))
            
        if len(documents) == 0:
            return None, [], "❌ Erro ao cruzar as colunas. Verifique os cabeçalhos da planilha."
            
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = Chroma.from_documents(documents, embeddings)
        
        return vectorstore.as_retriever(search_kwargs={"k": 2}), sorted(list(lista_autores)), f"✅ Conexão bem-sucedida! {len(documents)} obras jurídicas carregadas."
        
    except Exception as e:
        return None, [], f"❌ Erro ao processar a estrutura do Excel: {e}"

# Inicializa o processador inteligente
with st.spinner("Alinhando Títulos, ISBNs e Índices da planilha real (Aguarde)..."):
    retriever, autores_disponiveis, mensagem = inicializar_sistema_real()

if retriever is None:
    st.error(mensagem)
    st.stop()

# =====================================================================
# TELA DE PESQUISA DO ADVOGADO
# =====================================================================
st.sidebar.success(mensagem)
st.sidebar.markdown("### Menu de Busca")

tipo_busca = st.sidebar.radio("Selecione o método de consulta:", ["Pesquisa por Tema / Caso (IA)", "Filtrar por Autor"])

resultados = []

if tipo_busca == "Pesquisa por Tema / Caso (IA)":
    pergunta = st.text_input("🔍 Descreva o caso jurídico ou tema que você está trabalhando:", 
                            placeholder="Ex: Responsabilidade civil por erro médico ou direito penal...")
    if pergunta:
        with st.spinner("Buscando correlações doutrinárias..."):
            resultados = retriever.invoke(pergunta)
else:
    autor_selecionado = st.selectbox("📚 Selecione o Autor que deseja consultar:", [""] + autores_disponiveis)
    if autor_selecionado:
        with st.spinner("Puxando catálogo do autor..."):
            resultados = retriever.invoke(f"Autor: {autor_selecionado}")

# =====================================================================
# EXIBIÇÃO INTEGRAL E CASADA DAS INFORMAÇÕES
# =====================================================================
if resultados:
    st.subheader("📚 Obras Sugeridas:")
    st.write("---")
    
    for idx, livre in enumerate(resultados):
        m = livre.metadata
        col_img, col_dados = st.columns([1, 4]) # Reserva espaço correto na proporção lateral
        
        with col_img:
            # Tenta carregar a imagem da capa do site oficial da Ediciones Olejnik usando o ISBN
            link_capa_dinamico = f"https://edicionesolejnik.com.br{m['isbn']}.jpg"
            st.image(link_capa_dinamico, width=140)
                
        with col_dados:
            # EXIBE O NOME DA OBRA (TÍTULO) EM DESTAQUE E O ISBN LOGO ABAIXO EM CONJUNTO
            st.markdown(f"### {m['titulo']}")
            st.markdown(f"**Autor:** {m['autor']} | **ISBN do Livro:** {m['isbn']} | **Preço:** {m['preco']}")
            
            with st.expander("📖 Ver Sumário / Índice Completo"):
                st.write(m['indice']) # Exibe o índice cadastrado na planilha
                
            with st.expander("📝 Ver Resumo Técnico / Resenha"):
                st.write(m['resumo']) # Exibe o resumo real e longo contido na coluna R
                
            link_compra = "https://edicionesolejnik.com.br"
            st.markdown(f"<a href='{link_compra}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;'>🛒 Comprar no Site Oficial</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)", unsafe_allow_html=True)      
