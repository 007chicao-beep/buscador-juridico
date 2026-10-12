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
# LEITURA DA PLANILHA EXCEL REAL E CARREGAMENTO DE DADOS (COM CACHE)
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
        linha_cabecalho = 0
        df_teste = pd.read_excel(caminho_excel, nrows=15, header=None)
        for i, row in df_teste.iterrows():
            texto_linha = " ".join([str(val).upper() for val in row.values if pd.notna(val)])
            if any(termo in texto_linha for termo in ['ISBN', 'CODIGO', 'TITULO', 'AUTOR', 'TÍTULO']):
                linha_cabecalho = i
                break
                
        df = pd.read_excel(caminho_excel, header=linha_cabecalho)
        
        # Identificação automática das colunas principais
        col_isbn = next((c for c in df.columns if any(t in str(c).upper() for t in ['ISBN', 'COD'])), df.columns[0] if len(df.columns) > 0 else '')
        col_tit = next((c for c in df.columns if any(t in str(c).upper() for t in ['TIT', 'NOM'])), df.columns[1] if len(df.columns) > 1 else '')
        col_aut = next((c for c in df.columns if 'AUT' in str(c).upper()), df.columns[2] if len(df.columns) > 2 else 'Desconhecido')
        col_pre = next((c for c in df.columns if any(t in str(c).upper() for t in ['PRE', 'VAL'])), 'Sob consulta')
        col_ind = next((c for c in df.columns if any(t in str(c).upper() for t in ['IND', 'SUM', 'SUMA'])), None)

        documents = []
        lista_autores = set()
        
        for _, row in df.iterrows():
            raw_isbn = str(row.get(col_isbn, '')).strip().replace('.0', '')
            isbn_livro = "".join([c for c in raw_isbn if c.isdigit()])
            if not isbn_livro or len(isbn_livro) < 5: 
                continue
                
            titulo_livro = str(row.get(col_tit, 'Sem Título')).strip()
            autor_livro = str(row.get(col_aut, 'Desconhecido')).strip()
            preco_livro = str(row.get(col_pre, 'Sob consulta')).strip()
            
            # FORÇANDO A LEITURA DA COLUNA R (Índice 17 na programação, pois começa no 0)
            txt_res = ""
            if len(row) >= 18:
                txt_res = str(row.iloc[17]).strip()
            
            # Trata casos onde a célula está vazia ou veio como texto 'nan'
            if not txt_res or txt_res.lower() == 'nan' or txt_res == '':
                txt_res = "Resumo analítico disponível sob consulta na secretaria da Editora."
            
            txt_ind = str(row.get(col_ind, 'Índice completo disponível sob consulta.')) if col_ind else "Índice completo disponível sob consulta."
            if not txt_ind or txt_ind.lower() == 'nan':
                txt_ind = "Índice completo disponível sob consulta."
            
            if autor_livro and autor_livro != 'nan' and autor_livro != 'Desconhecido':
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
            return None, [], "❌ Não foi possível extrair nenhum livro válido da planilha Excel."
            
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = Chroma.from_documents(documents, embeddings)
        
        return vectorstore.as_retriever(search_kwargs={"k": 2}), sorted(list(lista_autores)), f"✅ Conexão bem-sucedida! {len(documents)} obras jurídicas carregadas."
        
    except Exception as e:
        return None, [], f"❌ Erro ao ler a planilha Excel: {e}"

# Inicializa o processador inteligente
with st.spinner("Lendo sua planilha real e processando a coluna de resumos (Aguarde)..."):
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
# EXIBIÇÃO INTEGRAL DAS INFORMAÇÕES
# =====================================================================
if resultados:
    st.subheader("📚 Obras Sugeridas:")
    st.write("---")
    
    for idx, livre in enumerate(resultados):
        m = livre.metadata
        col_img, col_dados = st.columns([1, 4]) # Dá mais espaço para o texto respirar
        
        with col_img:
            # Tenta carregar do site corporativo. Se não achar, a caixa se adapta elegantemente
            link_capa_dinamico = f"https://edicionesolejnik.com.br{m['isbn']}.jpg"
            st.image(link_capa_dinamico, width=150)
                
        with col_dados:
            st.markdown(f"### {m['titulo']}")
            st.markdown(f"**Autor:** {m['autor']} | **ISBN:** {m['isbn']} | **Preço:** R$ {m['preco']}")
            
            with st.expander("📖 Ver Sumário / Índice Completo"):
                st.text(m['indice'])
                
            with st.expander("📝 Ver Resumo Técnico / Resenha"):
                st.write(m['resumo']) # Exibirá o texto real contido na coluna R
                
            link_compra = "https://edicionesolejnik.com.br"
            st.markdown(f"<a href='{link_compra}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;'>🛒 Comprar no Site Oficial</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)
