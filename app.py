import os
import zipfile
import pandas as pd
from docx import Document as DocxReader
import streamlit as st

# Configuração da página do Streamlit
st.set_page_config(page_title="Ediciones Olejnik - Buscador", page_icon="⚖️", layout="wide")

# Cabeçalho com a identidade da Editora
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚖️ Ediciones Olejnik</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Buscador Bibliográfico para Ciências Jurídicas</h3>", unsafe_allow_html=True)
st.markdown("---")

# ==============================================================================
# 1. PROCESSAMENTO DOS ARQUIVOS LOCAIS (ZIPS DA BARRA LATERAL OU GITHUB)
# ==============================================================================
arquivo_zip = "aplicativo.zip"  # Nome padrão do seu ZIP com os Words e Capas
pasta_extracao = "extracao_total"

# Verifica se o arquivo ZIP existe para começar
if not os.path.exists(arquivo_zip):
    st.error(f"❌ Erro: O arquivo '{arquivo_zip}' não foi encontrado. Garanta que ele foi enviado junto ao projeto!")
    st.info("👉 Se você usa o GitHub, certifique-se de que o 'aplicativo.zip' está na pasta raiz do repositório.")
    st.stop()

# Descompacta o arquivo na memória interna do servidor caso ainda não tenha sido feito
if not os.path.exists(pasta_extracao):
    with zipfile.ZipFile(arquivo_zip, 'r') as zip_ref:
        zip_ref.extractall(pasta_extracao)

# Varre a pasta de extração mapeando planilhas, words e capas
arquivos_no_zip = []
for raiz, _, arquivos in os.walk(pasta_extracao):
    for arq in arquivos:
        arquivos_no_zip.append(os.path.join(raiz, arq))

caminho_excel = next((c for c in arquivos_no_zip if c.lower().endswith(('.xlsx', '.xls')) and not os.path.basename(c).startswith('~$')), None)

if not caminho_excel:
    st.error("❌ Erro: Nenhuma planilha Excel foi localizada dentro do arquivo ZIP.")
    st.stop()

# Indexação dos documentos do Word e imagens de capa por ISBN
mapa_indices, mapa_resenhas, mapa_capas = {}, {}, {}
for cam in arquivos_no_zip:
    nome_arq = os.path.basename(cam).upper()
    isbn = "".join([c for c in nome_arq if c.isdigit()])
    if not isbn or len(isbn) < 5: 
        continue
    
    if "INDICE" in nome_arq or "SUMARIO" in nome_arq:
        mapa_indices[isbn] = cam
    elif "RESEÑA" in nome_arq or "RESENA" in nome_arq or "RESUMO" in nome_arq:
        mapa_resenhas[isbn] = cam
    elif nome_arq.lower().endswith(('.jpg', '.jpeg', '.png')):
        mapa_capas[isbn] = cam

def extrair_texto_docx(caminho):
    try:
        doc = DocxReader(caminho)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])
    except:
        return ""

# ==============================================================================
# 2. CARREGAMENTO DA PLANILHA E MONTAGEM DA INTERFACE
# ==============================================================================
# Abre a planilha considerando a linha correta do cabeçalho
df = pd.read_excel(caminho_excel, header=1)

# Interface de pesquisa tradicional por Abas que você usava
aba_autor, aba_palavra = st.tabs(["👤 Pesquisar por Autor", "🔍 Pesquisar por Tema / Palavra-Chave"])

livros_filtrados = pd.DataFrame()

with aba_autor:
    autores_disponiveis = sorted(df['Autor'].dropna().unique())
    autor_selecionado = st.selectbox("Selecione o Autor que deseja consultar:", [""] + autores_disponiveis)
    if autor_selecionado:
        livros_filtrados = df[df['Autor'] == autor_selecionado]

with aba_palavra:
    termo_busca = st.text_input("Digite um Tema, Título ou Palavra-Chave para buscar no catálogo:")
    if termo_busca:
        livros_filtrados = df[
            df['Título'].str.contains(termo_busca, case=False, na=False) |
            df['Materia'].astype(str).str.contains(termo_busca, case=False, na=False) if 'Materia' in df.columns else False
        ]

# ==============================================================================
# 3. EXIBIÇÃO DAS OBRAS ENCONTRADAS COM SEUS RESPECTIVOS TEXTOS E IMAGENS
# ==============================================================================
if not livros_filtrados.empty:
    st.markdown(f"### 📋 Obras Sugeridas Localizadas ({len(livros_filtrados)}):")
    
    for idx, livro in livros_filtrados.iterrows():
        st.markdown("---")
        
        # Amarração exata usando o ISBN limpo da linha atual
        raw_isbn = str(livro.get('ISBN-EAN', '')).strip().split('.')
        isbn_livro = "".join([c for c in raw_isbn if c.isdigit()])
        
        # Associa dinamicamente os textos lidos dos arquivos Word específicos
        c_res = mapa_resenhas.get(isbn_livro, None)
        c_ind = mapa_indices.get(isbn_livro, None)
        c_capa = mapa_capas.get(isbn_livro, None)

        texto_resenha = extrair_texto_docx(c_res) if c_res else str(livro.get('Reseña', ''))
        texto_indice = extrair_texto_docx(c_ind) if c_ind else "Índice detalhado disponível sob consulta na secretaria da Editorial."

        if not texto_resenha or texto_resenha.lower() == 'nan' or texto_resenha.strip() == '':
            texto_resenha = "Reseña técnica disponible bajo consulta en la Editorial."

        # Montagem do Layout visual de exibição na tela
        col_capa, col_texto = st.columns([1, 4]) # Mantém a proporção correta
        
        with col_capa:
            if c_capa and os.path.exists(c_capa):
                st.image(c_capa, width=150)
            else:
                st.image("https://unsplash.com", 
                         caption="Capa não disponível")
                st.caption(f"ISBN: {isbn_livro}")
                
        with col_texto:
            st.markdown(f"#### **{livro.get('Título', 'Título Indisponível')}**")
            st.markdown(f"👤 **Autor:** {livro.get('Autor', 'N/A')}  |  🆔 **ISBN:** {livro.get('ISBN-EAN', 'N/A')}")
            
            with st.expander("📝 Ver Resumen Técnico / Reseña Completa"):
                st.write(texto_resenha)
                
            with st.expander("📖 Ver Sumário / Índice Detalhado por Capítulos"):
                st.write(texto_indice)
            
            link_loja = livro.get('Link_Site', '#')
            st.link_button("🛒 Comprar no Site Oficial", link_loja, type="primary")

elif autor_selecionado or termo_busca:
    st.info("⚠️ Nenhum livro foi encontrado para os critérios selecionados.")
