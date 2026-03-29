-- ============================================================
--  Fast Food Menu - PostgreSQL Setup
--  Jadvallar + Ma'lumotlar + Rasm yo'llari
-- ============================================================

-- Eski jadvallarni o'chirish (qayta ishga tushirganda)
DROP TABLE IF EXISTS menu_items CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- ============================================================
-- 1. KATEGORIYALAR JADVALI
-- ============================================================
CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 2. MENU ELEMENTLARI JADVALI
-- ============================================================
CREATE TABLE menu_items (
    id           SERIAL PRIMARY KEY,
    category_id  INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name         VARCHAR(200) NOT NULL,
    description  VARCHAR(500),
    price        INTEGER NOT NULL,        -- UZS (so'm)
    image_path   VARCHAR(500),            -- images/ papkasidagi fayl yo'li
    created_at   TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- KATEGORIYALAR
-- ============================================================
INSERT INTO categories (name) VALUES
    ('Pizza'),
    ('Shaverma & Haggi'),
    ('Lavash'),
    ('Hot-Dog'),
    ('KFC & Twister'),
    ('Fri & Kartoshka'),
    ('Gamburger'),
    ('Moxito & Milky Shake'),
    ('Vafli'),
    ('Chay'),
    ('Kofe');

-- ============================================================
-- PIZZA  (category_id = 1)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(1, 'Pizza Мясной',    'Go''sht pizza',    100000, 'images/pizza_myasnoy.png'),
(1, 'Pizza Пепперони', 'Pepperoni pizza',   95000, 'images/pizza_pepperoni.png'),
(1, 'Pizza Куриный',   'Tovuq pizza',       85000, 'images/pizza_kuriny.png'),
(1, 'Pizza Маргарита', 'Margarita pizza',   75000, 'images/pizza_margarita.png'),
(1, 'Pizza Комбо',     'Kombo pizza',      115000, 'images/pizza_kombo.png'),
(1, 'Pizza Верона',    'Verona pizza',      85000, 'images/pizza_verona.png'),
(1, 'Pizza Мих',       'Mix pizza',        115000, 'images/pizza_mix.png'),
(1, 'Pizza Диамонд',   'Diamond pizza',     95000, 'images/pizza_diamond.png');

-- ============================================================
-- SHAVERMA & HAGGI  (category_id = 2)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(2, 'Shaverma Классический', 'Klassik shaverma',   35000, 'images/shaverma_classic.png'),
(2, 'Shaverma Сыром',        'Pishloqli shaverma', 40000, 'images/shaverma_cheese.png'),
(2, 'Haggi Мясной',          'Go''sht haggi',      40000, 'images/haggi_myasnoy.png'),
(2, 'Haggi Куриные',         'Tovuq haggi',        36000, 'images/haggi_kuriny.png');

-- ============================================================
-- LAVASH  (category_id = 3)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(3, 'Lavash Классический',  'Klassik lavash',          40000, 'images/lavash_classic.png'),
(3, 'Lavash Двойной',       'Ikki qavatli lavash',      48000, 'images/lavash_double.png'),
(3, 'Lavash Тандыр',        'Tandirli lavash',          45000, 'images/lavash_tandir.png'),
(3, 'Lavash Тандыр Острый', 'Achchiq tandirli lavash',  45000, 'images/lavash_tandir_hot.png');

-- ============================================================
-- HOT-DOG  (category_id = 4)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(4, 'Hot-Dog Классический', 'Klassik hot-dog',      15000, 'images/hotdog_classic.png'),
(4, 'Hot-Dog Двойной',      'Ikki barobar hot-dog', 20000, 'images/hotdog_double.png'),
(4, 'Hot-Dog Американский', 'Amerika hot-dog',      20000, 'images/hotdog_american.png'),
(4, 'Hot-Dog Барбекю',      'Barbekyuli hot-dog',   20000, 'images/hotdog_bbq.png'),
(4, 'Hot-Dog Турецкие',     'Turk hot-dog',         25000, 'images/hotdog_turkish.png');

-- ============================================================
-- KFC & TWISTER  (category_id = 5)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(5, 'KFC',         'KFC krujkalar',  30000, 'images/kfc.png'),
(5, 'Наггетсы',    'Nuggetlar',      30000, 'images/nuggets.png'),
(5, 'Twister',     'Twister wrap',   35000, 'images/twister.png'),
(5, 'Donar Kebab', 'Donar kebab',    38000, 'images/donar_kebab.png');

-- ============================================================
-- FRI & KARTOSHKA  (category_id = 6)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(6, 'Fri Картошка',      'Kartoshka fri',     20000, 'images/fri_kartoshka.png'),
(6, 'Kartoshka Шарики',  'Kartoshka sharlar', 20000, 'images/kartoshka_shariki.png'),
(6, 'Kartoshka Айдахо',  'Aydaho kartoshka',  20000, 'images/kartoshka_aydaho.png');

-- ============================================================
-- GAMBURGER  (category_id = 7)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(7, 'Gamburger Хоразм', 'Xorazm gamburger',   15000, 'images/gamburger_xorazm.png'),
(7, 'Gamburger Патира', 'Patira gamburger',   15000, 'images/gamburger_patira.png'),
(7, 'Gamburger Ўрама',  'O''rama gamburger',  35000, 'images/gamburger_urama.png');

-- ============================================================
-- MOXITO & MILKY SHAKE  (category_id = 8)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(8, 'Moxito Классический',   'Klassik moxito',       30000, 'images/moxito_classic.png'),
(8, 'Moxito Ягодные',        'Mevalı moxito',        30000, 'images/moxito_berry.png'),
(8, 'Milky Shake Клубника',  'Qulupnay milkshake',   30000, 'images/milkshake_strawberry.png'),
(8, 'Milky Shake Банановый', 'Banan milkshake',      30000, 'images/milkshake_banana.png'),
(8, 'Milky Shake Шоколадный','Shokolad milkshake',   30000, 'images/milkshake_chocolate.png');

-- ============================================================
-- VAFLI  (category_id = 9)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(9, 'Vafli Клубничные', 'Qulupnayli vafli', 55000, 'images/vafli_strawberry.png'),
(9, 'Vafli Банановые',  'Bananli vafli',    60000, 'images/vafli_banana.png'),
(9, 'Vafli Мих',        'Mix vafli',        60000, 'images/vafli_mix.png');

-- ============================================================
-- CHAY  (category_id = 10)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(10, 'Chay Зелёный',    'Yashil choy',       15000, 'images/chay_green.png'),
(10, 'Chay Чёрный',     'Qora choy',         15000, 'images/chay_black.png'),
(10, 'Chay С лимоном',  'Limonli choy',      20000, 'images/chay_lemon.png'),
(10, 'Chay Мих Фрукты', 'Meva aralash choy', 45000, 'images/chay_fruit_mix.png');

-- ============================================================
-- KOFE  (category_id = 11)
-- ============================================================
INSERT INTO menu_items (category_id, name, description, price, image_path) VALUES
(11, 'Kofe Латте',    'Latte qahva',  25000, 'images/kofe_latte.png'),
(11, 'Kofe Капучино', 'Kapuchino',    25000, 'images/kofe_kapuchino.png'),
(11, 'Kofe Чёрный',   'Qora qahva',   25000, 'images/kofe_black.png');

-- ============================================================
-- TEKSHIRISH
-- ============================================================
SELECT
    c.name        AS kategoriya,
    COUNT(m.id)   AS taomlar_soni,
    MIN(m.price)  AS min_narx,
    MAX(m.price)  AS max_narx
FROM categories c
LEFT JOIN menu_items m ON c.id = m.category_id
GROUP BY c.name, c.id
ORDER BY c.id;
