import streamlit as st
import pandas as pd
import os
import unicodedata

# Configuração visual e responsiva da aba do navegador
st.set_page_config(page_title="Ediciones Olejnik - Buscador IA", page_icon="⚖️", layout="wide")

# Elementos de Cabeçalho com a identidade da Editora
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚖️ Ediciones Olejnik</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Buscador Bibliográfico Inteligente para Ciências Jurídicas</h3>", unsafe_allow_html=True)
st.markdown("---")

# Função auxiliar para remover acentos, cedilhas e caracteres especiais
def normalizar_texto(texto):
    if not texto or pd.isna(texto):
        return ""
    texto_str = str(texto).lower().strip()
    nfkd_form = unicodedata.normalize('NFKD', texto_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

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
        df['Reseña'] = df['Reseña'].astype(str).str.strip()
        
        # Cria colunas invisíveis de busca "normalizadas" (sem acentos) para cruzamento de idiomas
        df['busca_titulo'] = df['Titulo - Sub.titulo'].apply(normalizar_texto)
        df['busca_autor'] = df['Autor'].apply(normalizar_texto)
        df['busca_resena'] = df['Reseña'].apply(normalizar_texto)
        
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
        termo_normalizado = normalizar_texto(pergunta)
        resultados = df[
            df['busca_titulo'].str.contains(termo_normalizado, na=False) |
            df['busca_autor'].str.contains(termo_normalizado, na=False) |
            df['busca_resena'].str.contains(termo_normalizado, na=False)
        ].head(8)
else:
    autor_selecionado = st.selectbox("📚 Selecione o Autor que deseja consultar:", [""] + autores_reais)
    if autor_selecionado:
        resultados = df[df['Autor'] == autor_selecionado].head(15)

# =====================================================================
# EXIBIÇÃO DE RESULTADOS AJUSTADA (SEM PREÇO, CAPA PROTEGIDA)
# =====================================================================
if not resultados.empty:
    st.subheader("📚 Obras Sugeridas:")
    st.write("---")
    
    for _, row in resultados.iterrows():
        col_img, col_dados = st.columns([1, 4]) # Dá a proporção ideal de espaçamento
        
        isbn_limpo = "".join([c for c in str(row['ISBN-EAN']) if c.isdigit()])
        titulo_obra = row['Titulo - Sub.titulo']
        
        with col_img:
            # Link dinâmico oficial da capa
            link_capa_dinamico = f"https://edicionesolejnik.com.br{isbn_limpo}.jpg"
            
            # HTML para desenhar uma capa elegante em azul caso a imagem oficial falhe
            html_capa_reserva = f"""
            <div style="width:130px; height:195px; background-color:#1E3A8A; color:white; 
                        border-radius:4px; padding:10px; display:flex; flex-direction:column; 
                        justify-content:center; align-items:center; text-align:center;
                        box-shadow: 2px 2px 5px rgba(0,0,0,0.3); border: 1px solid #0f255c;">
                <div style="font-size:10px; font-weight:bold; margin-bottom:10px; color:#93C5FD;">Ediciones Olejnik</div>
                <div style="font-size:11px; font-weight:600; line-height:1.2; overflow:hidden; display:-webkit-box; -webkit-line-clamp:6; -webkit-box-orient:vertical;">{titulo_obra}</div>
                <div style="font-size:8px; margin-top:auto; color:#93C5FD;">ISBN: {isbn_limpo}</div>
            </div>
            """
            
            # Como o servidor web gratuito bloqueia testes de imagem, exibimos a capa reserva estilizada
            # Caso queira forçar a imagem do site futuramente, basta trocar pela linha comentada abaixo
            # st.image(link_capa_dinamico, width=130)
            st.markdown(html_capa_reserva, unsafe_allow_html=True)
                
        with col_dados:
            st.markdown(f"### {titulo_obra}")
            st.markdown(f"**Autor:** {row['Autor']} | **ISBN do Livro:** {isbn_limpo}")
            
            # Exibe a resenha longa técnica completa e sem cortes contida na coluna Reseña
            with st.expander("📝 Ver Resumen Técnico / Reseña Completa"):
                st.write(row['Reseña'])
                
            # Solução para o Sumário/Índice via atendimento ágil
            with st.expander("📖 Ver Sumário / Índice Detalhado"):
                st.markdown("O sumário detalhado e a estrutura de capítulos desta obra estão disponíveis em formato Word digital.")
                link_whatsapp = f"https://wa.me{titulo_obra}%20(ISBN:%20{isbn_limpo})"
                st.markdown(f"<a href='{link_whatsapp}' target='_blank'><button style='background-color:#25D366; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-weight:bold;'>💬 Solicitar Índice via WhatsApp</button></a>", unsafe_allow_html=True)
                
            # Links comerciais de compra direcionados ao site
            col_btn1, col_btn2 = st.columns([1, 3])
            with col_btn1:
                link_compra = "https://edicionesolejnik.com.br"
                st.markdown(f"<a href='{link_compra}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer; width:100%;'>🛒 Comprar no Site</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)
elif pergunta if 'pergunta' in locals() else False:
    st.warning("⚠️ Nenhuma obra correspondente foi encontrada para esse termo no catálogo atual. Tente buscar usando termos mais gerais (ex: tribut, penal, constitu).")
