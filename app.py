import streamlit as st
from supabase import create_client, Client
import openai  # Se for usar OpenAI para gerar os vetores cognitivos

# 🔐 1. Conexão Segura com o seu Banco do Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuração da Página do App
st.set_page_config(page_title="Ediciones Olejnik - Buscador Cognitivo", page_icon="⚖️", layout="wide")

st.title("⚖️ Ediciones Olejnik")
st.subheader("Buscador Bibliográfico Cognitivo para Ciências Jurídicas")

# 🎨 2. Painel de Filtros Avançados na Interface
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    termo_pesquisa = st.text_input(
        "O que você está procurando?", 
        placeholder="Digite um Autor, Título, ISBN, País ou um Caso Concreto/Dúvida Jurídica..."
    )

with col2:
    filtro_pais = st.selectbox("Filtrar por País", ["Todos", "Argentina", "Chile", "Espanha", "Venezuela", "Colômbia", "México"])
    if filtro_pais == "Todos": filtro_pais = None

with col3:
    filtro_materia = st.selectbox("Filtrar por Matéria", ["Todas", "Direito Civil", "Direito Penal", "Direito Tributário", "Direito Administrativo"])
    if filtro_materia == "Todas": filtro_materia = None

# 🧠 3. Mecanismo de Execução ao Clicar em Buscar
if st.button("Iniciar Busca Inteligente", type="primary"):
    if termo_pesquisa:
        with st.spinner("Analisando o acervo doutrinário..."):
            
            # Variável para guardar o vetor caso seja uma busca cognitiva por IA
            vetor_pesquisa = None
            
            # Regra: Se o texto for longo, geramos o embedding (Vetor) para busca cognitiva
            if len(termo_pesquisa.split()) > 3 and not termo_pesquisa.isdigit():
                # Exemplo usando OpenAI para transformar a frase do advogado em vetor
                openai.api_key = st.secrets["OPENAI_API_KEY"]
                response = openai.Embedding.create(
                    input=[termo_pesquisa],
                    model="text-embedding-3-small"
                )
                vetor_pesquisa = response.data[0].embedding

            try:
                # 🔌 Chamada direta da função customizada que instalamos no Supabase
                resposta_banco = supabase.rpc(
                    "buscar_acervo_olejnik",
                    {
                        "termo_pesquisa": termo_pesquisa,
                        "filtro_pais": filtro_pais,
                        "filtro_materia": filtro_materia,
                        "query_embedding": vetor_pesquisa
                    }
                ).execute()

                resultados = resposta_banco.data

                # 📊 4. Exibição dos Cards de Resultados na Tela
                if resultados:
                    st.success(f"Encontramos {len(resultados)} correspondências no acervo da Olejnik:")
                    
                    for livro in resultados:
                        with st.container():
                            st.markdown(f"### 📕 {livro['titulo']}")
                            st.write(f"**Autor:** {livro['autor']} | **País:** {livro['pais']} | **ISBN:** {livro['isbn']}")
                            st.write(f"**Área:** {livro['materia_direito']} ({livro['sub_materia']})")
                            
                            # Indica se achou por termo exato ou por interpretação de IA
                            if livro['tipo_busca'] == 'Cognitiva (IA)':
                                st.info(f"💡 *Encontrado via Inteligência Artificial Cognitiva (Afinidade: {round(livro['similaridade'] * 100)}%)*")
                            else:
                                st.caption("🔍 *Correspondência direta de dados catalogados*")
                            st.markdown("---")
                else:
                    st.warning("Nenhum livro foi encontrado com os critérios informados.")

            except Exception as e:
                st.error(f"Erro ao conectar com o motor de busca: {e}")
    else:
        st.info("Por favor, digite um termo ou frase para pesquisar.")
