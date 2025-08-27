# Cotações AI – Assistente de Cotações Automatizado

**Cotações AI** é um sistema robusto e escalável desenhado para automatizar completamente o processo de resposta a pedidos de cotação de frete recebidos por e-mail. Utilizando Inteligência Artificial para interpretação de texto e uma arquitetura de filas de mensagens, o sistema garante alta performance, fiabilidade e capacidade de processamento paralelo.

---

## 🧠 Funcionalidades Principais

- 📥 **Leitura Inteligente de E-mails**: Monitoriza uma caixa de entrada via IMAP, identificando e processando apenas e-mails não lidos que contenham palavras-chave relevantes para cotações.
- 🤖 **Extração de Dados com IA**: Emprega a API da OpenAI para analisar o conteúdo de e-mails não estruturados e extrair com precisão informações vitais como destino, peso e volume.
- 📊 **Cálculo de Cotação Otimizado**: Compara os dados extraídos com uma tabela de preços (`tabela_precos.csv`) para encontrar a opção de transporte mais económica que cumpra os requisitos.
- 📤 **Respostas Profissionais e Automáticas**: Envia um e-mail de resposta formatado em HTML ao cliente, contendo todos os detalhes da cotação, incluindo preço e prazo de entrega.
- 🚀 **Arquitetura Escalável e Resiliente**: Construído sobre o padrão Produtor/Consumidor com **Redis** e **RQ (Redis Queue)**, permite o processamento de múltiplos e-mails em paralelo através de *workers* independentes e inclui um sistema de retentativas para tarefas que falhem.
- 📝 **Logging Detalhado**: Regista todas as operações e erros significativos num ficheiro (`app.log`) e no terminal, facilitando o diagnóstico e a monitorização.

---

## ⚙️ Arquitetura e Fluxo de Trabalho

O sistema opera numa arquitetura de **Produtor/Consumidor**, ideal para cargas de trabalho assíncronas e escaláveis.

1.  **O Produtor (`main.py`)**: Atua como o ponto de entrada. Quando executado, ele conecta-se ao servidor de e-mail, lê as mensagens não lidas e filtra as que são relevantes. Para cada e-mail de cotação, ele cria uma **tarefa** e a publica na fila do Redis.

2.  **A Fila (Redis)**: O Redis funciona como um intermediário de mensagens (Message Broker). Ele armazena as tarefas de forma persistente numa fila, garantindo que nenhuma se perca, mesmo que o sistema seja reiniciado.

3.  **Os Consumidores (`rq worker`)**: São processos independentes que se conectam ao Redis e ficam a "escutar" por novas tarefas na fila. Assim que uma tarefa é adicionada, um *worker* disponível a consome e executa a lógica de negócio completa:
    - **Análise**: Chama o `agent.py` para extrair os dados do e-mail.
    - **Cotação**: Usa o `cotador.py` para calcular o preço.
    - **Envio**: Utiliza o `email_sender.py` para enviar a resposta ao cliente.

Esta separação de responsabilidades permite que o sistema seja altamente escalável. Para aumentar a capacidade de processamento, basta iniciar mais instâncias do *worker*.

---

## 📋 Instalação e Configuração

Siga estes passos para configurar e executar o projeto no seu ambiente local.

### 1. Pré-requisitos

- Python 3.8 ou superior
- Git instalado
- Um servidor **Redis** a correr localmente.

### 2. Instalação do Projeto

**Clone o repositório:**
```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd Cotaçoes_AI
```

**Crie e ative um ambiente virtual (recomendado):**
```bash
python3 -m venv venv
source venv/bin/activate
# No Windows, use: venv\Scripts\activate
```

**Instale as dependências:**
```bash
pip install -r requirements.txt
```

### 3. Configuração do Redis

Escolha **uma** das opções abaixo para instalar e executar o Redis.

- **Opção A: Docker (Multiplataforma)**
  ```bash
  docker run -d -p 6379:6379 --name cotacoes-redis redis
  ```

- **Opção B: Homebrew (macOS)**
  ```bash
  brew install redis
  brew services start redis
  ```

### 4. Variáveis de Ambiente

Crie o seu ficheiro de configuração a partir do exemplo:
```bash
cp .env.example .env
```

Abra o ficheiro `.env` e preencha todas as variáveis:

- `OPENAI_API_KEY`: A sua chave secreta da API da OpenAI.
- `EMAIL_USUARIO`: O endereço de e-mail que o sistema usará para ler e enviar mensagens.
- `EMAIL_SENHA`: A **senha de aplicação** para a conta de e-mail. *Nota: Para serviços como o Gmail, é obrigatório gerar uma "Senha de app" específica em vez de usar a sua senha principal.*
- `EMAIL_SERVIDOR`: O endereço do servidor IMAP para leitura (ex: `imap.gmail.com`).
- `EMAIL_PASTA`: A pasta de e-mail a ser monitorizada (ex: `inbox`).
- `SMTP_SERVIDOR`: O endereço do servidor SMTP para envio (ex: `smtp.gmail.com`).
- `SMTP_PORTA`: A porta do servidor SMTP (normalmente `587` para TLS).

---

## 🚀 Executando o Sistema

O sistema requer dois processos a correr em simultâneo. Abra **dois terminais** no diretório do projeto.

**Terminal 1: Inicie o Worker**

Este processo ficará ativo, à espera de tarefas. Para maior capacidade, pode abrir mais terminais e iniciar mais workers.
```bash
rq worker
```

**Terminal 2: Execute o Produtor**

Este script verifica e enfileira os e-mails. Ele executa e termina, mas pode ser agendado (ex: com `cron`) para correr periodicamente.
```bash
python3 main.py
```

Ao executar o `main.py`, verá no terminal do *worker* que a tarefa foi recebida e está a ser processada.

---

## 📁 Estrutura do Projeto

- `main.py`: **Produtor**. Ponto de entrada que lê e-mails e enfileira as tarefas.
- `tasks.py`: **Lógica do Worker**. Contém a função principal que orquestra a análise, cotação e envio.
- `agent.py`: Módulo de **Inteligência Artificial**. Interage com a API da OpenAI.
- `cotador.py`: **Motor de Cotação**. Lê a tabela de preços e calcula o valor do frete.
- `email_reader.py`: **Leitor de E-mails**. Conecta-se ao servidor IMAP e extrai mensagens.
- `email_sender.py`: **Remetente de E-mails**. Formata e envia a resposta via SMTP.
- `logger_config.py`: **Configuração de Logs**. Centraliza as definições de logging para todo o projeto.
- `tabela_precos.csv`: **Base de Dados de Preços**. Contém os dados para o cálculo das cotações.
- `requirements.txt`: Lista de todas as dependências Python.
- `.env.example`: Ficheiro de exemplo para as variáveis de ambiente.
- `app.log`: **Ficheiro de Log**. Gerado automaticamente, regista todas as operações.

---

## 🔧 Configuração e Manutenção

### Tabela de Preços (`tabela_precos.csv`)

A precisão do sistema depende de uma tabela bem configurada. As colunas devem ser:

- `destino`: O nome da localidade (ex: "lisboa", "porto"). Deve estar em minúsculas.
- `peso_maximo` (kg): O peso máximo suportado por esta tarifa.
- `volume_maximo` (m³): O volume máximo suportado.
- `tipo_transporte`: Descrição do serviço (ex: "Normal", "Urgente", "Refrigerado").
- `preco_final`: O custo final do serviço em euros.
- `prazo_entrega`: O tempo de entrega estimado (ex: "24-48 horas").

### Logging e Falhas

- **Logs**: Verifique o ficheiro `app.log` para um histórico detalhado de todas as atividades e para depurar erros.
- **Fila de Falhas (`failed`)**: Se uma tarefa falhar todas as retentativas, o RQ a move para a fila `failed`. Pode usar ferramentas como `rq-dashboard` para inspecionar estas falhas e decidir se as quer reenfileirar ou descartar.

## 📨 Exemplo de Resposta Enviada

```html
<p>Olá,</p>
<p>Com base nas informações fornecidas, a melhor proposta é:</p>
<ul>
  <li><strong>Destino:</strong> Porto</li>
  <li><strong>Tipo de Transporte:</strong> Pequeno</li>
  <li><strong>Peso:</strong> 450kg</li>
  <li><strong>Volume:</strong> 8m³</li>
  <li><strong>Preço:</strong> 250,00€</li>
</ul>
<p>Ficamos ao dispor para qualquer questão adicional.</p>
<p>Melhores cumprimentos,<br><strong>Equipa de Logística</strong></p>
```

---

## 📌 Notas Finais

- O sistema pode ser programado com um **agendador local** (como cron ou Task Scheduler) para execução automática periódica.
- Para aumentar a robustez, pode adicionar logging, tratamento de exceções e histórico de pedidos.

---