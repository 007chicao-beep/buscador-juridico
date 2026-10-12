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
# LEITURA DA PLANILHA EXCEL REAL COM TRATAMENTO DE COLUNAS JURÍDICAS
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
        # Abre o Excel pulando possíveis linhas vazias do topo para ler os cabeçalhos reais
        df = pd.read_excel(caminho_excel, header=1)
        
        # Mapeamento manual com base nos dados reais validados na sua planilha
        col_isbn = 'ISBN-EAN' if 'ISBN-EAN' in df.columns else next((c for c in df.columns if 'ISBN' in str(c).upper()), df.columns[0])
        col_tit = 'Título - sub.título' if 'Título - sub.título' in df.columns else next((c for c in df.columns if 'TIT' in str(c).upper() or 'TÍT' in str(c).upper()), df.columns[1])
        col_aut = 'Autor' if 'Autor' in df.columns else next((c for c in df.columns if 'AUT' in str(c).upper()), df.columns[2])
        
        # Procura colunas de preço e índice/sumário pelos termos mais comuns
        col_pre = next((c for c in df.columns if any(t in str(c).upper() for t in ['PRE', 'VAL', 'R$', 'PRECIO', 'PRICE'])), None)
        col_ind = next((c for c in df.columns if any(t in str(c).upper() for t in ['IND', 'SUM', 'SUMA', 'PAUTA', 'INDICE', 'ÍNDICE'])), None)

        documents = []
        lista_autores = set()
        
        for _, row in df.iterrows():
            # Extrai e limpa o código ISBN
            raw_isbn = str(row.get(col_isbn, '')).strip().split('.')
            isbn_livro = "".join([c for c in raw_isbn if c.isdigit()])
            if not isbn_livro or len(isbn_livro) < 5: 
                continue
                
            # Captura o Título por extenso e o Nome do Autor da Obra
            titulo_livro = str(row.get(col_tit, '')).strip()
            autor_livro = str(row.get(col_aut, 'Desconhecido')).strip()
            
            # Trava de segurança: Se o título veio duplicando o ISBN por erro de linha, corrige
            if titulo_livro == isbn_livro or titulo_livro.lower() in ['nan', '']:
                continue

            # Captura e formatação de valores em Reais
            preco_raw = str(row.get(col_pre, '')).strip() if col_pre else ""
            if not preco_raw or preco_raw.lower() in ['nan', '0', '0.0', '']:
                preco_livro = "Sob consulta"
            else:
                preco_limpo = preco_raw.upper().replace('R$', '').replace('$', '').strip()
                preco_livro = f"R$ {preco_limpo}"
            
            # Puxa o resumo longo técnico diretamente da coluna R (18ª posição da planilha)
            txt_res = ""
            if len(row) >= 18:
                txt_res = str(row.iloc[17]).strip()
            
            if not txt_res or txt_res.lower() in ['nan', '']:
                txt_res = "Resumo detalhado disponível sob consulta na secretaria da Editora."
            
            # Puxa o Índice/Sumário do livro da coluna correspondente (geralmente coluna S / 19ª posição)
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
            return None, [], "❌ Erro ao associar os dados. Verifique a planilha Excel."
            
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = Chroma.from_documents(documents, embeddings)
        
        return vectorstore.as_retriever(search_kwargs={"k": 2}), sorted(list(lista_autores)), f"✅ Conexão estável! {len(documents)} obras jurídicas Olejnik operacionais."
        
    except Exception as e:
        return None, [], f"❌ Erro ao ler a estrutura do arquivo: {e}"

# Inicializa o processador inteligente
with st.spinner("Alinhando Títulos, preços e resumos do acervo Olejnik (Aguarde)..."):
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
# EXIBIÇÃO INTEGRAL E INTEGRADA DAS INFORMAÇÕES
# =====================================================================
if resultados:
    st.subheader("📚 Obras Sugeridas:")
    st.write("---")
    
    for idx, livre in enumerate(resultados):
        m = livre.metadata
        col_img, col_dados = st.columns([1, 4]) # Divide a tela perfeitamente entre imagem e texto
        
        with col_img:
            # Puxa a capa oficial usando a URL dinâmica baseada no ISBN real da planilha
            link_capa_dinamico = f"https://edicionesolejnik.com.br{m['isbn']}.jpg"
            st.image(link_capa_dinamico, width=140)
                
        with col_dados:
            # EXIBE O TÍTULO REAL DA OBRA POR EXTENSO E O ISBN EM CONJUNTO NO TOPO
            st.markdown(f"### {m['titulo']}")
            st.markdown(f"**Autor:** {m['autor']} | **ISBN do Livro:** {m['isbn']} | **Preço:** {m['preco']}")
            
            with st.expander("📖 Ver Sumário / Índice Completo"):
                st.write(m['indice'])
                
            with st.expander("📝 Ver Resumo Técnico / Resenha"):
                st.write(m['resumo'])
                
            link_compra = "https://edicionesolejnik.com.br"
            st.markdown(f"<a href='{link_compra}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;'>🛒 Comprar no Site Oficial</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)
