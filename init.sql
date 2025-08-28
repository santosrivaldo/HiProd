-- Criação da tabela usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY,
    nome VARCHAR(255) NOT NULL
);

-- Criação da tabela atividades
CREATE TABLE IF NOT EXISTS atividades (
    id SERIAL PRIMARY KEY,
    usuario_id UUID REFERENCES usuarios(id),
    ociosidade VARCHAR(255) NOT NULL,
    active_window VARCHAR(255) NOT NULL,
    horario TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);