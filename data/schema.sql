-- Esquema del modelo de cobranzas (ANSI SQL; compatible con PostgreSQL / DuckDB / SQLite con ajustes menores)

CREATE TABLE clientes (
    cliente_id               VARCHAR PRIMARY KEY,
    fecha_vinculacion        DATE,
    tipo_cliente             VARCHAR,
    rango_ingreso            VARCHAR,
    departamento             VARCHAR,
    antiguedad_laboral_meses INT
);

CREATE TABLE creditos (
    credito_id        VARCHAR PRIMARY KEY,
    cliente_id        VARCHAR NOT NULL REFERENCES clientes(cliente_id),
    producto          VARCHAR,
    fecha_desembolso  DATE,
    monto_original    DECIMAL(18,2),
    plazo_meses       INT,
    cuota_pactada     DECIMAL(18,2),
    fecha_vencimiento DATE,
    estado_actual     VARCHAR
);

CREATE TABLE gestiones_cobranza (
    gestion_id     VARCHAR PRIMARY KEY,
    credito_id     VARCHAR NOT NULL REFERENCES creditos(credito_id),
    fecha_gestion  TIMESTAMP,
    canal          VARCHAR,
    resultado      VARCHAR,
    promesa_pago   BOOLEAN,
    fecha_promesa  DATE
);

CREATE TABLE cartera_diaria (
    credito_id      VARCHAR NOT NULL REFERENCES creditos(credito_id),
    fecha_corte     DATE NOT NULL,
    dias_mora       INT,
    saldo_capital   DECIMAL(18,2),
    saldo_vencido   DECIMAL(18,2),
    cuotas_vencidas INT,
    valor_exigible  DECIMAL(18,2),
    estado_mora     VARCHAR,
    PRIMARY KEY (credito_id, fecha_corte)
);

CREATE TABLE pagos (
    pago_id        VARCHAR PRIMARY KEY,
    credito_id     VARCHAR NOT NULL REFERENCES creditos(credito_id),
    fecha_pago     DATE,
    fecha_registro TIMESTAMP,
    monto_pagado   DECIMAL(18,2),
    tipo_pago      VARCHAR,
    estado_pago    VARCHAR
);
