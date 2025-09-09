# Cotações AI: Assistente Inteligente para Cotações de Frete

![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)
![Redis](https://img.shields.io/badge/Redis-7.0-red?style=for-the-badge&logo=redis)
![Ollama](https://img.shields.io/badge/Ollama-Llama3-lightgrey?style=for-the-badge&logo=ollama)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Cotações AI** é um sistema automatizado para processar pedidos de cotação de frete recebidos por e-mail. Utilizando um modelo de linguagem local (LLM) para interpretação de texto e uma arquitetura de filas para processamento assíncrono, o sistema oferece uma solução eficiente, privada e escalável.

---

## 🏛️ Arquitetura e Fluxo de Trabalho

O sistema adota o padrão **Produtor/Consumidor** para garantir desacoplamento e escalabilidade. O fluxo de trabalho é o seguinte:

```mermaid
graph TD
    A -->|📧 E-mail Recebido| B{main.py (Produtor)}
    B --> |Enfileira Tarefa| C[🔄 Redis (Fila de Tarefas)]
    C --> |Consome Tarefa| D[👷 rq worker (Consumidor)]
    D --> E(1. Análise com IA)
    E --> F(2. Cálculo de Cotação)
    F --> G(3. Envio de Resposta)
    G --> H[✅ E-mail Enviado ao Cliente]
```

1.  **Produtor (`main.py`)**: Monitoriza a caixa de entrada, identifica e-mails de cotação e enfileira uma tarefa no Redis para cada um.
2.  **Fila (Redis)**: Atua como *message broker*, armazenando as tarefas de forma persistente.
3.  **Consumidor (`rq worker`)**: Processa as tarefas da fila, orquestrando a análise do e-mail, o cálculo da cotação e o envio da resposta.

---

## ✨ Funcionalidades Principais

- **Processamento Assíncrono**: Utiliza **Redis** e **RQ (Redis Queue)** para gerir tarefas em segundo plano, permitindo que o sistema processe múltiplos e-mails em paralelo.
- **IA Local e Privada**: Emprega o **Ollama** para executar o modelo **Llama 3** localmente, garantindo que os dados dos e-mails nunca saiam da sua infraestrutura.
- **Extração e Normalização Robusta de Dados**: Utiliza um LLM para extrair dados brutos (destino, peso, volume, tipo de transporte, temperatura) e funções Python para:
  -  **Normalização de Peso e Volume (melhorada)**: Converte formatos variados para unidades padrão (kg e m³), incluindo:
     - Volumes diretos: "45 m3", "0,42 m³", "0.42 m^3".
     - Dimensões: "112x47x80 cm", "3 x 3 x 5 m", mistos como "3m x 3 x 5m".
     - Tratamento correto de unidades finais com espaço (ex.: "... 80 cm" aplica-se às 3 dimensões).
  -  **Destino (agora sem fuzzy matching)**: O destino extraído é mantido exatamente como no e-mail (apenas normalizado para minúsculas). Há uma regra explícita para mapear "Aeroporto de Lisboa/Lisboa Aeroporto" para "Lisboa". Caso não exista correspondência exata na tabela de preços, a lógica de fallback acontece no `cotador.py` via API (ver abaixo).
- **Cálculo Otimizado**: Consulta uma tabela de preços em CSV (`tabela_precos.csv`) para encontrar a tarifa mais económica que corresponda aos requisitos do pedido.
- **Fallback por Distância (Novo)**: Se não houver entrada exata na tabela para o destino, o sistema usa geocoding do destino e distância de condução a partir de "Lisboa, Portugal" e calcula o preço por km (detalhes na seção abaixo).
- **Respostas Automáticas**: Envia um e-mail de resposta profissional, formatado em HTML, com os detalhes da cotação.
- **Logging Detalhado**: Regista todas as operações e erros em `app.log` para fácil monitorização e depuração, com a opção de ativar nível `DEBUG` para depuração profunda.
- **RAG Local (Opcional)**: Integração com **ChromaDB + LlamaIndex** para consulta de exemplos internos (e-mails/cotações anteriores) e melhoria de extrações. Persistência em `./rag_test_db`. Embeddings forçados a **CPU**. Se as dependências não estiverem disponíveis, existe fallback automático para um modo em memória (sem fuzzy matching), mantendo a mesma API.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem**: Python 3.13
- **IA e LLM**: Ollama (com Llama 3)
- **Fila de Mensagens**: Redis, RQ (Redis Queue)
- **Manipulação de Dados**: Pandas
- **Gestão de Dependências**: Pip, `requirements.txt`
- **Variáveis de Ambiente**: `python-dotenv`
- **RAG**: ChromaDB (persistente local) + LlamaIndex (camada de indexação/consulta) + Sentence-Transformers (embeddings locais) [opcional, com fallback em memória]
- **Fallback de distância**: Nominatim (Geocoding via HTTP) + OSRM (Driving distance) via `requests` (sem chave de API)

---

## 🚀 Guia de Instalação e Execução

Siga estes passos para configurar e executar o projeto.

### 1. Pré-requisitos

- Python 3.8 ou superior
- Git
- **Redis**: A correr localmente. [Ver opções de instalação](#3-configuração-do-redis).
- **Ollama**: Instalado e em execução. Visite [ollama.com](https://ollama.com/) para descarregar.

### 2. Instalação do Projeto

```bash
# 1. Clone o repositório
git clone <URL_DO_REPOSITORIO>
cd Cotaçoes_AI

# 2. Crie e ative um ambiente virtual
python3 -m venv venv
source venv/bin/activate
# No Windows: venv\Scripts\activate

# 3. Instale as dependências mínimas
pip install -r requirements.txt

# 4. Descarregue o modelo de IA (com o Ollama a correr)
ollama pull llama3
```

Observações:
- O RAG completo (ChromaDB/LlamaIndex + embeddings) é opcional. Caso não o instale, o sistema usa um fallback em memória para a parte de similaridade.
- Para instalar o RAG completo em Python 3.13 (CPU), pode usar:

```bash
# PyTorch (CPU wheels)
pip install -U torch --index-url https://download.pytorch.org/whl/cpu

# Transformers + Sentence-Transformers
pip install -U transformers
pip install -U sentence-transformers

# ChromaDB e LlamaIndex
pip install -U chromadb
pip install -U llama-index llama-index-vector-stores-chroma llama-index-embeddings-huggingface
```

### 3. Configuração do Redis

- **Docker (Recomendado)**:
  ```bash
  docker run -d -p 6379:6379 --name cotacoes-redis redis
  ```
- **Homebrew (macOS)**:
  ```bash
  brew install redis && brew services start redis
  ```

### 4. Variáveis de Ambiente

Crie um ficheiro `.env` a partir do exemplo e preencha as suas credenciais.

```bash
cp .env.example .env
```

- `EMAIL_USUARIO`: O e-mail que o sistema usará.
- `EMAIL_SENHA`: **Senha de aplicação** do e-mail (para o Gmail, não use a senha principal).
- `EMAIL_SERVIDOR`: Servidor IMAP (ex: `imap.gmail.com`).
- `SMTP_SERVIDOR`: Servidor SMTP (ex: `smtp.gmail.com`).

### 5. Tabela de Preços

Por motivos de privacidade, a tabela de preços não é partilhada no repositório. Crie a sua a partir do ficheiro de exemplo:

```bash
cp tabela_precos.example.csv tabela_precos.csv
```

Depois, edite `tabela_precos.csv` com as suas próprias tarifas.

### 6. Execução

Abra **dois terminais** no diretório do projeto.

- **Terminal 1: Inicie o Worker**
  ```bash
  # Ative o ambiente virtual: source venv/bin/activate
  # macOS (recomendado para evitar crashes do Metal/MPS em processos forkados)
  export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
  export PYTORCH_ENABLE_MPS_FALLBACK=1
  export CUDA_VISIBLE_DEVICES=""
  rq worker
  ```

- **Terminal 2: Execute o Produtor**
  ```bash
  # Ative o ambiente virtual: source venv/bin/activate
  python3 main.py
```

O produtor irá ler os e-mails e enfileirar as tarefas, que serão processadas pelo worker.

#### Execução do pipeline RAG (Demo Local)

Para experimentar a base vetorial local com exemplos fictícios:

```bash
python3 rag_pipeline_test.py
```

Este script irá:
- Persistir documentos de exemplo no `./rag_test_db`
- Executar consultas e imprimir os resultados mais relevantes

### 7. Modo de Teste (Simulação de E-mails)

Para testar o fluxo completo sem interagir com servidores de e-mail reais (IMAP/SMTP) ou a necessidade de e-mails em tempo real, pode ativar o `APP_TEST_MODE`.

1.  **Modificar `email_reader.py`**: A função `obter_emails()` retornará um e-mail de teste hardcoded.
2.  **Modificar `email_sender.py`**: A função `enviar_email_cotacao()` registará o HTML completo do e-mail de resposta no log, em vez de enviá-lo.

Para executar no modo de teste, abra **dois terminais** no diretório do projeto e, em AMBOS os terminais, antes de ativar o ambiente virtual, defina a variável de ambiente:

```bash
export APP_TEST_MODE=true
# Para macOS, no terminal do worker, adicione também:
# export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```

Depois, siga os passos de `6. Execução` acima. No log do `rq worker`, procure por `HTML gerado (simulado):` para ver o conteúdo HTML da resposta do e-mail.

**Dica de Depuração**: Para ver logs mais detalhados, incluindo o processo de normalização e fuzzy matching, pode alterar o nível do logger para `DEBUG` em `logger_config.py` (linha `9`):

```python
# logger_config.py
logger.setLevel(logging.DEBUG)
```

---

## 🔍 RAG Local (ChromaDB + LlamaIndex)

Esta integração permite que o sistema consulte exemplos anteriores para dar contexto ao LLM e melhorar a extração (especialmente em destinos ambíguos como aeroportos ou regiões próximas).

- **Persistência**: `./rag_test_db` (pasta local)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (100% local), executados em **CPU** para maior compatibilidade.
- **Módulo**: `rag_store.py`
  - `ingest_email(email_text: str, metadata: dict) -> str`
  - `retrieve_similar(query_text: str, top_k: int = 3) -> list[dict]`
- **Demo/seed**: `rag_pipeline_test.py`
- **Testes**: `tests/test_rag_pipeline.py`

### Como o RAG é usado no pipeline real

- `agent.py/analisar_email()`
  - Recupera contexto via `retrieve_similar(corpo_email, top_k=3)`
  - Injeta esse contexto no prompt do LLM (Ollama/Llama3) antes da extração

- `tasks.py/processar_email_task()`
  - Após envio do e-mail com sucesso, persiste o exemplo no vector store via `ingest_email()` com metadados úteis (`destino`, `peso`, `volume`, `temperatura`, `tipo_transporte`)

### Variáveis de ambiente (sugestão)

Opcionalmente, pode controlar o uso do RAG com uma flag (ainda não obrigatória):

```
RAG_ENABLED=true
```

Se desativado ou se as dependências não estiverem instaladas, o módulo `rag_store.py` ativa automaticamente um fallback em memória que mantém a mesma API (similaridade simples por sobreposição de palavras).

---

## 🚚 Fallback de Preço por Distância (Nominatim + OSRM)

Quando o destino extraído não existir exatamente na `tabela_precos.csv`, o `cotador.py` executa o seguinte:

- Geocoding do destino e da origem fixa "Lisboa, Portugal" usando Nominatim via HTTP.
- Cálculo da distância de condução usando o endpoint público do OSRM.
- Cálculo do preço por km com base em faixas configuráveis em ficheiro privado.

Requisitos: apenas `requests`. Não é necessária chave de API. O pedido inclui um header `User-Agent` conforme recomendado pelo Nominatim.

### Configuração Privada de Preços por Km

Os valores das faixas são confidenciais e não devem ser commitados no repositório. Use um ficheiro gitignored `pricing_config.json` com a seguinte estrutura:

```json
[
  {
    "peso_max": 500,
    "volume_max": 2,
    "tarifa_eur_km": 0.0,
    "tipo_transporte": "carro (<500Kg/<2M3)"
  }
  // ... adicione as restantes faixas
]
```

Passos recomendados:
- Copie o exemplo e preencha com os valores reais (não commit):
  ```bash
  cp pricing_config.example.json pricing_config.json
  ```
- Opcionalmente, aponte para outro caminho via variável de ambiente `PRICING_CONFIG_PATH`.

## 🗂️ Estrutura da Tabela de Preços

O ficheiro `tabela_precos.csv` é o coração da lógica de cotação. A sua estrutura deve ser a seguinte:

| Coluna          | Descrição                                         | Exemplo         |
|-----------------|---------------------------------------------------|-----------------|
| `destino`       | Localidade de entrega (minúsculas)                | `lisboa`        |
| `peso_maximo`   | Peso máximo (kg) suportado por esta tarifa        | `1000`          |
| `volume_maximo` | Volume máximo (m³) suportado                      | `10`            |
| `tipo_transporte` | Descrição do serviço                              | `Normal`        |
| `temperatura`   | Condição de transporte (`ambiente` ou `frio`)     | `ambiente`      |
| `preco`         | Custo final do serviço em euros                   | `150.50`        |

---

## 🧰 Troubleshooting

- **macOS: Crash envolvendo Metal/MPS (MPSLibrary ... XPC_ERROR_CONNECTION_INVALID)**
  - Execute o worker com:
    ```bash
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
    export PYTORCH_ENABLE_MPS_FALLBACK=1
    export CUDA_VISIBLE_DEVICES=""
    rq worker
    ```
  - Os embeddings do RAG estão forçados a CPU no código (`rag_store.py`).

- **ImportError: No module named 'chromadb' durante testes**
  - O RAG é opcional. Se não quiser instalar o stack completo, o sistema usa fallback em memória automaticamente.
  - Para instalar o stack completo no Python 3.13 (CPU), siga os comandos da secção de instalação (PyTorch CPU, transformers/sentence-transformers, ChromaDB, LlamaIndex).

- **Geocoding/OSRM**
  - Nominatim é rate-limited. Para uso intensivo, considere cachear resultados ou self-hosting.
  - O OSRM público é best-effort. Para produção, considere self-hosting um servidor OSRM.


## 📜 Licença

Este projeto está licenciado sob a Licença MIT. Consulte o ficheiro `LICENSE` para mais detalhes.