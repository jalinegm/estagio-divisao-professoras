import streamlit as st
import pandas as pd
import unicodedata


def normalizar(texto):
    return unicodedata.normalize('NFKD', str(texto)) \
        .encode('ASCII', 'ignore') \
        .decode('ASCII') \
        .upper() \
        .strip()


st.set_page_config(page_title="Alocação de Estágios - IFFar", layout="wide")

st.title("🎓 Sistema de Alocação de Orientandos de Estágio")
st.markdown("Faça o upload dos arquivos, insira os professores e realize a divisão automática conforme os critérios.")


def carregar_csv(arquivo):
    try:
        return pd.read_csv(arquivo, encoding='utf-8', sep=None, engine='python')
    except UnicodeDecodeError:
        arquivo.seek(0)
        return pd.read_csv(arquivo, encoding='latin-1', sep=None, engine='python')


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
Cátia Keske - Panambi, Santo Augusto, Alegrete, Jaguari
Fabricia Sônego - Reitoria
Jaline Mombach - Reitoria
Janete Maria de Conto - Reitoria
Jiani Cardoso da Roza - Alegrete
Luthiane Miszak de Oliveira - Santo Ângelo
Marcele Ravasio - Santo Ângelo"""

    professores_input = st.text_area(
        "Insira os professores (Nome - Campus 1, Campus 2...), um por linha:",
        value=professores_default,
        height=200
    )

st.subheader("3. Configurações da Divisão")
col_cfg1, col_cfg2 = st.columns(2)
with col_cfg1:
    MAX_DIFERENCA = st.number_input(
        "Diferença máxima de alunos entre professores:",
        min_value=0, max_value=10, value=2, step=1
    )
with col_cfg2:
    MAX_CAMPI_POR_PROF = st.number_input(
        "Número máximo de campi diferentes por professor:",
        min_value=1, max_value=10, value=3, step=1
    )

st.info(
    "**Critérios aplicados automaticamente:**\n"
    "- Divisão separada e proporcional por categoria: IFFar, Não Informado e Outros (Outro IF + Outra Instituição)\n"
    "- Professor alocado preferencialmente ao(s) campus(i) que trabalha\n"
    f"- Diferença máxima de **{MAX_DIFERENCA}** alunos entre professores\n"
    f"- Máximo de **{MAX_CAMPI_POR_PROF}** campi diferentes por professor"
)

if st.button("Realizar Divisão", type="primary"):
    if not file_participantes or not file_enquete:
        st.error("Por favor, faça o upload dos dois arquivos CSV.")
    else:
        try:
            df_part = carregar_csv(file_participantes)
            df_enq = carregar_csv(file_enquete)

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
                t = str(texto).strip()
                if pd.isna(texto) or t == '' or t == 'Nenhuma resposta' or 'não informado' in t.lower():
                    return 'Não informado'
                if t == 'Campus do IFFar':
                    return 'IFFar'
                return 'Outros'

            df_final['Local_Estagio'] = df_final['Local_Estagio_Raw'].apply(
                classificar_estagio)

            # --- ESTATÍSTICAS GERAIS ---
            st.subheader("📊 Estatísticas Gerais da Turma")
            stats = df_final['Local_Estagio'].value_counts()
            st.metric("Total de Alunos", len(df_final))
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Campus IFFar", stats.get('IFFar', 0))
            col2.metric("Não Informado", stats.get('Não informado', 0))
            col3.metric("Outros", stats.get('Outros', 0))
            col4.metric(
                "% Não Informado", f"{stats.get('Não informado', 0)/len(df_final)*100:.1f}%")

            # --- PARSE DOS PROFESSORES ---
            professores = []
            for linha in professores_input.strip().split('\n'):
                linha = linha.strip()
                if '-' in linha:
                    nome, campi_str = linha.split('-', 1)
                    campi_lista = [normalizar(c) for c in campi_str.split(',')]
                    is_reitoria = any('REITORIA' in normalizar(c)
                                      for c in campi_str.split(','))
                    professores.append({
                        'Professor':   nome.strip(),
                        'Campi_Lista': campi_lista,
                        'is_reitoria': is_reitoria,
                    })

            if not professores:
                st.error("Nenhum professor válido inserido.")
                st.stop()

            num_profs = len(professores)
            categorias = ['IFFar', 'Não informado', 'Outros']
            grupos = {
                cat: df_final[df_final['Local_Estagio'] == cat].copy() for cat in categorias}

            # cotas por categoria + ajuste global
            cotas = {p['Professor']: {cat: 0 for cat in categorias}
                     for p in professores}
            for cat in categorias:
                n_cat = len(grupos[cat])
                base = n_cat // num_profs
                resto = n_cat % num_profs
                for i, p in enumerate(professores):
                    cotas[p['Professor']][cat] = base + (1 if i < resto else 0)

            totais_cota = {p['Professor']: sum(
                cotas[p['Professor']][c] for c in categorias) for p in professores}
            dif_cotas = max(totais_cota.values()) - min(totais_cota.values())

            if dif_cotas > MAX_DIFERENCA:
                num_alunos = len(df_final)
                base_total = num_alunos // num_profs
                resto_total = num_alunos % num_profs
                cap_alvo = {p['Professor']: base_total + (1 if i < resto_total else 0)
                            for i, p in enumerate(professores)}
                for p in professores:
                    nome_p = p['Professor']
                    total_atual = sum(cotas[nome_p][c] for c in categorias)
                    diff = cap_alvo[nome_p] - total_atual
                    cotas[nome_p]['Outros'] = max(
                        0, cotas[nome_p]['Outros'] + diff)

            # alocação greedy por categoria
            prof_counts = {p['Professor']: 0 for p in professores}
            prof_cat_counts = {p['Professor']: {
                cat: 0 for cat in categorias} for p in professores}
            prof_campi = {p['Professor']: set() for p in professores}
            alocacoes_idx = {}

            for cat in categorias:
                df_cat = grupos[cat].copy().sort_values(
                    by='Campus_Aluno').reset_index()

                for _, aluno in df_cat.iterrows():
                    campus_aluno = normalizar(aluno['Campus_Aluno'])
                    orig_idx = aluno['index']

                    candidatos = []
                    for p in professores:
                        nome_p = p['Professor']

                        if prof_cat_counts[nome_p][cat] >= cotas[nome_p][cat]:
                            continue

                        campi_alocados = prof_campi[nome_p]
                        novo_campus = campus_aluno not in campi_alocados
                        bloqueado = novo_campus and len(
                            campi_alocados) >= MAX_CAMPI_POR_PROF

                        match_campus = campus_aluno in p['Campi_Lista']

                        pontuacao = 0
                        if not p['is_reitoria']:
                            pontuacao += 10000 if match_campus else -10000

                        if not novo_campus:
                            pontuacao += 100
                        if bloqueado:
                            pontuacao -= 500

                        candidatos.append(
                            (pontuacao, prof_counts[nome_p], nome_p, bloqueado))

                    if not candidatos:
                        st.error(
                            f"Não foi possível alocar o aluno {aluno.get('Email', orig_idx)}.")
                        st.stop()

                    nao_bloqueados = [c for c in candidatos if not c[3]]
                    pool = nao_bloqueados if nao_bloqueados else candidatos
                    pool.sort(key=lambda x: (-x[0], x[1]))
                    prof_escolhido = pool[0][2]

                    prof_counts[prof_escolhido] += 1
                    prof_cat_counts[prof_escolhido][cat] += 1
                    prof_campi[prof_escolhido].add(campus_aluno)
                    alocacoes_idx[orig_idx] = prof_escolhido

            df_final['Professor_Orientador'] = df_final.index.map(
                alocacoes_idx)

            st.divider()
            totais = list(prof_counts.values())
            dif_real = max(totais) - min(totais)
            if dif_real > MAX_DIFERENCA:
                st.warning(
                    f"⚠️ Diferença máxima entre professores: {dif_real} alunos (limite: {MAX_DIFERENCA}).")
            else:
                st.success(
                    f"✅ Divisão realizada! Diferença máxima entre professores: {dif_real} aluno(s).")

            resumo = []
            for p in professores:
                nome_p = p['Professor']
                resumo.append({
                    'Professor':               nome_p,
                    'Total Alunos':            prof_counts[nome_p],
                    'Qtd Campi Diferentes':    len(prof_campi[nome_p]),
                    'Campi Alocados':          ', '.join(sorted(prof_campi[nome_p])),
                    'IFFar':                   prof_cat_counts[nome_p]['IFFar'],
                    'Não Informado':           prof_cat_counts[nome_p]['Não informado'],
                    'Outros (Outro IF/Inst.)': prof_cat_counts[nome_p]['Outros'],
                })

            st.subheader("Resumo por Professor")
            st.dataframe(pd.DataFrame(resumo),
                         use_container_width=True, hide_index=True)

            st.subheader("Distribuição: Professor × Campus")
            st.dataframe(pd.crosstab(df_final['Professor_Orientador'], df_final['Campus_Aluno']),
                         use_container_width=True)

            csv = df_final.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Baixar Resultado Completo (.csv)",
                data=csv,
                file_name='alocacao_estagios_iffar.csv',
                mime='text/csv',
                type='primary'
            )

        except ValueError as ve:
            st.warning(f"Aviso de leitura de colunas: {ve}")
        except Exception as e:
            st.error(
                f"Ocorreu um erro ao processar os arquivos. Detalhes: {e}")
