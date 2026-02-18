"""initial seed data

Revision ID: 0001_seed
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0001_seed'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tg_id', sa.BigInteger(), unique=True, nullable=False, index=True),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(512), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('ref_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('promo_given', sa.Boolean(), server_default='false'),
    )

    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
    )

    op.create_table(
        'foods',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('rating', sa.Float(), server_default='5.0'),
        sa.Column('is_new', sa.Boolean(), server_default='false'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('image_url', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'couriers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('chat_id', sa.BigInteger(), unique=True, nullable=False),
        sa.Column('name', sa.String(512), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('order_number', sa.String(64), unique=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('customer_name', sa.String(512), nullable=False),
        sa.Column('phone', sa.String(32), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('total', sa.Float(), nullable=False),
        sa.Column('status', sa.String(32), server_default='NEW'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('location_lat', sa.Float(), nullable=True),
        sa.Column('location_lng', sa.Float(), nullable=True),
        sa.Column('courier_id', sa.Integer(), sa.ForeignKey('couriers.id'), nullable=True),
        sa.Column('channel_message_id', sa.BigInteger(), nullable=True),
        sa.Column('promo_code', sa.String(64), nullable=True),
    )

    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('food_id', sa.Integer(), sa.ForeignKey('foods.id'), nullable=True),
        sa.Column('name_snapshot', sa.String(512), nullable=False),
        sa.Column('price_snapshot', sa.Float(), nullable=False),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('line_total', sa.Float(), nullable=False),
    )

    op.create_table(
        'promos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('discount_percent', sa.Float(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('usage_limit', sa.Integer(), nullable=True),
        sa.Column('used_count', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key', sa.String(128), unique=True, nullable=False),
        sa.Column('value', sa.String(1024), nullable=True),
    )

    # Seed categories - WITHOUT explicit id, let sequence handle it
    op.execute("""
        INSERT INTO categories (name, is_active) VALUES
        ('Lavash', true),
        ('Burger', true),
        ('Xaggi', true),
        ('Shaurma', true),
        ('Hotdog', true),
        ('Combo', true),
        ('Sneki', true),
        ('Sous', true),
        ('Napitki', true)
    """)

    # Seed foods using subquery for category_id
    op.execute("""
        INSERT INTO foods (category_id, name, description, price, rating, is_new, is_active) VALUES
        ((SELECT id FROM categories WHERE name='Lavash'), 'Lavash Classic', 'Klassik lavash tovuq va sabzavotlar bilan', 18000, 4.8, false, true),
        ((SELECT id FROM categories WHERE name='Lavash'), 'Lavash Spicy', 'Achchiq lavash mol go''shti va chili sous bilan', 22000, 4.9, true, true),
        ((SELECT id FROM categories WHERE name='Lavash'), 'Lavash Mix', 'Ikki xil go''sht bilan aralash lavash', 25000, 4.7, false, true),
        ((SELECT id FROM categories WHERE name='Burger'), 'Classic Burger', 'Klassik burger mol go''shti kotletasi bilan', 28000, 4.6, false, true),
        ((SELECT id FROM categories WHERE name='Burger'), 'Chicken Burger', 'Tovuq filesi bilan burger', 24000, 4.7, false, true),
        ((SELECT id FROM categories WHERE name='Burger'), 'Double Burger', 'Ikki kotleta, ikki pishloq', 35000, 4.9, true, true),
        ((SELECT id FROM categories WHERE name='Shaurma'), 'Shaurma Classic', 'Tovuq, sabzavot va sous bilan shaurma', 20000, 4.8, false, true),
        ((SELECT id FROM categories WHERE name='Shaurma'), 'Shaurma XL', 'Ikki porsiya go''sht bilan katta shaurma', 30000, 4.9, true, true),
        ((SELECT id FROM categories WHERE name='Shaurma'), 'Shaurma BBQ', 'BBQ sous va mol go''shti bilan shaurma', 26000, 4.7, false, true),
        ((SELECT id FROM categories WHERE name='Hotdog'), 'Classic Hotdog', 'Klassik hotdog sosiska bilan', 14000, 4.5, false, true),
        ((SELECT id FROM categories WHERE name='Hotdog'), 'Cheese Hotdog', 'Pishloq va xantal bilan hotdog', 17000, 4.6, false, true),
        ((SELECT id FROM categories WHERE name='Hotdog'), 'Mega Hotdog', 'Ikki sosiska bilan katta hotdog', 22000, 4.7, true, true),
        ((SELECT id FROM categories WHERE name='Combo'), 'Combo 1', 'Shaurma + kartoshka + ichimlik', 45000, 4.9, false, true),
        ((SELECT id FROM categories WHERE name='Combo'), 'Combo 2', 'Burger + kartoshka + ichimlik', 50000, 4.8, true, true),
        ((SELECT id FROM categories WHERE name='Combo'), 'Family Combo', '2 shaurma + 2 ichimlik + snek', 85000, 5.0, true, true),
        ((SELECT id FROM categories WHERE name='Sneki'), 'Kartoshka fri', 'Qarsildoq kartoshka fri', 12000, 4.7, false, true),
        ((SELECT id FROM categories WHERE name='Sneki'), 'Piyoz halqalari', 'Qarsildoq xamirda piyoz halqalari', 14000, 4.6, false, true),
        ((SELECT id FROM categories WHERE name='Sneki'), 'Naggetsy', '10 dona tovuq naggetslar', 18000, 4.8, false, true),
        ((SELECT id FROM categories WHERE name='Sous'), 'Ketchup', 'Klassik tomat ketchup', 3000, 4.5, false, true),
        ((SELECT id FROM categories WHERE name='Sous'), 'Mayonez', 'Klassik mayonez', 3000, 4.5, false, true),
        ((SELECT id FROM categories WHERE name='Sous'), 'Chili sous', 'Achchiq chili sous', 4000, 4.7, false, true),
        ((SELECT id FROM categories WHERE name='Napitki'), 'Coca-Cola 0.5', 'Koka-kola 0.5 litr', 8000, 4.8, false, true),
        ((SELECT id FROM categories WHERE name='Napitki'), 'Fanta 0.5', 'Fanta apelsin 0.5 litr', 8000, 4.6, false, true),
        ((SELECT id FROM categories WHERE name='Napitki'), 'Suv 0.5', 'Mineral suv gazsiz', 5000, 4.5, false, true)
    """)


def downgrade() -> None:
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('promos')
    op.drop_table('foods')
    op.drop_table('categories')
    op.drop_table('couriers')
    op.drop_table('app_settings')
    op.drop_table('users')
