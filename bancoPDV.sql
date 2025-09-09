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
