import csv
import os
import psycopg2
import re

# Configuração do banco de dados
DB_CONFIG = {
    'dbname': 'certificados_db',
    'user': 'certificados_user',
    'password': 'certificados_pwd',
    'host': 'db',
    'port': '5432'
}

def normalizar_cpf(cpf):
    if not cpf:
        return None
    clean_cpf = re.sub(r'\D', '', str(cpf))
    if len(clean_cpf) < 9:
        return None
    if len(clean_cpf) < 11:
        clean_cpf = clean_cpf.zfill(11)
    elif len(clean_cpf) > 11:
        clean_cpf = clean_cpf[:11]
    return f'{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}'

def extract_drive_id(url):
    if not url:
        return None
        
    # Padrão para URLs do Google Drive
    patterns = [
        r'id=([a-zA-Z0-9_-]+)',                # formato ?id=
        r'/d/([a-zA-Z0-9_-]+)',                # formato /d/
        r'drive\.google\.com/file/d/([^/]+)',  # formato completo
        r'drive\.google\.com/open\?id=([^&]+)' # formato open?id=
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def formatar_link_direto(url):
    drive_id = extract_drive_id(url)
    if drive_id:
        return f"https://drive.google.com/uc?export=download&id={drive_id}"
    return url

# Conectar ao banco de dados
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Criar tabela se não existir - MODIFICAÇÃO: Removida restrição UNIQUE do CPF
cur.execute('''
CREATE TABLE IF NOT EXISTS certificados (
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
CREATE INDEX IF NOT EXISTS idx_cpf ON certificados(cpf);
''')
conn.commit()

# Arquivo CSV
arquivo_csv = 'data/base_dados.csv'

# Processar CSV
with open(arquivo_csv, 'r', encoding='utf-8') as f:
    print('Processando CSV...')
    reader = csv.DictReader(f)
    
    # Processo de importação
    registros_validos = 0
    registros_invalidos = 0
    
    for i, row in enumerate(reader):
        try:
            nome = row.get('Nome', '').strip()
            cpf_raw = row.get('CPF', '')
            cpf = normalizar_cpf(cpf_raw)
            curso = row.get('Curso', '').strip()
            
            # Verificar qual coluna tem o link do certificado
            link_raw = None
            if 'LINK DRIVE' in row and row['LINK DRIVE']:
                link_raw = row['LINK DRIVE'].strip()
            elif 'Certificado' in row and row['Certificado']:
                link_raw = row['Certificado'].strip()
            
            link = formatar_link_direto(link_raw) if link_raw else None
            estado = row.get('ESTADO', '').strip()
            data_adesao = row.get('Data de Adesão', '').strip()
            escola = row.get('Escola', '').strip()
            
            # Verificar dados obrigatórios
            if nome and cpf and curso and link:
                try:
                    # Modificação: Usar ON CONFLICT com chave composta (cpf, curso)
                    cur.execute('''
                    INSERT INTO certificados 
                    (nome, curso, cpf, link_certificado, estado, data_adesao, escola)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cpf, curso) DO UPDATE 
                    SET nome = EXCLUDED.nome,
                        link_certificado = EXCLUDED.link_certificado,
                        estado = EXCLUDED.estado,
                        data_adesao = EXCLUDED.data_adesao,
                        escola = EXCLUDED.escola
                    ''', (nome, curso, cpf, link, estado, data_adesao, escola))
                    registros_validos += 1
                    
                    # Commit a cada 100 registros
                    if registros_validos % 100 == 0:
                        conn.commit()
                        print(f'Processados {registros_validos} registros...')
                except Exception as e:
                    registros_invalidos += 1
                    print(f'Erro ao inserir {nome} (CPF: {cpf}, Curso: {curso}): {e}')
            else:
                registros_invalidos += 1
                razoes = []
                if not nome:
                    razoes.append("sem nome")
                if not cpf:
                    razoes.append(f"CPF inválido ({cpf_raw})")
                if not curso:
                    razoes.append("sem curso")
                if not link:
                    razoes.append("sem link de certificado")
                
                print(f'Registro inválido linha {i+2}: {", ".join(razoes)}')
        except Exception as e:
            registros_invalidos += 1
            print(f'Erro ao processar linha {i+2}: {e}')
    
    # Commit final
    conn.commit()
    
    # Verificar total de registros
    cur.execute('SELECT COUNT(*) FROM certificados')
    total = cur.fetchone()[0]
    
    print(f'\nImportação concluída!')
    print(f'Registros válidos importados: {registros_validos}')
    print(f'Registros inválidos: {registros_invalidos}')
    print(f'Total na tabela certificados: {total}')
    
    # Verificar quantos alunos distintos
    cur.execute('SELECT COUNT(DISTINCT cpf) FROM certificados')
    total_alunos = cur.fetchone()[0]
    print(f'Total de alunos distintos: {total_alunos}')
    
    # Verificar alunos com múltiplos certificados
    cur.execute('''
    SELECT cpf, nome, COUNT(*) as total 
    FROM certificados 
    GROUP BY cpf, nome 
    HAVING COUNT(*) > 1 
    ORDER BY total DESC 
    LIMIT 5
    ''')
    alunos_multi = cur.fetchall()
    if alunos_multi:
        print("\nExemplos de alunos com múltiplos certificados:")
        for aluno in alunos_multi:
            print(f"- {aluno[1]} (CPF: {aluno[0]}, Certificados: {aluno[2]})")
            # Mostrar os cursos do aluno
            cur.execute('SELECT curso FROM certificados WHERE cpf = %s', (aluno[0],))
            cursos = [c[0] for c in cur.fetchall()]
            print(f"  Cursos: {', '.join(cursos)}")

# Fechar conexão
cur.close()
conn.close()