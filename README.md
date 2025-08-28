# Cotações AI: Assistente Inteligente para Cotações de Frete

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Redis](https://img.shields.io/badge/Redis-7.0-red?style=for-the-badge&logo=redis)
![Ollama](https://img.shields.io/badge/Ollama-Llama3-lightgrey?style=for-the-badge&logo=ollama)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Cotações AI** é um sistema automatizado para processar pedidos de cotação de frete recebidos por e-mail. Utilizando um modelo de linguagem local (LLM) para interpretação de texto e uma arquitetura de filas para processamento assíncrono, o sistema oferece uma solução eficiente, privada e escalável.

---

## 🏛️ Arquitetura e Fluxo de Trabalho

O sistema adota o padrão **Produtor/Consumidor** para garantir desacoplamento e escalabilidade. O fluxo de trabalho é o seguinte:

```mermaid
graph TD
    A[📧 E-mail Recebido] --> B{main.py (Produtor)}
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
- **Extração de Dados**: Interpreta e-mails não estruturados para extrair informações essenciais: `destino`, `peso`, `volume` e `temperatura` (ambiente ou frio).
- **Cálculo Otimizado**: Consulta uma tabela de preços em CSV (`tabela_precos.csv`) para encontrar a tarifa mais económica que corresponda aos requisitos do pedido.
- **Respostas Automáticas**: Envia um e-mail de resposta profissional, formatado em HTML, com os detalhes da cotação.
- **Logging Detalhado**: Regista todas as operações e erros em `app.log` para fácil monitorização e depuração.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem**: Python 3.8+
- **IA e LLM**: Ollama (com Llama 3)
- **Fila de Mensagens**: Redis, RQ (Redis Queue)
- **Manipulação de Dados**: Pandas
- **Gestão de Dependências**: Pip, `requirements.txt`
- **Variáveis de Ambiente**: `python-dotenv`

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

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Descarregue o modelo de IA (com o Ollama a correr)
ollama pull llama3
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
  rq worker
  ```

- **Terminal 2: Execute o Produtor**
  ```bash
  # Ative o ambiente virtual: source venv/bin/activate
  python3 main.py
  ```

O produtor irá ler os e-mails e enfileirar as tarefas, que serão processadas pelo worker.

---

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

## 📜 Licença

Este projeto está licenciado sob a Licença MIT. Consulte o ficheiro `LICENSE` para mais detalhes.