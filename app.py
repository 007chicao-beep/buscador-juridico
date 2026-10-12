import os
import zipfile
import gdown
import pandas as pd
from docx import Document as DocxReader
import streamlit as st

# Configuração da página do Streamlit
st.set_page_config(page_title="Buscador Jurídico", layout="wide")

# ==============================================================================
# 1. DOWNLOAD E EXTRAÇÃO DAS CAPAS COM GDOWN (ESTÁVEL E SEM ERROS DE CONEXÃO)
# ==============================================================================
ID_CAPAS_DRIVE = "1CnfjblNWOhWWFNuq4gCs6XGKwMWW9bex"

arquivo_capas_zip = "capas.zip"
pasta_destino_capas = "capas"

# Executa o download estável e a extração apenas uma vez ao iniciar o app
if not os.path.exists(pasta_destino_capas):
    with st.spinner("🚀 Inicializando servidor: Baixando catálogo com 1.890 capas..."):
        url_drive = f'https://google.com{ID_CAPAS_DRIVE}'
        
        try:
            # Faz o download seguro driblando o bloqueio de arquivos grandes do Google
            gdown.download(url_drive, arquivo_capas_zip, quiet=False)
            
            if os.path.exists(arquivo_capas_zip):
                with zipfile.ZipFile(arquivo_capas_zip, 'r') as zip_ref:
                    zip_ref.extractall(pasta_destino_capas)
                # Apaga o zip temporário para liberar memória no Streamlit Cloud
                os.remove(arquivo_capas_zip)
                st.toast("🖼️ Catálogo de capas carregado com sucesso!", icon="✅")
        except Exception as e:
            st.error(f"⚠️ Erro ao processar o arquivo de capas do Drive: {e}")
            st.info("Tentando seguir com o aplicativo sem as imagens por enquanto...")

# ==============================================================================
# 2. CARREGAMENTO E EXIBIÇÃO DOS DADOS (PLANILHA EXCEL)
# ==============================================================================
caminho_excel = None
for arquivo in os.listdir('.'):
    if arquivo.lower().endswith(('.xlsx', '.xls')) and not arquivo.startswith('~$'):
        caminho_excel = arquivo
        break

st.title("📚 Buscador Jurídico - Obras Sugeridas")

if not caminho_excel:
    st.error("❌ Erro: Planilha de dados Excel não localizada no repositório. Faça o upload dela no seu GitHub!")
else:
    df = pd.read_excel(caminho_excel)

    autores_disponiveis = sorted(df['Autor'].dropna().unique())
    autor_selecionado = st.selectbox("👤 Selecione o Autor que deseja consultar:", [""] + autores_disponiveis)

    if autor_selecionado:
        st.markdown(f"## 📚 Obras Sugeridas de **{autor_selecionado}**:")
        livros_filtrados = df[df['Autor'] == autor_selecionado]
        
        for idx, livro in livros_filtrados.iterrows():
            st.markdown("---")
            
            # CORRIGIDO: Vinculando dinamicamente ao dicionário do livro atual do loop
            raw_isbn = str(livro.get('ISBN-EAN', '')).strip().split('.')
            isbn_livro = "".join([c for c in raw_isbn if c.isdigit()])
            
            caminhos_possiveis = [
                f"capas/{isbn_livro}.jpg",
                f"capas/{isbn_livro}.png",
                f"capas/{isbn_livro}.jpeg",
                f"capas/capas/{isbn_livro}.jpg",
                f"capas/capas/{isbn_livro}.png"
            ]
            
            caminho_foto_final = None
            for caminho in caminhos_possiveis:
                if os.path.exists(caminho):
                    caminho_foto_final = caminho
                    break
            
            col_capa, col_texto = st.columns() # Dá um espaçamento elegante na tela
            
            with col_capa:
                if caminho_foto_final:
                    st.image(caminho_foto_final, width=160)
                else:
                    st.image("https://unsplash.com", 
                             caption="Capa não disponível")
                    st.caption(f"ISBN: {isbn_livro}")
                    
            with col_texto:
                st.markdown(f"### {livro.get('Título', 'Título do Livro')}")
                st.markdown(f"**Autor:** {livro.get('Autor')} | **ISBN do Livro:** {livro.get('ISBN-EAN')}")
                
                with st.expander("📝 Ver Resumen Técnico / Reseña Completa"):
                    st.write(livro.get('Reseña', 'Reseña técnica disponible bajo consulta na Editorial.'))
                    
                with st.expander("📖 Ver Sumário / Índice Detalhado por Capítulos"):
                    st.write(livro.get('Indice_Completo', 'Índice detalhado disponível sob consulta na secretaria.'))
                
                link_compra = livro.get('Link_Site', '#')
                st.link_button("🛒 Comprar no Site Oficial", link_compra, type="primary")
