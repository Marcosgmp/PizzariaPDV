-- Clientes
CREATE TABLE Customers (
    id_customer SERIAL PRIMARY KEY,
    name_customers VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    address TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    loyalty_points INT DEFAULT 0
);

-- Entregadores
CREATE TABLE Delivery_drivers (
    id_driver SERIAL PRIMARY KEY,
    name_driver VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    status_driver VARCHAR(20) NOT NULL 
        CHECK (status_driver IN ('disponível', 'em entrega')) 
        DEFAULT 'disponível'
);

-- Produtos
CREATE TABLE Products (
    id_product SERIAL PRIMARY KEY,
    name_product VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL, -- pizza, bebida etc.
    size_product VARCHAR(10),       -- P, M, G (quando necessário)
    price NUMERIC(10,2) NOT NULL
);

-- Estoque
CREATE TABLE Inventory (
    id_inventory SERIAL PRIMARY KEY,
    id_product INT NOT NULL REFERENCES Products(id_product) ON DELETE CASCADE,
    stock_quantity INT NOT NULL,
    expiration_date DATE
);

-- Pedidos
CREATE TABLE Orders (
    id_order SERIAL PRIMARY KEY,
    id_customer INT NOT NULL REFERENCES Customers(id_customer) ON DELETE CASCADE,
    id_driver INT REFERENCES Delivery_drivers(id_driver),
    order_date TIMESTAMP DEFAULT NOW(),
    status_order VARCHAR(20) NOT NULL 
        CHECK (status_order IN ('Preparando', 'A caminho', 'Entregue')) 
        DEFAULT 'Preparando',
    total NUMERIC(10,2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL
);

-- Itens do Pedido
CREATE TABLE Order_items (
    id_item SERIAL PRIMARY KEY,
    id_order INT NOT NULL REFERENCES Orders(id_order) ON DELETE CASCADE,
    id_product INT NOT NULL REFERENCES Products(id_product),
    quantity INT NOT NULL,
    note TEXT
);

-- Pagamentos
CREATE TABLE Payments (
    id_payment SERIAL PRIMARY KEY,
    id_order INT UNIQUE NOT NULL REFERENCES Orders(id_order) ON DELETE CASCADE,
    type_payment VARCHAR(20) NOT NULL, 
    status_payments VARCHAR(20) NOT NULL 
        CHECK (status_payments IN ('Pendente', 'Confirmado', 'Cancelado')) 
        DEFAULT 'Pendente',
    payment_date TIMESTAMP DEFAULT NOW()
);

-- Alertas do Caixa
CREATE TABLE Cash_alerts (
    id_alert SERIAL PRIMARY KEY,
    id_order INT NOT NULL REFERENCES Orders(id_order) ON DELETE CASCADE,
    message_alert TEXT NOT NULL,
    status VARCHAR(20) 
        CHECK (status IN ('ativo', 'resolvido')) 
        DEFAULT 'ativo'
);

-- Clientes (adicionando coordenadas)
ALTER TABLE Customers 
ADD COLUMN latitude NUMERIC(9,6),
ADD COLUMN longitude NUMERIC(9,6);

-- Entregadores (opcional: localização atual em tempo real)
ALTER TABLE Delivery_drivers 
ADD COLUMN latitude NUMERIC(9,6),
ADD COLUMN longitude NUMERIC(9,6);


-- Clientes: buscar rápido por telefone (já tem UNIQUE, mas índice explícito ajuda em consultas)
CREATE INDEX idx_customers_phone ON Customers(phone);

-- Entregadores: buscar motoristas pelo status (quem está disponível)
CREATE INDEX idx_drivers_status ON Delivery_drivers(status_driver);

-- Produtos: filtrar por categoria + tamanho (ex: pizza G, bebida etc.)
CREATE INDEX idx_products_category_size 
    ON Products(category, size_product);

-- Estoque: buscar pelo produto (ligação com estoque)
CREATE INDEX idx_inventory_product ON Inventory(id_product);

-- Pedidos: consultas frequentes por cliente e status
CREATE INDEX idx_orders_customer ON Orders(id_customer);
CREATE INDEX idx_orders_status ON Orders(status_order);

-- Entregadores nos pedidos (relatórios de entregas por motoboy)
CREATE INDEX idx_orders_driver ON Orders(id_driver);

-- Itens do pedido: buscar por pedido e produto
CREATE INDEX idx_order_items_order ON Order_items(id_order);
CREATE INDEX idx_order_items_product ON Order_items(id_product);

-- Pagamentos: buscar rápido por status (pendente/confirmado)
CREATE INDEX idx_payments_status ON Payments(status_payments);

-- Alertas: buscar rápido por pedido e status (ativos ou resolvidos)
CREATE INDEX idx_alerts_order ON Cash_alerts(id_order);
CREATE INDEX idx_alerts_status ON Cash_alerts(status);

