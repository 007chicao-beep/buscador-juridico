import os
import zipfile
import requests
import pandas as pd
from docx import Document as DocxReader
import streamlit as st

# Configuração da página do Streamlit
st.set_page_config(page_title="Buscador Jurídico", layout="wide")

# ==============================================================================
# 1. DOWNLOAD E EXTRAÇÃO AUTOMÁTICA DO ARQUIVO DE CAPAS DO DRIVE (1.890 FOTOS)
# ==============================================================================
# ID extraído do link que você enviou
ID_CAPAS_DRIVE = "1CnfjblNWOhWWFNuq4gCs6XGKwMWW9bex"

arquivo_capas_zip = "capas.zip"
pasta_destino_capas = "capas"

def baixar_capas_do_drive(id_drive, nome_destino):
    url = f'https://google.com{id_drive}'
    resposta = requests.get(url, stream=True)
    if resposta.status_code == 200:
        with open(nome_destino, 'wb') as f:
            for pedaco in resposta.iter_content(chunk_size=8192):
                f.write(pedaco)
        return True
    return False

# Executa o download e a extração apenas uma vez ao iniciar o servidor do Streamlit
if not os.path.exists(pasta_destino_capas):
    with st.spinner("🚀 Inicializando servidor: Baixando e extraindo catálogo com 1.890 capas..."):
        sucesso_download = baixar_capas_do_drive(ID_CAPAS_DRIVE, arquivo_capas_zip)
        
        if sucesso_download and os.path.exists(arquivo_capas_zip):
            try:
                with zipfile.ZipFile(arquivo_capas_zip, 'r') as zip_ref:
                    zip_ref.extractall(pasta_destino_capas)
                # Remove o zip temporário para não ocupar espaço desnecessário no servidor
                os.remove(arquivo_capas_zip)
                st.toast("🖼️ Catálogo de capas carregado com sucesso!", icon="✅")
            except Exception as e:
                st.error(f"Erro ao descompactar o arquivo de capas: {e}")

# ==============================================================================
# 2. CARREGAMENTO DOS DADOS JURÍDICOS (PLANILHA EXCEL)
# ==============================================================================
# Procurar automaticamente pela planilha gerada pelo seu robô
caminho_excel = None
for arquivo in os.listdir('.'):
    if arquivo.lower().endswith(('.xlsx', '.xls')) and not arquivo.startswith('~$'):
        caminho_excel = arquivo
        break

st.title("📚 Buscador Jurídico - Obras Sugeridas")

if not caminho_excel:
    st.error("❌ Erro: Planilha de dados Excel não localizada no repositório do GitHub. Certifique-se de realizar o upload dela!")
else:
    # Carrega a planilha (ajuste o parâmetro 'header' se o seu cabeçalho estiver em outra linha)
    df = pd.read_excel(caminho_excel)

    # Criação do Filtro de Autores na tela (semelhante ao seu print original)
    autores_disponiveis = sorted(df['Autor'].dropna().unique())
    autor_selecionado = st.selectbox("👤 Selecione o Autor que deseja consultar:", [""] + autores_disponiveis)

    if autor_selecionado:
        st.markdown(f"## 📚 Obras Sugeridas de **{autor_selecionado}**:")
        
        # Filtra os livros do autor selecionado
        livros_filtrados = df[df['Autor'] == autor_selecionado]
        
        for idx, livro in livros_filtrados.iterrows():
            st.markdown("---")
            
            # Limpa o ISBN tirando pontos e espaços para bater com o nome da imagem
            raw_isbn = str(livro.get('ISBN-EAN', '')).strip().split('.')
            isbn_livro = "".join([c for c in raw_isbn if c.isdigit()])
            
            # Define os caminhos possíveis onde a imagem descompactada pode estar
            # (Adiciona tratamento caso ela esteja dentro de uma subpasta criada pelo ZIP)
            caminhos_possiveis = [
                f"capas/{isbn_livro}.jpg",
                f"capas/{isbn_livro}.png",
                f"capas/{isbn_livro}.jpeg",
                f"capas/capas/{isbn_livro}.jpg", # Trata caso a pasta tenha sido zipada dentro de outra pasta
                f"capas/capas/{isbn_livro}.png"
            ]
            
            caminho_foto_final = None
            for caminho in caminhos_possiveis:
                if os.path.exists(caminho):
                    caminho_foto_final = caminho
                    break
            
            # Divide a interface em duas colunas: Capa na Esquerda, Textos e Botões na Direita
            col_capa, col_texto = st.columns([1, 4])
            
            with col_capa:
                if caminho_foto_final:
                    st.image(caminho_foto_final, width=160)
                else:
                    # Imagem cinza padrão caso o livro não possua foto correspondente ao ISBN
                    st.image("https://unsplash.com", 
                             caption="Capa não disponível")
                    st.caption(f"ISBN buscado: {isbn_livro}")
                    
            with col_texto:
                st.markdown(f"### {livro.get('Título', 'Título do Livro')}")
                st.markdown(f"**Autor:** {livro.get('Autor')} | **ISBN do Livro:** {livro.get('ISBN-EAN')}")
                
                # Sanfona para exibir a resenha
                with st.expander("📝 Ver Resumen Técnico / Reseña Completa"):
                    st.write(livro.get('Reseña', 'Reseña técnica disponible bajo consulta na Editorial.'))
                    
                # Sanfona para exibir o sumário
                with st.expander("📖 Ver Sumário / Índice Detalhado por Capítulos"):
                    st.write(livro.get('Indice_Completo', 'Índice detalhado disponível sob consulta na secretaria.'))
                
                # Botão de Compra
                link_compra = livro.get('Link_Site', '#') # Ajuste o nome da coluna se for diferente na planilha
                st.link_button("🛒 Comprar no Site Oficial", link_compra, type="primary")
