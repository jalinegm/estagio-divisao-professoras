import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Alocação de Estágios - IFFar", layout="wide")

st.title("🎓 Sistema de Alocação de Orientandos de Estágio")
st.markdown("Faça o upload dos arquivos, insira os professores e escolha as regras para realizar a divisão automática.")

# --- FUNÇÃO PARA LER CSV COM PROTEÇÃO ---


def carregar_csv(arquivo):
    try:
        return pd.read_csv(arquivo, encoding='utf-8', sep=None, engine='python')
    except UnicodeDecodeError:
        arquivo.seek(0)
        return pd.read_csv(arquivo, encoding='latin-1', sep=None, engine='python')


# --- SEÇÃO 1 e 2: UPLOADS E PROFESSORES ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Dados dos Estudantes")
    file_participantes = st.file_uploader(
        "Upload da Planilha de Participantes (.csv)", type=['csv'])
    file_enquete = st.file_uploader(
        "Upload da Enquete de Estágio (.csv)", type=['csv'])

with col2:
    st.subheader("2. Professores e Campi")
    professores_default = """Andrea Silva - Reitoria
Andressa Rodrigues - Santo Ângelo
Carla Tatiana Zappe - Reitoria
Cátia Keske - Panambi
Fabricia Sônego - Reitoria
Jaline Mombach - Reitoria
Janete Maria de Conto - Reitoria
Jiani Cardoso da Roza - Alegrete
Luthiane Miszak de Oliveira - Santo Ângelo
Marcele Ravasio - Santo Ângelo"""

    professores_input = st.text_area(
        "Insira os professores (Nome - Campus), um por linha:",
        value=professores_default,
        height=140
    )

# --- SEÇÃO 3: CONFIGURAÇÕES DO ALGORITMO ---
st.subheader("3. Configurações da Divisão")
col_conf1, col_conf2 = st.columns(2)

with col_conf1:
    prioridade_escolha = st.radio(
        "Critério Principal de Prioridade:",
        options=[
            "📍 Priorizar Local de Estágio (Balanceia IFFar, Outros IFs, etc.)",
            "🏫 Priorizar Agrupamento por Campus (Reduz a quantidade de campi por prof.)"
        ]
    )

with col_conf2:
    flexibilidade_escolha = st.radio(
        "Flexibilidade na Quantidade de Alunos:",
        options=[
            "⚖️ Divisão Exata (Diferença máxima de 1 aluno entre professores)",
            "🔄 Flexível (Até ~3 alunos de diferença para otimizar os agrupamentos)"
        ]
    )

# Identificadores booleanos para o algoritmo
is_prioridade_local = "Local" in prioridade_escolha
is_flexivel = "Flexível" in flexibilidade_escolha

# --- LÓGICA DE PROCESSAMENTO ---
if st.button("Realizar Divisão", type="primary"):
    if not file_participantes or not file_enquete:
        st.error("Por favor, faça o upload dos dois arquivos CSV.")
    else:
        try:
            df_part = carregar_csv(file_participantes)
            df_enq = carregar_csv(file_enquete)

            # Identificação segura das colunas
            col_email_part_lista = [
                c for c in df_part.columns if 'email' in c.lower() or 'e-mail' in c.lower()]
            col_email_enq_lista = [
                c for c in df_enq.columns if 'email' in c.lower() or 'e-mail' in c.lower()]
            col_escolha_lista = [
                c for c in df_enq.columns if 'escolha' in c.lower() or 'institui' in c.lower()]
            col_grupo_lista = [
                c for c in df_part.columns if 'grupo' in c.lower() or 'campus' in c.lower()]

            if not col_email_part_lista:
                raise ValueError(
                    "Coluna de E-mail não encontrada na Planilha de Participantes.")
            if not col_email_enq_lista:
                raise ValueError("Coluna de E-mail não encontrada na Enquete.")
            if not col_escolha_lista:
                raise ValueError(
                    "Coluna de Escolha de local não encontrada na Enquete.")
            if not col_grupo_lista:
                raise ValueError(
                    "Coluna de Grupo/Campus não encontrada nos Participantes.")

            col_email_part = col_email_part_lista[0]
            col_email_enq = col_email_enq_lista[0]
            col_escolha = col_escolha_lista[-1]
            col_grupo = col_grupo_lista[0]

            df_enq_clean = df_enq[[col_email_enq, col_escolha]].copy()
            df_enq_clean.rename(
                columns={col_email_enq: 'Email', col_escolha: 'Local_Estagio_Raw'}, inplace=True)
            df_enq_clean['Email'] = df_enq_clean['Email'].str.lower().str.strip()

            df_alunos = df_part.copy()
            df_alunos.rename(
                columns={col_email_part: 'Email', col_grupo: 'Campus_Aluno'}, inplace=True)
            df_alunos['Email'] = df_alunos['Email'].str.lower().str.strip()

            df_final = pd.merge(df_alunos, df_enq_clean,
                                on='Email', how='left')
            df_final['Local_Estagio_Raw'] = df_final['Local_Estagio_Raw'].fillna(
                'Não informado')

            def classificar_estagio(texto):
                texto = str(texto).lower()
                if 'iffar' in texto or 'campus' in texto:
                    return 'IFFar'
                if 'outro instituto' in texto or 'outro if' in texto:
                    return 'Outro IF'
                if 'outras' in texto:
                    return 'Outras instituições'
                return 'Não informado'

            df_final['Local_Estagio'] = df_final['Local_Estagio_Raw'].apply(
                classificar_estagio)

            ordem_estagio = {'IFFar': 1, 'Outro IF': 2,
                             'Outras instituições': 3, 'Não informado': 4}
            df_final['Ordem_Prioridade'] = df_final['Local_Estagio'].map(
                ordem_estagio)

            professores = []
            for linha in professores_input.split('\n'):
                if '-' in linha:
                    nome, campus = linha.split('-', 1)
                    professores.append(
                        {'Professor': nome.strip(), 'Campus_Prof': campus.strip()})

            if len(professores) == 0:
                st.error("Nenhum professor válido inserido.")
                st.stop()

            num_profs = len(professores)
            num_alunos = len(df_final)

            # --- CÁLCULO DE CAPACIDADE (Flexível ou Exato) ---
            professores_ordenados_capacidade = sorted(
                professores,
                key=lambda p: 0 if "REITORIA" in p['Campus_Prof'].upper(
                ) else 1
            )

            base_cap = num_alunos // num_profs
            resto = num_alunos % num_profs

            # Se for flexível, damos uma margem de +2 na capacidade máxima de cada professor
            # Isso permite que um professor pegue 2 alunos a mais para não quebrar um grupo do mesmo campus
            margem_flex = 2 if is_flexivel else 0

            capacidades_maximas = {}
            for i, p in enumerate(professores_ordenados_capacidade):
                cota_exata = base_cap + 1 if i < resto else base_cap
                capacidades_maximas[p['Professor']] = cota_exata + margem_flex

            # --- ORDENAÇÃO DINÂMICA DA PLANILHA ---
            if is_prioridade_local:
                df_final = df_final.sort_values(
                    by=['Ordem_Prioridade', 'Campus_Aluno']).reset_index(drop=True)
            else:
                # Se a prioridade for Campus, agrupa primeiro os alunos do mesmo campus na fila de processamento
                df_final = df_final.sort_values(
                    by=['Campus_Aluno', 'Ordem_Prioridade']).reset_index(drop=True)

            # --- ALGORITMO ---
            alocacoes = []
            prof_counts = {p['Professor']: 0 for p in professores}
            prof_tipos = {p['Professor']: {'IFFar': 0, 'Outro IF': 0,
                                           'Outras instituições': 0, 'Não informado': 0} for p in professores}
            prof_campi_alocados = {p['Professor']: set() for p in professores}

            for index, aluno in df_final.iterrows():
                campus_aluno = str(aluno['Campus_Aluno']).upper().strip()
                tipo_cat = aluno['Local_Estagio']

                candidatos = []

                for p in professores:
                    nome_p = p['Professor']
                    campus_p = str(p['Campus_Prof']).upper().strip()

                    if prof_counts[nome_p] < capacidades_maximas[nome_p]:
                        pontuacao = 0

                        if is_prioridade_local:
                            # PESOS FOCADOS EM BALANCEAR LOCAL DE ESTÁGIO
                            pontuacao -= prof_tipos[nome_p][tipo_cat] * 1000
                            if "REITORIA" not in campus_p and (campus_p in campus_aluno or campus_aluno in campus_p):
                                pontuacao += 50
                            if campus_aluno in prof_campi_alocados[nome_p]:
                                pontuacao += 15
                            else:
                                pontuacao -= len(
                                    prof_campi_alocados[nome_p]) * 5

                        else:
                            # PESOS FOCADOS EM AGRUPAR CAMPI (Minimizar campi diferentes por professor)
                            if "REITORIA" not in campus_p and (campus_p in campus_aluno or campus_aluno in campus_p):
                                pontuacao += 1000  # Professor do mesmo campus ganha a preferência absoluta

                            if campus_aluno in prof_campi_alocados[nome_p]:
                                pontuacao += 800   # Bônus gigante se o professor JÁ tiver alunos desse campus
                            else:
                                # Penalidade monstruosa por abrir novo campus
                                pontuacao -= len(
                                    prof_campi_alocados[nome_p]) * 500

                            # Local do estágio vira critério secundário
                            pontuacao -= prof_tipos[nome_p][tipo_cat] * 10

                        is_reitoria = 0 if "REITORIA" in campus_p else 1
                        candidatos.append(
                            (pontuacao, prof_counts[nome_p], is_reitoria, nome_p))

                candidatos.sort(key=lambda x: (-x[0], x[1], x[2]))
                prof_escolhido = candidatos[0][3]

                alocacoes.append(prof_escolhido)
                prof_counts[prof_escolhido] += 1
                prof_tipos[prof_escolhido][tipo_cat] += 1
                prof_campi_alocados[prof_escolhido].add(campus_aluno)

            df_final['Professor_Orientador'] = alocacoes

            # --- RESULTADOS DA DISTRIBUIÇÃO ---
            st.divider()
            st.success("✅ Divisão realizada com sucesso!")

            resumo_detalhado = []
            for p in professores:
                nome_p = p['Professor']
                # Atualiza a string de cota para mostrar o limite usado na rodada
                limite_rodada = capacidades_maximas[nome_p]
                resumo_detalhado.append({
                    'Professor': nome_p,
                    'Total Alunos (Limite)': f"{prof_counts[nome_p]} / {limite_rodada}",
                    'Qtd Campi Diferentes': len(prof_campi_alocados[nome_p]),
                    'IFFar': prof_tipos[nome_p]['IFFar'],
                    'Outro IF': prof_tipos[nome_p]['Outro IF'],
                    'Outras Instituições': prof_tipos[nome_p]['Outras instituições'],
                    'Não Informado': prof_tipos[nome_p]['Não informado']
                })

            df_resumo_detalhado = pd.DataFrame(resumo_detalhado)

            st.subheader("Total por Professor (Detalhado)")
            st.dataframe(df_resumo_detalhado,
                         use_container_width=True, hide_index=True)

            st.subheader("Distribuição: Professor x Campus")
            cruzamento = pd.crosstab(
                df_final['Professor_Orientador'], df_final['Campus_Aluno'])
            st.dataframe(cruzamento, use_container_width=True)

            df_final_display = df_final.drop(columns=['Ordem_Prioridade'])

            # --- EXPORTAÇÃO ---
            csv = df_final_display.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Baixar Resultado Completo (.csv)",
                data=csv,
                file_name='alocacao_estagios_iffar_finalizada.csv',
                mime='text/csv',
                type='primary'
            )

        except ValueError as ve:
            st.warning(f"Aviso de leitura de colunas: {ve}")
        except Exception as e:
            st.error(
                f"Ocorreu um erro ao processar os arquivos. Detalhes: {e}")
