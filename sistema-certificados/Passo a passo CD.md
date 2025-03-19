# Sistema de Certificados - Carreta Digital

Este sistema permite gerenciar e consultar certificados emitidos pelo programa Carreta Digital através de uma interface web simples. Os usuários podem buscar seus certificados utilizando o CPF e fazer o download dos mesmos.

## Requisitos

- Docker (versão 19.03 ou superior)
- Docker Compose (versão 1.27 ou superior)

## Estrutura do Projeto

O sistema é composto por:
- Aplicação web em Flask
- Banco de dados PostgreSQL
- Scripts de importação e gerenciamento de dados

## Passo a Passo para Instalação e Execução

### 1. Preparação Inicial

1. Clone ou copie todos os arquivos do repositório para sua máquina
   ```
   git clone [URL_DO_REPOSITORIO] sistema-certificados
   ```
   ou descompacte o arquivo ZIP recebido

2. Navegue até o diretório do projeto
   ```
   cd sistema-certificados
   ```

3. Crie uma pasta para os dados (se não existir)
   ```
   mkdir -p data
   ```

4. Coloque o arquivo CSV com os dados dos certificados na pasta `data` com o nome `base_dados.csv`

### 2. Configuração dos Permissões

1. Torne o script de entrada executável
   ```
   chmod +x entrypoint.sh
   ```

### 3. Inicialização dos Contêineres

1. Inicie os contêineres Docker
   ```
   docker-compose up -d
   ```

2. Verifique se os contêineres estão rodando corretamente
   ```
   docker-compose ps
   ```
   Você deve ver dois contêineres ativos: `db` e `web`

### 4. Preparação do Banco de Dados

1. Aguarde cerca de 30 segundos para o PostgreSQL inicializar completamente

2. Verifique a conexão com o banco de dados
   ```
   docker-compose exec web python test_db.py
   ```
   Deve mostrar "Conexão bem-sucedida!"

3. Crie a estrutura do banco de dados
   ```
   docker-compose exec web python recriar_tabela.py
   ```

4. Importe os dados do arquivo CSV para o banco
   ```
   docker-compose exec web python custom_import.py
   ```
   Este comando processará o arquivo CSV e importará os dados para o banco

### 5. Acesso à Aplicação

1. Acesse a aplicação através do navegador:
   ```
   http://localhost:5000
   ```

2. A página inicial mostrará a interface de busca de certificados

### 6. Solução de Problemas (se necessário)

Se encontrar problemas com a exibição de múltiplos certificados para um mesmo CPF:

1. Execute o script de correção
   ```
   docker-compose exec web python fix_multicerts.py
   ```

2. Reinicie a aplicação web
   ```
   docker-compose restart web
   ```

## Comandos Úteis

- Para verificar os logs da aplicação:
  ```
  docker-compose logs web
  ```

- Para verificar os logs do banco de dados:
  ```
  docker-compose logs db
  ```

- Para parar a aplicação:
  ```
  docker-compose down
  ```

- Para reiniciar a aplicação:
  ```
  docker-compose restart
  ```

## Solução de Problemas Comuns

### Erro de permissão no entrypoint.sh
- Solução: Execute `chmod +x entrypoint.sh` no sistema hospedeiro

### Banco de dados não está acessível
- Solução: Espere mais tempo para a inicialização ou reinicie os contêineres com `docker-compose restart`

### Não consegue visualizar todos os certificados
- Solução: Execute o script `fix_multicerts.py` como descrito acima

### Erro ao importar os dados
- Verifique se o arquivo CSV está no formato correto
- Verifique se o arquivo CSV está no diretório `data/` com o nome `base_dados.csv`

### A aplicação não abre no navegador
- Verifique se a porta 5000 está disponível no sistema hospedeiro
- Verifique se os contêineres estão rodando com `docker-compose ps`
- Verifique os logs com `docker-compose logs web`

## Estrutura dos Dados

O sistema espera um arquivo CSV com os seguintes campos:
- Nome: Nome completo do aluno
- CPF: CPF do aluno
- Curso: Nome do curso realizado
- LINK DRIVE ou Certificado: Link para o certificado
- ESTADO: Estado onde o curso foi realizado (opcional)
- Data de Adesão: Data de adesão ao programa (opcional)
- Escola: Instituição de ensino (opcional)

## Observações Importantes

- Cada aluno (CPF) pode ter múltiplos certificados
- O sistema normaliza o CPF automaticamente para o formato XXX.XXX.XXX-XX
- Os links do Google Drive são convertidos para links diretos de download
