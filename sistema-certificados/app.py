import os
from flask import Flask, request, jsonify, redirect, render_template
import psycopg2
from psycopg2.extras import RealDictCursor
import re
import urllib.parse

app = Flask(__name__)

# Configuração da conexão com o PostgreSQL
DB_CONFIG = {
    "dbname": "certificados_db",
    "user": os.environ.get("DB_USER", "certificados_user"),
    "password": os.environ.get("DB_PASSWORD", "certificados_pwd"),
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432")
}

def conectar_db():
    """Estabelece conexão com o banco de dados"""
    return psycopg2.connect(**DB_CONFIG)

def normalizar_cpf(cpf):
    """Remove caracteres não numéricos do CPF"""
    return re.sub(r'[^0-9]', '', cpf)

@app.route('/')
def index():
    """Página inicial com formulário de consulta"""
    return render_template('index.html')

@app.route('/estados')
def listar_estados():
    """Lista os estados disponíveis no banco de dados"""
    try:
        # Conectar ao banco de dados
        conn = conectar_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Buscar estados disponíveis
        cursor.execute("SELECT DISTINCT estado FROM certificados WHERE estado != '' ORDER BY estado")
        resultados = cursor.fetchall()
        
        # Fechar conexão
        cursor.close()
        conn.close()
        
        # Extrair lista de estados
        estados = [r['estado'] for r in resultados if r['estado']]
        
        return jsonify({"estados": estados})
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar estados: {str(e)}"}), 500

@app.route('/certificado', methods=['POST'])
def buscar_certificado():
    """Busca certificados pelo CPF"""
    # Obter CPF da requisição
    dados = request.json
    if not dados or 'cpf' not in dados:
        return jsonify({"erro": "CPF não fornecido"}), 400
    
    # Normalizar CPF
    cpf = normalizar_cpf(dados['cpf'])
    if not cpf:
        return jsonify({"erro": "CPF inválido"}), 400
    
    # Formatar CPF para o padrão do banco (XXX.XXX.XXX-XX)
    if len(cpf) == 11:
        cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    else:
        # Buscar parcial se CPF incompleto
        cpf_formatado = cpf
    
    # Filtrar por estado se fornecido
    estado = dados.get('estado', None)
    
    try:
        # Conectar ao banco de dados
        conn = conectar_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Buscar todos os certificados para o CPF
        if estado:
            cursor.execute(
                """
                SELECT 
                    nome, curso, cpf, link_certificado, estado, data_adesao, escola 
                FROM certificados 
                WHERE cpf LIKE %s AND estado = %s
                ORDER BY curso
                """, 
                (f"%{cpf_formatado}%", estado)
            )
        else:
            cursor.execute(
                """
                SELECT 
                    nome, curso, cpf, link_certificado, estado, data_adesao, escola 
                FROM certificados 
                WHERE cpf LIKE %s
                ORDER BY curso
                """, 
                (f"%{cpf_formatado}%",)
            )
            
        resultados = cursor.fetchall()
        
        # Fechar conexão
        cursor.close()
        conn.close()
        
        if resultados:
            # Verificar se cada certificado tem um link válido
            for certificado in resultados:
                # Adicionar ID específico para cada certificado (CPF+Curso para URL)
                curso_url = urllib.parse.quote(certificado['curso'])
                cpf_url = urllib.parse.quote(certificado['cpf'])
                certificado['certificado_id'] = f"{cpf_url}/{curso_url}"
            
            return jsonify({
                "certificados": resultados,
                "total": len(resultados)
            })
        else:
            return jsonify({"erro": "Certificado não encontrado"}), 404
            
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar certificado: {str(e)}"}), 500

@app.route('/download-certificado/<path:cpf>/<path:curso>', methods=['GET'])
def download_certificado(cpf, curso):
    """Redirecionamento direto para download do certificado"""
    try:
        # Conectar ao banco de dados
        conn = conectar_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Buscar o certificado específico (CPF + curso)
        # Usar LIKE para CPF e curso exato
        cursor.execute(
            "SELECT link_certificado FROM certificados WHERE cpf = %s AND curso = %s", 
            (cpf, curso)
        )
        
        resultado = cursor.fetchone()
        
        # Fechar conexão
        cursor.close()
        conn.close()
        
        if resultado and resultado["link_certificado"]:
            # Validar o link antes de redirecionar
            link = resultado["link_certificado"]
            # Redirecionar para o URL do PDF
            return redirect(link)
        else:
            return jsonify({"erro": "Link do certificado não encontrado"}), 404
            
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar certificado: {str(e)}"}), 500

@app.route('/estatisticas')
def estatisticas():
    """Retorna estatísticas sobre certificados no banco de dados"""
    try:
        conn = conectar_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        stats = {}
        
        # Total de certificados
        cursor.execute("SELECT COUNT(*) as total FROM certificados")
        stats['total_certificados'] = cursor.fetchone()['total']
        
        # Total de alunos distintos
        cursor.execute("SELECT COUNT(DISTINCT cpf) as total FROM certificados")
        stats['total_alunos'] = cursor.fetchone()['total']
        
        # Média de certificados por aluno
        if stats['total_alunos'] > 0:
            stats['media_certificados_por_aluno'] = stats['total_certificados'] / stats['total_alunos']
        else:
            stats['media_certificados_por_aluno'] = 0
            
        # Alunos com mais certificados
        cursor.execute("""
            SELECT nome, cpf, COUNT(*) as total_cursos 
            FROM certificados 
            GROUP BY nome, cpf 
            ORDER BY total_cursos DESC 
            LIMIT 5
        """)
        stats['alunos_mais_certificados'] = cursor.fetchall()
        
        # Certificados por estado
        cursor.execute("SELECT estado, COUNT(*) as total FROM certificados GROUP BY estado ORDER BY total DESC")
        stats['por_estado'] = cursor.fetchall()
        
        # Certificados por curso
        cursor.execute("SELECT curso, COUNT(*) as total FROM certificados GROUP BY curso ORDER BY total DESC")
        stats['por_curso'] = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"erro": f"Erro ao obter estatísticas: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)