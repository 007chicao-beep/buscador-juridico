import os
import zipfile
import gdown
import pandas as pd
from docx import Document as DocxReader
import streamlit as st

# Configuração da página do Streamlit
st.set_page_config(page_title="Buscador Jurídico", layout="wide")

# ==============================================================================
# 1. DOWNLOAD E EXTRAÇÃO DAS CAPAS (MANTIDO E CORRIGIDO)
# ==============================================================================
ID_CAPAS_DRIVE = "1CnfjblNWOhWWFNuq4gCs6XGKwMWW9bex"
arquivo_capas_zip = "capas.zip"
pasta_destino_capas = "capas"

if not os.path.exists(pasta_destino_capas):
    with st.spinner("🚀 Inicializando servidor: Carregando banco de dados de imagens..."):
        url_drive = f'https://google.com{ID_CAPAS_DRIVE}'
        try:
            gdown.download(url_drive, arquivo_capas_zip, quiet=True)
            if os.path.exists(arquivo_capas_zip):
                with zipfile.ZipFile(arquivo_capas_zip, 'r') as zip_ref:
                    zip_ref.extractall(pasta_destino_capas)
                os.remove(arquivo_capas_zip)
                st.toast("🖼️ Catálogo de capas carregado!", icon="✅")
        except Exception as e:
            st.warning(f"Aviso: Imagens indisponíveis no momento. Carregando catálogo textual... ({e})")

# ==============================================================================
# 2. LOCALIZAÇÃO DA PLANILHA EXCEL
# ==============================================================================
caminho_excel = None
for arquivo in os.listdir('.'):
    if arquivo.lower().endswith(('.xlsx', '.xls')) and not arquivo.startswith('~$'):
        caminho_excel = arquivo
        break

st.title("📚 Buscador Jurídico")

if not caminho_excel:
    st.error("❌ Erro: Planilha de dados Excel não localizada na raiz do repositório.")
else:
    # IMPORTANTE: Carrega os dados originais (ajuste o header se sua planilha tiver linhas em branco antes)
    @st.cache_data
    def carregar_e_processar_dados(caminho):
        # Lê a planilha assumindo que os dados principais começam na linha informada 
        # (Se seu Excel original usava header=1, mude aqui para header=1)
        df_base = pd.read_excel(caminho, header=0)
        return df_base

    df = carregar_e_processar_dados(caminho_excel)

    # ==============================================================================
    # 3. INTERFACE DE PESQUISA (SISTEMA DE BUSCA COMPLETO POR AUTOR OU PALAVRA-CHAVE)
    # ==============================================================================
    
    # Criando abas para separar os tipos de pesquisa
    aba_autor, aba_palavra = st.tabs(["👤 Pesquisar por Autor", "🔍 Pesquisar por Tema / Palavra-Chave"])
    
    livros_filtrados = pd.DataFrame() # Inicia vazio

    with aba_autor:
        autores_disponiveis = sorted(df['Autor'].dropna().unique())
        autor_selecionado = st.selectbox("Selecione o Autor que deseja consultar:", [""] + autores_disponiveis)
        if autor_selecionado:
            livros_filtrados = df[df['Autor'] == autor_selecionado]

    with aba_palavra:
        termo_busca = st.text_input("Digite um Tema, Título ou Palavra-Chave para buscar no catálogo:")
        if termo_busca:
            # Varre as colunas principais procurando pelo termo digitado
            livros_filtrados = df[
                df['Título'].str.contains(termo_busca, case=False, na=False) |
                df['Materia'].astype(str).str.contains(termo_busca, case=False, na=False) if 'Materia' in df.columns else False |
                df['Reseña'].astype(str).str.contains(termo_busca, case=False, na=False) if 'Reseña' in df.columns else False
            ]

    # ==============================================================================
    # 4. EXIBIÇÃO RESULTADOS E ASSOCIAÇÃO CORRETA DOS TEXTOS (RESUMO / ÍNDICE)
    # ==============================================================================
    if not livros_filtrados.empty:
        st.markdown(f"### 📋 Obras Sugeridas Localizadas ({len(livros_filtrados)}):")
        
        for idx, livro in livros_filtrados.iterrows():
            st.markdown("---")
            
            # Limpeza do ISBN para vincular à capa descompactada
            raw_isbn = str(livro.get('ISBN-EAN', '')).strip().split('.')
            isbn_livro = "".join([c for c in raw_isbn if c.isdigit()])
            
            # Mapeamento do caminho das imagens
            caminhos_possiveis = [
                f"capas/{isbn_livro}.jpg",
                f"capas/{isbn_livro}.png",
                f"capas/{isbn_livro}.jpeg",
                f"capas/capas/{isbn_livro}.jpg"
            ]
            caminho_foto_final = None
            for caminho in caminhos_possiveis:
                if os.path.exists(caminho):
                    caminho_foto_final = caminho
                    break

            # Cria as duas colunas na interface (1 parte para capa, 5 partes para o texto)
            col_capa, col_texto = st.columns([1, 5])
            
            with col_capa:
                if caminho_foto_final:
                    st.image(caminho_foto_final, width=150)
                else:
                    st.image("https://unsplash.com", 
                             caption="Capa não disponível")
                    st.caption(f"ISBN: {isbn_livro}")
                    
            with col_texto:
                st.markdown(f"#### **{livro.get('Título', 'Título Indisponível')}**")
                st.markdown(f"👤 **Autor:** {livro.get('Autor')}  |  🆔 **ISBN:** {livro.get('ISBN-EAN')}")
                
                # --- ASSOCIAÇÃO DO RESUMO ---
                with st.expander("📝 Ver Resumen Técnico / Reseña Completa"):
                    # Puxa o conteúdo direto da coluna 'Reseña' ou 'Resumo' associada à linha atual
                    texto_resenha = livro.get('Reseña', livro.get('Resumo', ''))
                    if pd.isna(texto_resenha) or str(texto_resenha).strip() == "" or str(texto_resenha).lower() == "nan":
                        texto_resenha = "Reseña técnica disponible bajo consulta en la Editorial."
                    st.write(texto_resenha)
                    
                # --- ASSOCIAÇÃO DO ÍNDICE/SUMÁRIO ---
                with st.expander("📖 Ver Sumário / Índice Detalhado por Capítulos"):
                    # Procura de forma dinâmica por qualquer variação do nome da coluna de índices completos
                    texto_indice = livro.get('Indice_Completo', livro.get('Índice', livro.get('Indice', '')))
                    if pd.isna(texto_indice) or str(texto_indice).strip() == "" or str(texto_indice).lower() == "nan":
                        texto_indice = "Índice detalhado disponível sob consulta na secretaria da Editorial."
                    st.write(texto_indice)
                
                # Botão para redirecionar para a loja
                link_loja = livro.get('Link_Site', livro.get('Link', '#'))
                st.link_button("🛒 Comprar no Site Oficial", link_loja, type="primary")
                
    elif (autor_selecionado if 'autor_selecionado' in locals() else False) or (termo_busca if 'termo_busca' in locals() else False):
        st.info("⚠️ Nenhum livro foi encontrado para os critérios selecionados.")
