import os
import pandas as pd
import streamlit as st

# Configuração da página do Streamlit
st.set_page_config(page_title="Ediciones Olejnik - Buscador", page_icon="⚖️", layout="wide")

# Cabeçalho com a identidade da Editora
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚖️ Ediciones Olejnik</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Buscador Bibliográfico para Ciências Jurídicas</h3>", unsafe_allow_html=True)
st.markdown("---")

# ==============================================================================
# 1. LOCALIZAÇÃO DA PLANILHA EXCEL NO REPOSITÓRIO
# ==============================================================================
caminho_excel = None
for arquivo in os.listdir('.'):
    if arquivo.lower().endswith(('.xlsx', '.xls')) and not arquivo.startswith('~$'):
        caminho_excel = arquivo
        break

if not caminho_excel:
    st.error("❌ Erro: Nenhuma planilha Excel (.xlsx) foi encontrada na raiz do seu GitHub.")
    st.info("👉 Por favor, faça o upload da sua planilha Excel direto no site do GitHub junto com este código.")
    st.stop()

# Carrega a planilha (considerando o cabeçalho na linha correta)
df = pd.read_excel(caminho_excel, header=1)

# ==============================================================================
# 2. INTERFACE DE PESQUISA (ABAS TRADICIONAIS)
# ==============================================================================
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
# 3. EXIBIÇÃO DAS OBRAS E ACABAMENTO VISUAL PERSONALIZADO
# ==============================================================================
if not livros_filtrados.empty:
    st.markdown(f"### 📋 Obras Sugeridas Localizadas ({len(livros_filtrados)}):")
    
    for idx, livro in livros_filtrados.iterrows():
        st.markdown("---")
        
        # Coleta das informações básicas da linha atual
        titulo_livro = str(livro.get('Título', 'Título Indisponível'))
        isbn_exibicao = str(livro.get('ISBN-EAN', 'N/A'))
        
        # Puxa o resumo e índice das colunas da própria planilha
        texto_resenha = str(livro.get('Reseña', ''))
        texto_indice = str(livro.get('Indice_Completo', ''))

        if not texto_resenha or texto_resenha.lower() == 'nan' or texto_resenha.strip() == '':
            texto_resenha = "Reseña técnica disponible bajo consulta en la Editorial."
            
        if not texto_indice or texto_indice.lower() == 'nan' or texto_indice.strip() == '':
            texto_indice = "Índice detalhado disponível sob consulta na secretaria da Editorial."

        # Layout com duas colunas (Capa na Esquerda, Textos na Direita)
        col_capa, col_texto = st.columns([1, 4])
        
        with col_capa:
            # BLOCO PERSONALIZADO: Cria um card HTML elegante com fundo azul escuro, nome do livro e ISBN
            card_capa_html = f"""
            <div style="
                background-color: #1E3A8A; 
                color: #FFFFFF; 
                padding: 20px 15px; 
                border-radius: 8px; 
                text-align: center; 
                box-shadow: 2px 2px 10px rgba(0,0,0,0.15);
                min-height: 220px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                align-items: center;
                border: 2px solid #1D4ED8;
            ">
                <div style="font-size: 14px; font-weight: bold; margin-bottom: 10px; line-height: 1.3; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical;">
                    {titulo_livro}
                </div>
                <div style="background-color: #172554; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-family: monospace; letter-spacing: 0.5px; width: 100%;">
                    ISBN {isbn_exibicao}
                </div>
            </div>
            """
            st.markdown(card_capa_html, unsafe_allow_html=True)
                
        with col_texto:
            st.markdown(f"#### **{titulo_livro}**")
            st.markdown(f"👤 **Autor:** {livro.get('Autor', 'N/A')}  |  🆔 **ISBN:** {isbn_exibicao}")
            
            with st.expander("📝 Ver Resumen Técnico / Reseña Completa"):
                st.write(texto_resenha)
                
            with st.expander("📖 Ver Sumário / Índice Detalhado por Capítulos"):
                st.write(texto_indice)
            
            link_loja = livro.get('Link_Site', '#')
            st.link_button("🛒 Comprar no Site Oficial", link_loja, type="primary")

elif autor_selecionado or termo_busca:
    st.info("⚠️ Nenhum livro foi encontrado para os critérios selecionados.")
