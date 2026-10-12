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

# Função auxiliar para remover acentos, cedilhas e caracteres especiais de busca
def normalizar_texto(texto):
    if not texto or pd.isna(texto):
        return ""
    texto_str = str(texto).lower().strip()
    nfkd_form = unicodedata.normalize('NFKD', texto_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# =====================================================================
# LEITURA DE DADOS ULTRA-LEVE DA NOVA PLANILHA UNIFICADA
# =====================================================================
@st.cache_data
def carregar_catalogo_completo_olejnik():
    caminho_excel = "catalogo_completo_olejnik.xlsx"
    
    if not os.path.exists(caminho_excel):
        for arquivo in os.listdir('.'):
            if arquivo.lower().endswith(('.xlsx', '.xls')) and not arquivo.startswith('~$'):
                caminho_excel = arquivo
                break
                
    if not os.path.exists(caminho_excel):
        return None, "❌ Erro: A planilha unificada 'catalogo_completo_olejnik.xlsx' não foi localizada no repositório."
        
    try:
        df = pd.read_excel(caminho_excel)
        
        # Sincroniza e limpa as colunas oficiais geradas pelo robô extrator
        df['ISBN-EAN'] = df['ISBN-EAN'].astype(str).str.strip().str.replace('.0', '', regex=False)
        df['Titulo - Sub.titulo'] = df['Titulo - Sub.titulo'].astype(str).str.strip()
        df['Autor'] = df['Autor'].astype(str).str.strip()
        df['Reseña'] = df['Reseña'].astype(str).str.strip()
        df['Indice_Completo'] = df['Indice_Completo'].astype(str).str.strip()
        
        # Cria colunas invisíveis de busca cruzada e bilíngue (removendo acentos)
        df['busca_titulo'] = df['Titulo - Sub.titulo'].apply(normalizar_texto)
        df['busca_autor'] = df['Autor'].apply(normalizar_texto)
        df['busca_resena'] = df['Reseña'].apply(normalizar_texto)
        df['busca_indice'] = df['Indice_Completo'].apply(normalizar_texto)
        
        # Filtra linhas inválidas ou sem título
        df = df[df['Titulo - Sub.titulo'].notna() & (df['Titulo - Sub.titulo'] != 'nan') & (df['Titulo - Sub.titulo'] != '')]
        return df, "✅ Catálogo mestre unificado com sucesso!"
    except Exception as e:
        return None, f"❌ Erro ao ler a nova planilha Excel: {e}"

# Inicializa o banco de dados de alta performance
with st.spinner("Carregando o catálogo unificado de livros jurídicos... Aguarde..."):
    df, mensagem = carregar_catalogo_completo_olejnik()

if df is None:
    st.error(mensagem)
    st.stop()

# Coleta e ordena a lista de autores reais cadastrados no catálogo mestre
autores_reais = sorted([str(a) for a in df['Autor'].unique() if pd.notna(a) and str(a).lower() != 'nan' and str(a) != 'Consultar Catálogo'])

# =====================================================================
# TELA DE PESQUISA DO ADVOGADO (BILÍNGUE POR TEMA OU AUTOR)
# =====================================================================
st.sidebar.success(f"📊 {len(df)} Obras Operacionais")
st.sidebar.markdown("### Menu de Busca")
tipo_busca = st.sidebar.radio("Selecione o método de consulta:", ["Pesquisa por Tema / Conteúdo", "Filtrar por Autor"])

resultados = pd.DataFrame()

if tipo_busca == "Pesquisa por Tema / Conteúdo":
    pergunta = st.text_input("🔍 Digite palavras-chave do tema ou livro que você procura:", 
                            placeholder="Ex: Tributação, penal, constitucional, direito comercial...")
    if pergunta:
        termo_normalizado = normalizar_texto(pergunta)
        # Varre instantaneamente as 4 colunas de texto ao mesmo tempo (cruzando PT/ES sem travar)
        resultados = df[
            df['busca_titulo'].str.contains(termo_normalizado, na=False) |
            df['busca_autor'].str.contains(termo_normalizado, na=False) |
            df['busca_resena'].str.contains(termo_normalizado, na=False) |
            df['busca_indice'].str.contains(termo_normalizado, na=False)
        ].head(8) # Traz os 8 melhores resultados com velocidade máxima
else:
    autor_selecionado = st.selectbox("📚 Selecione o Autor que deseja consultar:", [""] + autores_reais)
    if autor_selecionado:
        resultados = df[df['Autor'] == autor_selecionado].head(15)

# =====================================================================
# EXIBIÇÃO DE RESULTADOS COM VISUAL CORPORATIVO E SEM EXIBIÇÃO DE PREÇO
# =====================================================================
if not resultados.empty:
    st.subheader("📚 Obras Sugeridas:")
    st.write("---")
    
    for _, row in resultados.iterrows():
        col_img, col_dados = st.columns([1, 4]) # Proporção ideal de tela (Capa menor, textos maiores)
        
        isbn_limpo = "".join([c for c in str(row['ISBN-EAN']) if c.isdigit()])
        titulo_obra = row['Titulo - Sub.titulo']
        
        with col_img:
            # HTML para desenhar uma capa elegante em azul corporativo protegida contra quebras de links
            html_capa_reserva = f"""
            <div style="width:130px; height:195px; background-color:#1E3A8A; color:white; 
                        border-radius:4px; padding:12px; display:flex; flex-direction:column; 
                        justify-content:center; align-items:center; text-align:center;
                        box-shadow: 2px 2px 6px rgba(0,0,0,0.35); border: 1px solid #0f255c;
                        font-family: sans-serif;">
                <div style="font-size:9px; font-weight:bold; margin-bottom:12px; color:#93C5FD; text-transform: uppercase; letter-spacing: 1px;">Ediciones Olejnik</div>
                <div style="font-size:11px; font-weight:600; line-height:1.3; overflow:hidden; display:-webkit-box; -webkit-line-clamp:6; -webkit-box-orient:vertical;">{titulo_obra}</div>
                <div style="font-size:8px; margin-top:auto; color:#93C5FD; font-weight: 500;">ISBN {isbn_limpo}</div>
            </div>
            """
            st.markdown(html_capa_reserva, unsafe_allow_html=True)
                
        with col_dados:
            st.markdown(f"### {titulo_obra}")
            
            autor_exibir = row['Autor'] if str(row['Autor']).lower() != 'nan' else "Consultar Editora"
            st.markdown(f"**Autor:** {autor_exibir} | **ISBN do Livro:** {isbn_limpo}")
            
            # Exibe a resenha técnica longa e sem cortes extraída pelo robô
            with st.expander("📝 Ver Resumen Técnico / Reseña Completa"):
                txt_reseña = row['Reseña']
                if not txt_reseña or str(txt_reseña).lower() == 'nan':
                    txt_reseña = "Reseña técnica disponible bajo consulta en la Editorial."
                st.write(txt_reseña)
                
            # Exibe o índice original completo mapeado por capítulos pelo robô de forma limpa
            with st.expander("📖 Ver Sumário / Índice Detalhado por Capítulos"):
                txt_indice = row['Indice_Completo']
                if not txt_indice or str(txt_indice).lower() == 'nan' or 'Índice detalhado disponível' in str(txt_indice):
                    txt_indice = "Índice detallado disponible bajo consulta en la secretaría de la Editorial."
                    st.write(txt_indice)
                else:
                    st.text(txt_indice) # st.text preserva a quebra de linhas original dos parágrafos do Word
                
            # Link comercial direcionado para o site oficial
            link_compra = "https://edicionesolejnik.com.br"
            st.markdown(f"<a href='{link_compra}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:8px 20px; border-radius:4px; cursor:pointer; font-weight: 500;'>🛒 Comprar no Site Oficial</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)
elif pergunta if 'pergunta' in locals() else False:
    st.warning("⚠️ Nenhuma obra correspondente foi encontrada para esse termo no catálogo atual. Tente buscar usando termos mais gerais (ex: tribut, penal, constitu).")
