from flask import Flask, request, jsonify
import psycopg2
import uuid
from datetime import datetime
from datetime import timezone
import psycopg2.extras
from dotenv import load_dotenv
import os

# Carregar variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)

# Configurando a conexão com o PostgreSQL usando variáveis de ambiente
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cursor = conn.cursor()

# Registrando o adaptador para UUID
psycopg2.extras.register_uuid()

# Função para inicializar as tabelas se não existirem
def init_db():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id UUID PRIMARY KEY,
        nome VARCHAR(100) NOT NULL
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS atividades (
        id SERIAL PRIMARY KEY,
        usuario_id UUID NOT NULL,
        ociosidade TEXT NOT NULL,
        active_window TEXT NOT NULL,
        horario TIMESTAMP NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    );
    ''')
    conn.commit()

@app.route('/usuario', methods=['GET'])
def get_user():
    usuario_id = request.args.get('usuario_id')
    if usuario_id:
        cursor.execute("SELECT * FROM usuarios WHERE id = %s;", (uuid.UUID(usuario_id),))
        usuario = cursor.fetchone()
        if usuario:
            return jsonify({'usuario_id': str(usuario[0]), 'usuario': usuario[1]}), 200
    else:
        usuario_nome = request.args.get('usuario_nome')
        if not usuario_nome:
            return jsonify({'message': 'Nome de usuário não fornecido!'}), 400
        
        # Verifica se o usuário já existe
        cursor.execute("SELECT * FROM usuarios WHERE nome = %s;", (usuario_nome,))
        usuario = cursor.fetchone()
        if usuario:
            return jsonify({'usuario_id': str(usuario[0]), 'usuario': usuario[1]}), 200  # Retorna o usuário existente

        # Se não existir, cria um novo usuário
        new_user_id = uuid.uuid4()
        cursor.execute("INSERT INTO usuarios (id, nome) VALUES (%s, %s);", (str(new_user_id), usuario_nome))  # Convertendo UUID para string
        conn.commit()
        return jsonify({'message': 'Usuário criado com sucesso!', 'usuario_id': str(new_user_id)}), 201

@app.route('/atividade', methods=['POST'])
def add_activity():
    data = request.json
    
    # Valida se os dados necessários estão presentes
    if 'usuario_id' not in data or 'ociosidade' not in data or 'active_window' not in data:
        return jsonify({'message': 'Dados inválidos!'}), 400

    # Adiciona a atividade no PostgreSQL
    cursor.execute(
        "INSERT INTO atividades (usuario_id, ociosidade, active_window, horario) VALUES (%s, %s, %s, %s);",
        (str(uuid.UUID(data['usuario_id'])), data['ociosidade'], data['active_window'], datetime.now(timezone.utc))
    )
    conn.commit()
    
    return jsonify({'message': 'Atividade salva com sucesso!'}), 201

@app.route('/atividades', methods=['GET'])
def get_activities():
    cursor.execute("SELECT * FROM atividades;")
    atividades = cursor.fetchall()
    result = [{'usuario_id': str(atividade[1]), 'ociosidade': atividade[2], 'active_window': atividade[3], 'horario': atividade[4]} for atividade in atividades]
    return jsonify(result)

@app.route('/usuarios', methods=['GET'])
def get_users():
    cursor.execute("SELECT * FROM usuarios;")
    usuarios = cursor.fetchall()
    result = [{'usuario_id': str(usuario[0]), 'usuario': usuario[1]} for usuario in usuarios]
    return jsonify(result)

if __name__ == '__main__':
    init_db()  # Inicializa o banco de dados
    app.run(debug=True)