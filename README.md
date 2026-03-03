# Alocação de Estágios - Formação Pedagógica
🎓 **Sistema Automático de Divisão de Orientandos de Estágio**

App Streamlit para alocar alunos de estágio a professores, garantindo **equidade, proximidade geográfica e limites configuráveis**.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)

## Como Funciona
O sistema processa **duas planilhas CSV**:
- **Participantes do Curso** (export Moodle): Lista de alunos inscritos com campus
- **Enquete de Preferências**: Respostas sobre local desejado de estágio

**Saída**: Planilha `alocacao_estagios_iffar.csv` com professor orientador por aluno

## Critérios Principais
- **Categorias de Estágio** (da enquete):
  | Categoria | Descrição |
  |-----------|-----------|
  | **IFFar** | "Campus do IFFar" |
  | **Não Informado** | Sem resposta / "Nenhuma resposta" |
  | **Outros** | Outro IF ou instituição privada/estadual |

- **Professores**: Cada um com campi associados (ex.: "Cátia Keske - Panambi, Santo Augusto"). Reitoria é curinga
- **Configurações** (ajustáveis no app):
  - Diferença máxima de alunos entre profs: **2**
  - Máx. campi diferentes por prof: **3**

## Algoritmo (Passo a Passo)
1. **Merge e Categorização**: Une planilhas por email e classifica preferências em 3 grupos
2. **Cotas Iniciais**: Divide alunos de cada categoria proporcionalmente pelos professores (ex.: 205 alunos ÷ 10 profs ≈ 20-21 cada)
3. **Ajuste de Equilíbrio**: Corrige cotas "Outros" se diferença total > 2 alunos
4. **Alocação Greedy** (por categoria, alunos ordenados por campus):