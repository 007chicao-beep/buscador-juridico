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
# LEITURA DA PLANILHA EXCEL REAL COM BUSCA AUTOMÁTICA DE CABEÇALHO
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
        # Analisa onde está a linha de cabeçalho real buscando termos-chave
        linha_cabecalho = 0
        df_teste = pd.read_excel(caminho_excel, nrows=15, header=None)
        for i, row in df_teste.iterrows():
            texto_linha = " ".join([str(val).upper() for val in row.values if pd.notna(val)])
            if any(termo in texto_linha for termo in ['ISBN', 'CODIGO', 'TITULO', 'AUTOR', 'TÍTULO']):
                linha_cabecalho = i
                break
                
        df = pd.read_excel(caminho_excel, header=linha_cabecalho)
        
        # Mapeamento inteligente que aceita variações em Português e Espanhol
        col_isbn = next((c for c in df.columns if any(t in str(c).upper() for t in ['ISBN', 'EAN', 'COD'])), df.columns[0])
        col_tit = next((c for c in df.columns if any(t in str(c).upper() for t in ['TIT', 'NOM', 'OBRA']) and 'ISBN' not in str(c).upper()), df.columns[1])
        col_aut = next((c for c in df.columns if any(t in str(c).upper() for t in ['AUT', 'ESCRI'])), df.columns[2])
        
        # Procura de forma avançada as colunas de Preço, Resumo e Índice
        col_pre = next((c for c in df.columns if any(t in str(c).upper() for t in ['PRE', 'VAL', 'R$', 'PRIC', 'COST'])), None)
        col_res = next((c for c in df.columns if any(t in str(c).upper() for t in ['RES', 'SINO', 'DESCR', 'RESE', 'COLUNA R', 'R'])), None)
        col_ind = next((c for c in df.columns if any(t in str(c).upper() for t in ['IND', 'SUM', 'SUMA', 'PAUTA', 'ÍNDI'])), None)

        documents = []
        lista_autores = set()
        
        for idx_row, row in df.iterrows():
            # Extrai e limpa o ISBN
            raw_isbn = str(row.get(col_isbn, '')).strip().split('.')
            isbn_livro = "".join([c for c in raw_isbn if c.isdigit()])
            if not isbn_livro or len(isbn_livro) < 5: 
                continue
                
            titulo_livro = str(row.get(col_tit, 'Sem Título')).strip()
            autor_livro = str(row.get(col_aut, 'Desconhecido')).strip()
            
            # Se por algum motivo o título veio duplicando o ISBN, ignora a linha corrompida
            if titulo_livro == isbn_livro or titulo_livro.lower() in ['nan', '']:
                continue

            # Captura e formatação do Preço Real em Reais
            preco_raw = str(row.get(col_pre, '')).strip() if col_pre else ""
            if not preco_raw or preco_raw.lower() in ['nan', '0', '0.0', '']:
                preco_livro = "Sob consulta"
            else:
                preco_limpo = preco_raw.upper().replace('R$', '').replace('$', '').strip()
                preco_livro = f"R$ {preco_limpo}"
            
            # Puxa o resumo (Tenta por nome de coluna ou pega pela posição da 18ª coluna/Letra R)
            txt_res = ""
            if col_res:
                txt_res = str(row.get(col_res, '')).strip()
            elif len(row) >= 18:
                txt_res = str(row.iloc[17]).strip()
                
            if not txt_res or txt_res.lower() in ['nan', '']:
                txt_res = "Resumo analítico disponível sob consulta na secretaria da Editora."
            
            # Puxa o índice (Tenta por nome de coluna ou pega pela posição da 19ª coluna/Letra S)
            txt_ind = ""
            if col_ind:
                txt_ind = str(row.get(col_ind, '')).strip()
            elif len(row) >= 19:
                txt_ind = str(row.iloc[18]).strip()
                
            if not txt_ind or txt_ind.lower() in ['nan', '']:
                txt_ind = "Índice detalhado disponível sob consulta na secretaria da Editora."
            
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
            return None, [], "❌ Erro ao cruzar os dados estruturados da planilha."
            
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = Chroma.from_documents(documents, embeddings)
        
        return vectorstore.as_retriever(search_kwargs={"k": 2}), sorted(list(lista_autores)), f"✅ Conexão estável! {len(documents)} obras jurídicas Olejnik operacionais."
        
    except Exception as e:
        return None, [], f"❌ Erro ao ler a estrutura do arquivo Excel: {e}"

# Inicializa o processador inteligente
with st.spinner("Sincronizando de forma inteligente o catálogo, preços e resumos (Aguarde)..."):
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
        col_img, col_dados = st.columns() # Divide a tela perfeitamente de forma responsiva
        
        with col_img:
            # Vinculação direta com o servidor de imagens oficial da Ediciones Olejnik usando o ISBN
            link_capa_dinamico = f"https://edicionesolejnik.com.br{m['isbn']}.jpg"
            st.image(link_capa_dinamico, width=140)
                
        with col_dados:
            st.markdown(f"### {m['titulo']}")
            st.markdown(f"**Autor:** {m['autor']} | **ISBN do Livro:** {m['isbn']} | **Preço:** {m['preco']}")
            
            with st.expander("📖 Ver Sumário / Índice Completo"):
                st.write(m['indice'])
                
            with st.expander("📝 Ver Resumo Técnico / Resenha"):
                st.write(m['resumo'])
                
            link_compra = "https://edicionesolejnik.com.br"
            st.markdown(f"<a href='{link_compra}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;'>🛒 Comprar no Site Oficial</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)
