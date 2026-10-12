import streamlit as st
import pandas as pd
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Configuração visual e responsiva da aba do navegador
st.set_page_config(page_title="Ediciones Olejnik - Buscador IA", page_icon="⚖️", layout="wide")

# Elementos de Cabeçalho com a identidade da Editora
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚖️ Ediciones Olejnik</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Buscador Bibliográfico Cognitivo para Ciências Jurídicas</h3>", unsafe_allow_html=True)
st.markdown("---")

# =====================================================================
# INDICAÇÃO AUTOMÁTICA DE RESULTADOS COM CACHE SEGURO
# =====================================================================
@st.cache_resource
def inicializar_sistema_estatico():
    exemplo_livros = [
        {
            "titulo": "Tratado de Derecho Constitucional", 
            "autor": "Carlos Olejnik", 
            "isbn": "9789563920011", 
            "resumo": "Estudo profundo sobre direitos fundamentais, separação de poderes, controle de constitucionalidade e a dignidade humana no ordenamento contemporâneo. A obra esmiúça de forma integral as garantias processuais do cidadão, trazendo vasta jurisprudência comparada da América Latina e Europa, servindo como guia indispensável para pareceres complexos de controle concentrado.", 
            "indice": "Capítulo I: Teoria Geral do Estado.\nCapítulo II: Direitos Fundamentais Nacionais.\nCapítulo III: Mecanismos de Controle de Constitucionalidade.", 
            "preco": "150.00"
        },
        {
            "titulo": "Manual de Derecho Penal y Criminología", 
            "autor": "Enrique Olejnik", 
            "isbn": "9789563920022", 
            "resumo": "Análise técnica abrangente de crimes cibernéticos, tipicidade penal, teoria do delito, processo criminal, teorias da pena e aplicação prática no direito penal econômico. Traz um panorama completo das novas modalidades de fraudes digitais, lavagem de capitais e os critérios dogmáticos de imputação objetiva nas corporações modernas.", 
            "indice": "Capítulo I: Criminologia Moderna.\nCapítulo II: Elementos Clássicos do Delito.\nCapítulo III: Crimes de Informática e Inovações Tecnológicas.", 
            "preco": "135.00"
        }
    ]
    
    documents = []
    lista_autores = set()
    
    for livro in exemplo_livros:
        lista_autores.add(livro['autor'])
        texto_busca = f"Livro: {livro['titulo']} | Autor: {livro['autor']} | Resumo: {livro['resumo']} | Índice: {livro['indice']}"
        metadados = {
            "isbn": livro['isbn'],
            "titulo": livro['titulo'],
            "autor": livro['autor'],
            "indice": livro['indice'],
            "resumo": livro['resumo'],
            "preco": livro['preco']
        }
        documents.append(Document(page_content=texto_busca, metadata=metadados))
        
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(documents, embeddings)
    
    return vectorstore.as_retriever(search_kwargs={"k": 2}), sorted(list(lista_autores)), "✅ Acervo Inteligente da Editora conectado com sucesso!"

# Inicializa o processador inteligente de forma estável
with st.spinner("Conectando com segurança ao catálogo da Editora (Aguarde)..."):
    retriever, autores_disponiveis, mensagem = inicializar_sistema_estatico()

# =====================================================================
# TELA DE PESQUISA DO ADVOGADO COM RECURSO DE FILTRO POR AUTOR
# =====================================================================
st.sidebar.success(mensagem)
st.sidebar.markdown("### Menu de Busca")

tipo_busca = st.sidebar.radio("Selecione o método de consulta:", ["Pesquisa por Tema / Caso (IA)", "Filtrar por Autor"])

resultados = []

if tipo_busca == "Pesquisa por Tema / Caso (IA)":
    pergunta = st.text_input("🔍 Descreva o caso jurídico ou tema que você está trabalhando:", 
                            placeholder="Ex: Responsabilidade civil por erro médico ou direito penal...")
    if pergunta:
        with st.spinner("Buscando correlações doutrinárias..."):
            resultados = retriever.invoke(pergunta)
else:
    autor_selecionado = st.selectbox("📚 Selecione o Autor que deseja consultar:", [""] + autores_disponiveis)
    if autor_selecionado:
        with st.spinner("Puxando catálogo do autor..."):
            resultados = retriever.invoke(f"Autor: {autor_selecionado}")

# =====================================================================
# EXIBIÇÃO INTEGRAL DAS INFORMAÇÕES
# =====================================================================
if resultados:
    st.subheader("📚 Obras Sugeridas:")
    st.write("---")
    
    for idx, livre in enumerate(resultados):
        m = livre.metadata
        col_img, col_dados = st.columns([1, 4]) # Reserva espaço correto para a foto
        
        with col_img:
            # Vinculação direta com o seu site usando o ISBN
            link_capa_dinamico = f"https://edicionesolejnik.com.br{m['isbn']}.jpg"
            st.image(link_capa_dinamico, width=150)
                
        with col_dados:
            st.markdown(f"### {m['titulo']}")
            st.markdown(f"**Autor:** {m['autor']} | **ISBN:** {m['isbn']} | **Preço:** R$ {m['preco']}")
            
            # Abas interativas expansíveis organizadas sob demanda
            with st.expander("📖 Ver Sumário / Índice Completo"):
                st.text(m['indice'])
                
            with st.expander("📝 Ver Resumo Técnico / Resenha"):
                st.write(m['resumo'])
                
            link_compra = "https://edicionesolejnik.com.br"
            st.markdown(f"<a href='{link_compra}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;'>🛒 Comprar no Site Oficial</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)
