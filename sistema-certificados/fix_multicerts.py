import psycopg2
import csv
import re
import os

# Configuração do banco de dados
DB_CONFIG = {
    'dbname': 'certificados_db',
    'user': 'certificados_user',
    'password': 'certificados_pwd',
    'host': 'db',
    'port': '5432'
}

def normalizar_cpf(cpf):
    """Normaliza o formato do CPF"""
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
    """Extrai ID do Google Drive de uma URL"""
    if not url:
        return None
        
    patterns = [
        r'id=([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)',
        r'drive\.google\.com/file/d/([^/]+)',
        r'drive\.google\.com/open\?id=([^&]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def formatar_link_direto(url):
    """Converte links do Drive para formato direto"""
    drive_id = extract_drive_id(url)
    if drive_id:
        return f"https://drive.google.com/uc?export=download&id={drive_id}"
    return url

def recriar_tabela():
    """Recria a tabela certificados com a estrutura correta"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Fazer backup dos dados existentes
    print("Fazendo backup dos dados existentes...")
    try:
        cur.execute("SELECT * FROM certificados")
        certificados_existentes = cur.fetchall()
        
        # Obter nomes de colunas
        colnames = [desc[0] for desc in cur.description]
        print(f"Backup: {len(certificados_existentes)} registros")
    except Exception as e:
        print(f"Erro ao fazer backup: {e}")
        certificados_existentes = []
        colnames = []
    
    # Recriar tabela
    print("Recriando tabela...")
    try:
        cur.execute("DROP TABLE IF EXISTS certificados")
        
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
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_cpf ON certificados(cpf);
        CREATE UNIQUE INDEX idx_cpf_curso ON certificados(cpf, curso);
        ''')
        conn.commit()
        print("Tabela recriada com sucesso!")
    except Exception as e:
        conn.rollback()
        print(f"Erro ao recriar tabela: {e}")
        cur.close()
        conn.close()
        return False
    
    # Restaurar dados se existirem
    if certificados_existentes and colnames:
        print("Restaurando dados...")
        try:
            # Remover coluna 'id' se existir (será gerada automaticamente)
            if 'id' in colnames:
                id_index = colnames.index('id')
                colnames.pop(id_index)
                certificados_existentes = [cert[:id_index] + cert[id_index+1:] for cert in certificados_existentes]
            
            # Remover coluna 'data_criacao' se existir (será gerada automaticamente)
            if 'data_criacao' in colnames:
                dc_index = colnames.index('data_criacao')
                colnames.pop(dc_index)
                certificados_existentes = [cert[:dc_index] + cert[dc_index+1:] for cert in certificados_existentes]
            
            # Preparar query de inserção
            placeholders = ', '.join(['%s'] * len(colnames))
            columns = ', '.join(colnames)
            
            for cert in certificados_existentes:
                try:
                    cur.execute(f"INSERT INTO certificados ({columns}) VALUES ({placeholders})", cert)
                except Exception as e:
                    print(f"Erro ao inserir certificado: {e}")
            
            conn.commit()
            print(f"Dados restaurados: {len(certificados_existentes)} registros")
        except Exception as e:
            conn.rollback()
            print(f"Erro ao restaurar dados: {e}")
    
    cur.close()
    conn.close()
    return True

def importar_dados(arquivo_csv):
    """Importa dados do CSV para o banco de dados com suporte a múltiplos certificados por CPF"""
    if not os.path.exists(arquivo_csv):
        print(f"Arquivo não encontrado: {arquivo_csv}")
        return False
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print(f"Importando dados de {arquivo_csv}...")
    
    registros_validos = 0
    registros_duplicados = 0
    registros_invalidos = 0
    
    # Tentar diferentes encodings
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    file_content = None
    
    for encoding in encodings:
        try:
            with open(arquivo_csv, 'r', encoding=encoding) as f:
                file_content = f.read()
                break
        except UnicodeDecodeError:
            continue
    
    if not file_content:
        print("Não foi possível ler o arquivo com nenhum dos encodings testados.")
        return False
    
    # Processar o CSV
    reader = csv.DictReader(file_content.splitlines())
    
    # Mapear os campos esperados
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
                    # Verificar se este CPF+curso já existe
                    cur.execute("SELECT id FROM certificados WHERE cpf = %s AND curso = %s", (cpf, curso))
                    existing = cur.fetchone()
                    
                    if existing:
                        # Atualizar certificado existente
                        cur.execute('''
                        UPDATE certificados 
                        SET nome = %s, link_certificado = %s, estado = %s, data_adesao = %s, escola = %s
                        WHERE cpf = %s AND curso = %s
                        ''', (nome, link, estado, data_adesao, escola, cpf, curso))
                        registros_duplicados += 1
                    else:
                        # Inserir novo certificado
                        cur.execute('''
                        INSERT INTO certificados 
                        (nome, curso, cpf, link_certificado, estado, data_adesao, escola)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''', (nome, curso, cpf, link, estado, data_adesao, escola))
                        registros_validos += 1
                    
                    # Commit a cada 100 registros
                    if (registros_validos + registros_duplicados) % 100 == 0:
                        conn.commit()
                        print(f"Processados {registros_validos + registros_duplicados} registros...")
                except Exception as e:
                    registros_invalidos += 1
                    print(f"Erro ao processar linha {i+2} (CPF: {cpf}, Curso: {curso}): {e}")
            else:
                registros_invalidos += 1
                razoes = []
                if not nome: razoes.append("sem nome")
                if not cpf: razoes.append("CPF inválido")
                if not curso: razoes.append("sem curso")
                if not link: razoes.append("sem link")
                print(f"Registro inválido linha {i+2}: {', '.join(razoes)}")
        except Exception as e:
            registros_invalidos += 1
            print(f"Erro ao processar linha {i+2}: {e}")
    
    # Commit final
    conn.commit()
    
    # Verificar resultados
    cur.execute("SELECT COUNT(*) FROM certificados")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT cpf) FROM certificados")
    alunos = cur.fetchone()[0]
    
    print("\nImportação concluída:")
    print(f"Registros válidos novos: {registros_validos}")
    print(f"Registros atualizados: {registros_duplicados}")
    print(f"Registros inválidos: {registros_invalidos}")
    print(f"Total na tabela: {total} certificados para {alunos} alunos")
    
    # Verificar alunos com múltiplos certificados
    cur.execute('''
    SELECT cpf, nome, COUNT(*) as total 
    FROM certificados 
    GROUP BY cpf, nome 
    HAVING COUNT(*) > 1 
    ORDER BY total DESC 
    LIMIT 5
    ''')
    
    multi_certs = cur.fetchall()
    if multi_certs:
        print("\nAlunos com múltiplos certificados:")
        for cpf, nome, total in multi_certs:
            print(f"- {nome} (CPF: {cpf}): {total} certificados")
    else:
        print("\nNenhum aluno possui múltiplos certificados!")
    
    cur.close()
    conn.close()
    return True

def main():
    print("== CORREÇÃO DE MÚLTIPLOS CERTIFICADOS ==")
    
    # 1. Recriar a tabela com a estrutura correta
    print("\nEtapa 1: Recriar tabela certificados")
    if not recriar_tabela():
        print("Falha ao recriar tabela. Encerrando.")
        return
    
    # 2. Importar dados
    arquivo_csv = 'data/base_dados.csv'
    print(f"\nEtapa 2: Importar dados de {arquivo_csv}")
    
    if not os.path.exists(arquivo_csv):
        print(f"Arquivo não encontrado: {arquivo_csv}")
        csv_files = [f for f in os.listdir('data') if f.endswith('.csv')]
        if csv_files:
            arquivo_csv = os.path.join('data', csv_files[0])
            print(f"Usando arquivo alternativo: {arquivo_csv}")
        else:
            print("Nenhum arquivo CSV encontrado na pasta 'data'")
            return
    
    importar_dados(arquivo_csv)
    
    print("\n== CORREÇÃO CONCLUÍDA ==")
    print("Agora você deve conseguir visualizar todos os certificados ao buscar por CPF.")
    print("Reinicie o contêiner web para aplicar todas as alterações:")
    print("$ docker-compose restart web")

if __name__ == "__main__":
    main()