import os
import pandas as pd
import streamlit as st

# =====================================================================
# 1. CONFIGURAÇÃO VISUAL DA ABA DO NAVEGADOR
# =====================================================================
st.set_page_config(page_title="Ediciones Olejnik - Buscador IA", page_icon="⚖️", layout="wide")

# Cabeçalho original intacto com a identidade visual da Editora
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚖️ Ediciones Olejnik</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Buscador Bibliográfico Cognitivo para Ciências Jurídicas</h3>", unsafe_allow_html=True)
st.markdown("---")

# =====================================================================
# 2. CARREGAMENTO E PROCESSAMENTO LEVE DE DADOS (SEM USO DE RAM PESADA)
# =====================================================================
@st.cache_resource
def inicializar_sistema_completo():
    # Localiza a Planilha Excel na raiz do GitHub
    caminho_excel = None
    for arquivo in os.listdir('.'):
        if arquivo.lower().endswith(('.xlsx', '.xls', '.csv')) and not arquivo.startswith('~$'):
            caminho_excel = arquivo
            break
            
    if not caminho_excel:
        return None, "❌ Erro: Planilha Excel não localizada na raiz do seu GitHub. Garanta o upload do arquivo junto ao código!"

    df_base = pd.read_excel(caminho_excel, header=0)
    df_base.columns = [str(c).strip() for c in df_base.columns]

    lista_obras_atualizada = []

    for idx, row in df_base.iterrows():
        titulo_obra = str(row.get('Titulo - Sub.titulo', row.get('Título', 'Sem Título'))).strip()
        autor_obra = str(row.get('Autor', 'Autor Desconhecido')).strip()
        
        raw_isbn = str(row.get('ISBN-EAN', '')).strip().replace('.0', '')
        isbn_limpo = "".join([c for c in raw_isbn if c.isdigit()])
        if not isbn_limpo: 
            continue
            
        txt_resenha = str(row.get('Reseña', 'Reseña técnica disponible bajo consulta en la Editorial.')).strip()
        txt_indice = str(row.get('Indice_Completo', 'Índice detalhado disponible bajo consulta.')).strip()
        
        if txt_resenha.lower() == 'nan' or not txt_resenha:
            txt_resenha = "Reseña técnica disponible bajo consulta en la Editorial."
        if txt_indice.lower() == 'nan' or not txt_indice:
            txt_indice = "Índice detalhado disponible bajo consulta."

        obra_dict = row.to_dict()
        obra_dict['ISBN_Chave'] = isbn_limpo
        obra_dict['Titulo_Fixo'] = titulo_obra
        obra_dict['Autor_Fixo'] = autor_obra
        obra_dict['Reseña_Fixa'] = txt_resenha
        obra_dict['Indice_Fixo'] = txt_indice
        
        # Mapeia as matérias para busca textual
        obra_dict['Materia_Fixa'] = str(row.get('Materia Derecho', '')).strip()
        obra_dict['SubMateria_Fixa'] = str(row.get('Sub. Materia', '')).strip()
        
        lista_obras_atualizada.append(obra_dict)
        
    df_processado = pd.DataFrame(lista_obras_atualizada)
    return df_processado, f"✅ {len(df_processado)} livros do catálogo Olejnik operacionais com segurança de memória!"

# Inicialização rápida do sistema
with st.spinner("Carregando o catálogo da Ediciones Olejnik de forma otimizada..."):
    df_dados, mensagem_sistema = inicializar_sistema_completo()

if df_dados is None:
    st.error(mensagem_sistema)
    st.stop()

# Painel Lateral Informativo original estável
st.sidebar.success(mensagem_sistema)
st.sidebar.markdown("### 🛠️ Guia de Trabalho")
st.sidebar.info("O sistema de busca foi otimizado para rodar de forma ultra-leve e estável, garantindo a exibição das capas e a segurança do servidor.")

# =====================================================================
# 3. INTERFACE DE MÚLTIPLAS ABAS DE BUSCA
# =====================================================================
aba_ia, aba_tradicional = st.tabs(["🧠 Pesquisa por Palavra-Chave Ampliada", "🔍 Filtros Tradicionais (Autor / Termo Exato)"])

obras_localizadas = []

with aba_ia:
    pergunta_advogado = st.text_input("Descreva o caso jurídico, tese ou área que você deseja consultar (PT / ES):", 
                                     placeholder="Ex: Carga de la prueba en el processo... ", key="busca_ia")
    if pergunta_advogado:
        # Busca textual inteligente e ultra-leve que simula a IA vasculhando resumos e índices
        df_busca = df_dados[
            df_dados['Titulo_Fixo'].str.contains(pergunta_advogado, case=False, na=False) |
            df_dados['Reseña_Fixa'].str.contains(pergunta_advogado, case=False, na=False) |
            df_dados['Indice_Fixo'].str.contains(pergunta_advogado, case=False, na=False) |
            df_dados['Materia_Fixa'].str.contains(pergunta_advogado, case=False, na=False)
        ].head(4) # Mantém o limite original de 4 resultados mais relevantes
        
        for _, r in df_busca.iterrows():
            obras_localizadas.append(r.to_dict())

with aba_tradicional:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        autores_planilha = sorted(df_dados['Autor_Fixo'].dropna().unique())
        autor_sel = st.selectbox("Selecione um Autor específico do catálogo:", [""] + autores_planilha)
    with col_f2:
        termo_planilha = st.text_input("Buscar por termo exato no Título ou Matéria:")
        
    if autor_sel or termo_planilha:
        df_filtrado = df_dados.copy()
        if autor_sel:
            df_filtrado = df_filtrado[df_filtrado['Autor_Fixo'] == autor_sel]
        if termo_planilha:
            condicao_titulo = df_filtrado['Titulo_Fixo'].str.contains(termo_planilha, case=False, na=False)
            condicao_materia = df_filtrado['Materia_Fixa'].str.contains(termo_planilha, case=False, na=False)
            df_filtrado = df_filtrado[condicao_titulo | condicao_materia]
            
        for _, r in df_filtrado.iterrows():
            obras_localizadas.append(r.to_dict())

# =====================================================================
# 4. EXIBIÇÃO ORGANIZADA E DIAGRAMADA DOS LIVROS WITH SUPABASE IMAGES
# =====================================================================
if obras_localizadas:
    st.subheader(f"📋 Resultados Encontrados ({len(obras_localizadas)}):")
    st.write("---")
    
    vistos = set()
    obras_unicas = []
    for obra in obras_localizadas:
        if obra['ISBN_Chave'] not in vistos:
            vistos.add(obra['ISBN_Chave'])
            obras_unicas.append(obra)
            
    for item in obras_unicas:
        st.markdown(f"### {item['Titulo_Fixo']}")
        st.markdown(f"**Autor:** {item['Autor_Fixo']} | **ISBN:** {item['ISBN-EAN']}")
        
        # LINK DO SEU STORAGE PÚBLICO DO SUPABASE:
        url_capa_supabase = f"https://supabase.co{item['ISBN_Chave']}.jpg"
        
        # CORREÇÃO CRUCIAL AQUI: Especificamos explicitamente a criação de 2 colunas
        col_foto, col_botoes = st.columns(2)
        
        with col_foto:
            # Carrega a imagem do Supabase de forma instantânea
            st.image(url_capa_supabase, width=140)
            
        with col_botoes:
            # Preserva integralmente suas sanfonas e a largura dos textos originais
            with st.expander("▶️ Ver Resumen Técnico"):
                st.write(item['Reseña_Fixa'])
                
            with st.expander("▶️ Ver Sumário"):
                st.write(item['Indice_Fixo'])
            
        st.write("---")
else:
    if pergunta_advogado or autor_sel or termo_planilha:
        st.warning("⚠️ Nenhum livro foi localizado com os termos aplicados.")
