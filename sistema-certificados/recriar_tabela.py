import psycopg2

# Configuração do banco de dados
DB_CONFIG = {
    'dbname': 'certificados_db',
    'user': 'certificados_user',
    'password': 'certificados_pwd',
    'host': 'db',
    'port': '5432'
}

print("Conectando ao banco de dados...")
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()
print("Conexão estabelecida com sucesso!")

# Recriar a tabela certificados (apaga a existente e cria uma nova)
print("Recriando tabela de certificados...")

# Drop tabela se existir
cur.execute("DROP TABLE IF EXISTS certificados")
conn.commit()

# Criar nova tabela com a estrutura correta
cur.execute('''
CREATE TABLE certificados (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    curso VARCHAR(255) NOT NULL,
    cpf VARCHAR(14) NOT NULL,
    link_certificado VARCHAR(512) NOT NULL,
    estado VARCHAR(50) DEFAULT '',
    data_adesao VARCHAR(50) DEFAULT '',
    escola VARCHAR(255) DEFAULT '',
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cpf, curso)
);

CREATE INDEX idx_cpf ON certificados(cpf);
CREATE INDEX idx_estado ON certificados(estado);
''')
conn.commit()

print("Tabela recriada com sucesso!")

# Fechar conexão
cur.close()
conn.close()
print("Conexão fechada.")