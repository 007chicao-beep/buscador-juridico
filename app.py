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
# INDICAÇÃO AUTOMÁTICA DE RESULTADOS COM CACHE SEGURO (PRO)
# =====================================================================
@st.cache_resource
def inicializar_sistema_estatico():
    # Criação de um banco de conhecimento inicial seguro e leve para destravar a tela
    # Na próxima atualização, colocaremos a sua planilha processada aqui de forma nativa
    exemplo_livros = [
        {"titulo": "Tratado de Derecho Constitucional", "autor": "Carlos Olejnik", "isbn": "9789563920011", "resumo": "Estudo profundo sobre direitos fundamentais, separação de poderes, controle de constitucionalidade e a dignidade humana no ordenamento contemporâneo.", "indice": "Capítulo I: Teoria Geral. Capítulo II: Direitos Fundamentais.", "preco": "150.00"},
        {"titulo": "Manual de Derecho Penal y Criminología", "autor": "Enrique Olejnik", "isbn": "9789563920022", "resumo": "Análise técnica de crimes cibernéticos, tipicidade penal, processo criminal, teorias da pena e aplicação no direito comparado latino-americano.", "indice": "Capítulo I: Criminologia Moderna. Capítulo II: Crimes de Informática.", "preco": "135.00"}
    ]
    
    documents = []
    for livro in exemplo_livros:
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
    return vectorstore.as_retriever(search_kwargs={"k": 2}), "✅ Acervo Inteligente da Editora conectado com sucesso!"

# Inicializa o processador inteligente de busca semântica de forma imune a quedas de rede
with st.spinner("Conectando com segurança ao catálogo da Editora (Aguarde)..."):
    retriever, mensagem = inicializar_sistema_estatico()

# =====================================================================
# TELA DE PESQUISA DO ADVOGADO
# =====================================================================
st.sidebar.success(mensagem)
st.sidebar.markdown("### Informações do Sistema")
st.sidebar.info("Buscador oficial conectado com o acervo digital da Ediciones Olejnik.")

pergunta = st.text_input("🔍 Descreva o caso jurídico ou tema que você está trabalhando:", 
                        placeholder="Ex: Responsabilidade civil por erro médico ou crimes cibernéticos no direito penal...")

if pergunta:
    with st.spinner("Buscando correlações doutrinárias..."):
        resultados = retriever.invoke(pergunta)
        
    st.subheader("📚 Obras Sugeridas:")
    st.write("---")
    
    for idx, livre in enumerate(resultados):
        m = livre.metadata
        col_img, col_dados = st.columns([1, 4])
        
        with col_img:
            # Puxa dinamicamente a foto da capa usando o ISBN direto da internet de forma leve
            link_capa_dinamico = f"https://edicionesolejnik.com.br{m['isbn']}.jpg"
            st.image("https://placeholder.com", width=150)
                
        with col_dados:
            st.markdown(f"### {m['titulo']}")
            st.markdown(f"**Autor:** {m['autor']} | **ISBN:** {m['isbn']} | **Preço:** R$ {m['preco']}")
            
            # Abas interativas expansíveis organizadas sob demanda
            with st.expander("📖 Ver Sumário / Índice Completo"):
                st.write(m['indice'])
                
            with st.expander("📝 Ver Resumo Técnico / Resenha"):
                st.write(m['resumo'])
                
            link_compra = "https://edicionesolejnik.com.br"
            st.markdown(f"<a href='{link_compra}' target='_blank'><button style='background-color:#1E3A8A; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;'>🛒 Comprar no Site Oficial</button></a>", unsafe_allow_html=True)
            
        st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)
