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
# 1. LOCALIZAÇÃO E CARREGAMENTO INTELIGENTE DA PLANILHA EXCEL
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

# Varre as primeiras 15 linhas para achar automaticamente onde começa o cabeçalho real
linha_cabecalho = 0
try:
    df_teste = pd.read_excel(caminho_excel, nrows=15, header=None)
    for idx, row in df_teste.iterrows():
        texto_linha = " ".join([str(val).upper() for val in row.values if pd.notna(val)])
        if any(termo in texto_linha for termo in ['ISBN', 'CODIGO', 'TITULO', 'AUTOR']):
            linha_cabecalho = idx
            break
except:
    linha_cabecalho = 0

# Carrega os dados com o cabeçalho localizado dinamicamente
df = pd.read_excel(caminho_excel, header=linha_cabecalho)

# Mapeia dinamicamente os nomes reais das colunas para evitar o erro KeyError
col_autor = next((c for c in df.columns if 'AUT' in str(c).upper()), None)
col_titulo = next((c for c in df.columns if any(t in str(c).upper() for t in ['TIT', 'NOM'])), None)
col_isbn = next((c for c in df.columns if any(t in str(c).upper() for t in ['ISBN', 'COD'])), None)
col_resena = next((c for c in df.columns if any(t in str(c).upper() for t in ['RESENA', 'RESEÑA', 'RESUMO'])), None)
col_indice = next((c for c in df.columns if any(t in str(c).upper() for t in ['INDICE', 'SUMARIO', 'SUMÁRIO'])), None)
col_link = next((c for c in df.columns if any(t in str(c).upper() for t in ['LINK', 'SITE', 'WEB'])), None)
col_materia = next((c for c in df.columns if any(t in str(c).upper() for t in ['MATERIA', 'TEMA', 'CATEGORIA'])), None)

# Validação básica das colunas obrigatórias
if not col_autor or not col_titulo:
    st.error("❌ Erro: Não foi possível identificar as colunas de 'Autor' ou 'Título' na sua planilha.")
    st.info("👉 Garanta que os nomes das colunas estejam bem definidos na planilha Excel.")
    st.stop()

# ==============================================================================
# 2. INTERFACE DE PESQUISA (ABAS TRADICIONAIS)
# ==============================================================================
aba_autor, aba_palavra = st.tabs(["👤 Pesquisar por Autor", "🔍 Pesquisar por Tema / Palavra-Chave"])

livros_filtrados = pd.DataFrame()

with aba_autor:
    autores_disponiveis = sorted(df[col_autor].dropna().unique())
    autor_selecionado = st.selectbox("Selecione o Autor que deseja consultar:", [""] + autores_disponiveis)
    if autor_selecionado:
        livros_filtrados = df[df[col_autor] == autor_selecionado]

with aba_palavra:
    termo_busca = st.text_input("Digite um Tema, Título ou Palavra-Chave para buscar no catálogo:")
    if termo_busca:
        # Filtra buscando correspondências no Título ou na Matéria (se existir)
        condicao_busca = df[col_titulo].str.contains(termo_busca, case=False, na=False)
        if col_materia:
            condicao_busca = condicao_busca | df[col_materia].astype(str).str.contains(termo_busca, case=False, na=False)
        livros_filtrados = df[condicao_busca]

# ==============================================================================
# 3. EXIBIÇÃO DAS OBRAS E ACABAMENTO VISUAL PERSONALIZADO (CARDS AZUIS)
# ==============================================================================
if not livros_filtrados.empty:
    st.markdown(f"### 📋 Obras Sugeridas Localizadas ({len(livros_filtrados)}):")
    
    for idx, livro in livros_filtrados.iterrows():
        st.markdown("---")
        
        # Coleta segura das informações básicas das colunas mapeadas
        titulo_livro = str(livro.get(col_titulo, 'Título Indisponível'))
        autor_livro = str(livro.get(col_autor, 'Autor Desconhecido'))
        isbn_exibicao = str(livro.get(col_isbn, 'N/A')) if col_isbn else 'N/A'
        
        # Puxa o resumo e índice de forma flexível
        texto_resenha = str(livro.get(col_resena, '')) if col_resena else ''
        texto_indice = str(livro.get(col_indice, '')) if col_indice else ''

        if not texto_resenha or texto_resenha.lower() == 'nan' or texto_resenha.strip() == '':
            texto_resenha = "Reseña técnica disponible bajo consulta en la Editorial."
            
        if not texto_indice or texto_indice.lower() == 'nan' or texto_indice.strip() == '':
            texto_indice = "Índice detalhado disponível sob consulta na secretaria da Editorial."

        # Layout com duas colunas (Capa Azul na Esquerda, Textos na Direita)
        col_capa, col_texto = st.columns([1, 4])
        
        with col_capa:
            # CARD VISUAL AZUL ESCURO PERSONALIZADO COM O NOME E ISBN DO LIVRO
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
                <div style="font-size: 13px; font-weight: bold; margin-bottom: 10px; line-height: 1.3; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical;">
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
            st.markdown(f"👤 **Autor:** {autor_livro}  |  🆔 **ISBN:** {isbn_exibicao}")
            
            with st.expander("📝 Ver Resumen Técnico / Reseña Completa"):
                st.write(texto_resenha)
                
            with st.expander("📖 Ver Sumário / Índice Detalhado por Capítulos"):
                st.write(texto_indice)
            
            link_loja = livro.get(col_link, '#') if col_link else '#'
            st.link_button("🛒 Comprar no Site Oficial", link_loja, type="primary")

elif autor_selecionado or termo_busca:
    st.info("⚠️ Nenhum livro foi encontrado para os critérios selecionados.")
