import os
import pandas as pd
import streamlit as st

# Configuração visual da aba do navegador
st.set_page_config(page_title="Ediciones Olejnik - Buscador IA", page_icon="⚖️", layout="wide")

# Cabeçalho com a identidade da Editora
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚖️ Ediciones Olejnik</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Buscador Bibliográfico para Ciências Jurídicas</h3>", unsafe_allow_html=True)
st.markdown("---")

# ==============================================================================
# 1. LOCALIZAÇÃO DA PLANILHA EXCEL NA RAIZ DO GITHUB
# ==============================================================================
caminho_excel = None
for arquivo in os.listdir('.'):
    if arquivo.lower().endswith(('.xlsx', '.xls')) and not arquivo.startswith('~$'):
        caminho_excel = arquivo
        break

if not caminho_excel:
    st.error("❌ Erro: Planilha Excel não localizada na barra lateral. Garanta que ela está lá!")
    st.stop()

# Abre a planilha original mapeando exatamente a linha correta do cabeçalho que você usava (header=1)
df = pd.read_excel(caminho_excel, header=1)

# ==============================================================================
# 2. INTERFACE DE PESQUISA (SISTEMA DE BUSCA POR ABAS ORIGINAL)
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
# 3. EXIBIÇÃO CONFIGURADA EXATAMENTE COMO VOCÊ SE SENTIA CONFORTÁVEL
# ==============================================================================
if not livros_filtrados.empty:
    st.markdown(f"### 📋 Obras Sugeridas Localizadas ({len(livros_filtrados)}):")
    
    for idx, livro in livros_filtrados.iterrows():
        st.markdown("---")
        
        titulo_livro = str(livro.get('Título', 'Título Indisponível'))
        isbn_exibicao = str(livro.get('ISBN-EAN', 'N/A'))
        texto_resenha = str(livro.get('Reseña', 'Reseña técnica disponible bajo consulta en la Editorial.'))
        texto_indice = str(livro.get('Indice_Completo', 'Índice detalhado disponível sob consulta na secretaria da Editorial.'))

        # Duas colunas para alinhar a foto fictícia azul à esquerda e os dados à direita
        col_capa, col_texto = st.columns([1, 4])
        
        with col_capa:
            # CAPA PERSONALIZADA COM FUNDO AZUL, NOME E ISBN (Sem quebrar a formatação do texto)
            card_capa_html = f"""
            <div style="
                background-color: #1E3A8A; 
                color: #FFFFFF; 
                padding: 20px 12px; 
                border-radius: 6px; 
                text-align: center; 
                min-height: 220px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                align-items: center;
                border: 1px solid #1D4ED8;
            ">
                <div style="font-size: 12px; font-weight: bold; line-height: 1.3; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical;">
                    {titulo_livro}
                </div>
                <div style="background-color: #172554; padding: 4px 6px; border-radius: 4px; font-size: 11px; font-family: monospace; width: 100%;">
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
                # Retornado para o st.write() que mostrava a estrutura perfeitamente estável antes
                st.write(texto_indice)
            
            link_loja = livro.get('Link_Site', '#')
            st.link_button("🛒 Comprar no Site Oficial", link_loja, type="primary")

elif autor_selecionado or termo_busca:
    st.info("⚠️ Nenhum livro foi encontrado para os critérios selecionados.")
