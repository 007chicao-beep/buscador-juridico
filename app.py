import streamlit as st
import pandas as pd
import os

# Configuração visual e responsiva da aba do navegador
st.set_page_config(page_title="Ediciones Olejnik - Buscador IA", page_icon="⚖️", layout="wide")

# Elementos de Cabeçalho com a identidade da Editora
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚖️ Ediciones Olejnik</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Buscador Bibliográfico Inteligente para Ciências Jurídicas</h3>", unsafe_allow_html=True)
st.markdown("---")

# =====================================================================
# LEITURA DE DADOS ULTRA-LEVE (NÃO CONSOME MEMÓRIA DO SERVIDOR)
# =====================================================================
@st.cache_data
def carregar_catalogo_olejnik():
    caminho_excel = None
    for arquivo in os.listdir('.'):
        if arquivo.lower().endswith(('.xlsx', '.xls')) and not arquivo.startswith('~$'):
            caminho_excel = arquivo
            break
            
    if not caminho_excel:
        return None, "❌ Erro: Nenhuma planilha Excel (.xlsx) foi encontrada na pasta do projeto."
        
    try:
        # Abre o Excel pulando linhas vazias iniciais de forma automática
        df = pd.read_excel(caminho_excel, header=1)
        
        # Garante a limpeza dos dados básicos das colunas oficiais da editora
        df['ISBN-EAN'] = df['ISBN-EAN'].astype(str).str.strip().str.replace('.0', '', regex=False)
        df['Titulo - Sub.titulo'] = df['Titulo - Sub.titulo'].astype(str).str.strip()
        df['Autor'] = df['Autor'].astype(str).str.strip()
        df['REALES'] = df['REALES'].astype(str).str.strip()
        df['Reseña'] = df['Reseña'].astype(str).str.strip()
        
        # Filtra linhas inválidas ou sem título real
        df = df[df['Titulo - Sub.titulo'].notna() & (df['Titulo - Sub.titulo'] != 'nan') & (df['Titulo - Sub.titulo'] != '')]
        return df, "✅ Catálogo integrado com sucesso!"
    except Exception as e:
        return None, f"❌ Erro ao ler a planilha Excel: {e}"

# Inicializa o banco de dados leve
with st.spinner("Sincronizando acervo bibliográfico (Aguarde)..."):
    df, mensagem = carregar_catalogo_olejnik()

if df is None:
    st.error(mensagem)
    st.stop()

# Coleta e ordena a lista de autores reais cadastrados no Excel
autores_reais = sorted([str(a) for a in df['Autor'].unique() if pd.notna(a) and str(a).lower() != 'nan'])

# =====================================================================
# TELA DE PESQUISA DO ADVOGADO
# =====================================================================
st.sidebar.success(f"📊 {len(df)} Obras Disponíveis")
st.sidebar.markdown("### Menu de Busca")
tipo_busca = st.sidebar.radio("Selecione o método de consulta:", ["Pesquisa por Tema / Conteúdo", "Filtrar por Autor"])

resultados = pd.DataFrame()

if tipo_busca == "Pesquisa por Tema / Conteúdo":
    pergunta = st.text_input("🔍 Digite palavras-chave do tema ou livro que você procura:", 
                            placeholder="Ex: Tributação, penal, constitucional, crimes cibernéticos...")
    if pergunta:
        termo = pergunta.lower().strip()
        # Procura o termo digitado de forma instantânea nas três colunas de texto ao mesmo tempo
        resultados = df[
            df['Titulo - Sub.titulo'].str.lower().str.contains(termo, na=False) |
            df['Autor'].str.lower().str.contains(termo, na=False) |
            df['Reseña'].str.lower().str.contains(termo, na=False)
        ].head(5) # Mostra as 5 melhores correspondências sem pesar a tela
else:
    autor_selecionado = st.selectbox("📚 Selecione o Autor que deseja consultar:", [""] + autores_reais)
    if autor_selecionado:
        resultados = df[df['Autor'] == autor_selecionado].head(10)

# =====================================================================
# EXIBIÇÃO DE RESULTADOS COM RESENHA INTEGRAIS E PREÇO EM REAIS
# =====================================================================
if not resultados.empty:
    st.subheader("📚 Obras Sugeridas:")
    st.write("---")
    
    for _, row in resultados.iterrows():
        col_img, col_dados = st.columns([1, 4]) # Reserva o espaço proporcional ideal em tela
        
        isbn_limpo = "".join([c for c in str(row['ISBN-EAN']) if c.isdigit()])
        
        with col_img:
            # Puxa a capa oficial usando a URL dinâmica baseada no ISBN real da planilha
            link_capa_dinamico = f"https://edicionesolejnik.com.br{isbn_limpo}.jpg"
            st.image(link_capa_dinamico, width=130)
                
        with col_dados:
            st.markdown(f"### {row['Titulo - Sub.titulo']}")
            
            preco_val = str(row['REALES']).strip()
            preco_exibir = f"R$ {preco_val}" if preco_val and preco_val.lower() != 'nan' else "Sob consulta"
            
            st.markdown(f"**Autor:** {row['Autor']} | **ISBN do Livro:** {isbn_limpo} | **Preço:** {preco_exibir}")
            
            # Exibe a resenha longa técnica completa e sem cortes contida na coluna Reseña
            with st.expander("📝 Ver Resumen Técnico / Reseña Completa"):
                st.write(row['Reseña'])
                
            link_compra = "https://edicionesolejnik.com.br"
            st.markdown(f"<a href='{link_compra}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;'>🛒 Comprar no Site Oficial</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)
elif pergunta if 'pergunta' in locals() else False:
    st.warning("⚠️ Nenhuma obra correspondente foi encontrada para esse termo no catálogo atual.")
