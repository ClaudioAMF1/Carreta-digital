import psycopg2
import time
import sys

max_attempts = 30
for attempt in range(max_attempts):
    try:
        print(f"Tentativa {attempt+1}/{max_attempts}...")
        conn = psycopg2.connect(
            dbname="certificados_db",
            user="certificados_user",
            password="certificados_pwd",
            host="db",
            port="5432"
        )
        print("Conexão bem-sucedida!")
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"Erro: {e}")
        time.sleep(2)

print("Não foi possível conectar ao banco de dados após várias tentativas.")
sys.exit(1)