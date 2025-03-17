import psycopg2
from psycopg2.extras import RealDictCursor

# Configuração do banco de dados
DB_CONFIG = {
    'dbname': 'certificados_db',
    'user': 'certificados_user',
    'password': 'certificados_pwd',
    'host': 'db',
    'port': '5432'
}

def conectar_db():
    """Estabelece conexão com o banco de dados"""
    return psycopg2.connect(**DB_CONFIG)

def verificar_estrutura_tabela():
    """Verifica a estrutura atual da tabela certificados"""
    conn = conectar_db()
    cur = conn.cursor()
    
    # Verificar se a tabela existe
    cur.execute("""
    SELECT EXISTS (
       SELECT FROM information_schema.tables 
       WHERE table_name = 'certificados'
    );
    """)
    tabela_existe = cur.fetchone()[0]
    
    if not tabela_existe:
        print("A tabela 'certificados' não existe!")
        cur.close()
        conn.close()
        return
    
    # Verificar as colunas da tabela
    cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'certificados';
    """)
    
    colunas = cur.fetchall()
    print("\nEstrutura da tabela certificados:")
    for coluna in colunas:
        print(f"- {coluna[0]}: {coluna[1]} (Nullable: {coluna[2]})")
    
    # Verificar restrições (constraints)
    cur.execute("""
    SELECT con.conname, con.contype, 
           pg_get_constraintdef(con.oid) as def
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE rel.relname = 'certificados';
    """)
    
    restricoes = cur.fetchall()
    print("\nRestrições da tabela:")
    for restricao in restricoes:
        print(f"- {restricao[0]} ({restricao[1]}): {restricao[2]}")
    
    cur.close()
    conn.close()

def buscar_cpfs_com_multiplos_certificados():
    """Busca CPFs que possuem múltiplos certificados"""
    conn = conectar_db()
    cur = conn.cursor()
    
    cur.execute("""
    SELECT cpf, COUNT(*) as total
    FROM certificados
    GROUP BY cpf
    HAVING COUNT(*) > 1
    ORDER BY total DESC
    LIMIT 10;
    """)
    
    resultados = cur.fetchall()
    print("\nCPFs com múltiplos certificados:")
    
    if not resultados:
        print("Nenhum CPF com múltiplos certificados encontrado!")
    else:
        print(f"Encontrados {len(resultados)} CPFs com múltiplos certificados.")
        for i, (cpf, total) in enumerate(resultados, 1):
            print(f"{i}. CPF {cpf}: {total} certificados")
            
            # Mostrar detalhes dos certificados para este CPF
            cur.execute("""
            SELECT id, nome, curso, link_certificado
            FROM certificados
            WHERE cpf = %s
            ORDER BY curso;
            """, (cpf,))
            
            certificados = cur.fetchall()
            print(f"   Certificados para {cpf} (Nome: {certificados[0][1]}):")
            for cert in certificados:
                print(f"   - ID: {cert[0]}, Curso: {cert[2]}")
                print(f"     Link: {cert[3][:50]}...")
            print()
    
    cur.close()
    conn.close()
    
    return resultados

def testar_api_busca_certificado(cpf_para_testar=None):
    """Simula a API de busca de certificados"""
    conn = conectar_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Se não foi fornecido um CPF, buscar um que tenha múltiplos certificados
    if not cpf_para_testar:
        sub_cursor = conn.cursor()
        sub_cursor.execute("""
        SELECT cpf
        FROM certificados
        GROUP BY cpf
        HAVING COUNT(*) > 1
        LIMIT 1;
        """)
        resultado = sub_cursor.fetchone()
        if resultado:
            cpf_para_testar = resultado[0]
        else:
            print("Não foi encontrado nenhum CPF com múltiplos certificados!")
            cursor.close()
            conn.close()
            return
        
        sub_cursor.close()
    
    print(f"\nTestando busca de certificado para CPF: {cpf_para_testar}")
    
    # Simular a busca feita pela API
    cursor.execute("""
    SELECT 
        nome, curso, cpf, link_certificado, estado, data_adesao, escola 
    FROM certificados 
    WHERE cpf = %s
    ORDER BY curso
    """, (cpf_para_testar,))
    
    resultados = cursor.fetchall()
    
    print(f"Total de resultados retornados: {len(resultados)}")
    if resultados:
        print(f"Nome do aluno: {resultados[0]['nome']}")
        print("Cursos encontrados:")
        for i, cert in enumerate(resultados, 1):
            print(f"{i}. {cert['curso']}")
    
    cursor.close()
    conn.close()
    
    return resultados

def corrigir_problema():
    """Corrige possíveis problemas na estrutura do banco"""
    print("\nCorrigindo possíveis problemas...")
    
    conn = conectar_db()
    cur = conn.cursor()
    
    # Verificar se a chave única composta está definida corretamente
    cur.execute("""
    SELECT EXISTS (
       SELECT FROM pg_constraint
       WHERE conname = 'certificados_cpf_curso_key'
    );
    """)
    
    constraint_exists = cur.fetchone()[0]
    
    if not constraint_exists:
        print("A restrição de chave única composta (cpf, curso) não existe!")
        print("Tentando adicionar a restrição...")
        
        try:
            cur.execute("""
            ALTER TABLE certificados
            ADD CONSTRAINT certificados_cpf_curso_key UNIQUE (cpf, curso);
            """)
            conn.commit()
            print("Restrição adicionada com sucesso!")
        except Exception as e:
            conn.rollback()
            print(f"Erro ao adicionar restrição: {e}")
    else:
        print("A restrição de chave única composta (cpf, curso) já existe.")
    
    # Verificar se há algum registro com "UNIQUE" no campo CPF que possa causar problemas
    cur.execute("""
    SELECT EXISTS (
       SELECT FROM pg_constraint
       WHERE conname = 'certificados_cpf_key'
    );
    """)
    
    cpf_key_exists = cur.fetchone()[0]
    
    if cpf_key_exists:
        print("Encontrada restrição incorreta: 'certificados_cpf_key'!")
        print("Tentando remover a restrição...")
        
        try:
            cur.execute("""
            ALTER TABLE certificados
            DROP CONSTRAINT certificados_cpf_key;
            """)
            conn.commit()
            print("Restrição incorreta removida com sucesso!")
        except Exception as e:
            conn.rollback()
            print(f"Erro ao remover restrição: {e}")
    
    cur.close()
    conn.close()

def main():
    print("== DIAGNÓSTICO DE CERTIFICADOS MÚLTIPLOS ==")
    
    # Verificar estrutura da tabela
    verificar_estrutura_tabela()
    
    # Verificar CPFs com múltiplos certificados
    cpfs_multiplos = buscar_cpfs_com_multiplos_certificados()
    
    # Se não há CPFs com múltiplos certificados, provavelmente há um problema estrutural
    if not cpfs_multiplos:
        print("\nNenhum CPF com múltiplos certificados encontrado no banco.")
        print("Isso sugere que pode haver algum problema na estrutura da tabela ou na importação dos dados.")
        
        # Tentar corrigir o problema
        corrigir_problema()
        
        print("\nApós as correções, você deve importar novamente os dados usando 'custom_import.py'")
        print("Em seguida, teste novamente a funcionalidade de busca por CPF na interface.")
    else:
        # Testar a API para um CPF com múltiplos certificados
        print("\nTestando a API de busca para um CPF com múltiplos certificados...")
        testar_api_busca_certificado(cpfs_multiplos[0][0])
        
        print("\nSe a API retornou todos os certificados, mas a interface mostra apenas um,")
        print("o problema está no frontend. Verifique o arquivo 'templates/index.html'.")
    
    print("\n== DIAGNÓSTICO CONCLUÍDO ==")

if __name__ == "__main__":
    main()