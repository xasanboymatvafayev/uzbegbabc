"""initial seed data

Revision ID: 0001_seed
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision = '0001_seed'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tables
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tg_id', sa.BigInteger(), unique=True, nullable=False, index=True),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(512), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('ref_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('promo_given', sa.Boolean(), default=False),
    )

    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
    )

    op.create_table(
        'foods',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('rating', sa.Float(), default=5.0),
        sa.Column('is_new', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('image_url', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'couriers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('chat_id', sa.BigInteger(), unique=True, nullable=False),
        sa.Column('name', sa.String(512), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_number', sa.String(64), unique=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('customer_name', sa.String(512), nullable=False),
        sa.Column('phone', sa.String(32), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('total', sa.Float(), nullable=False),
        sa.Column('status', sa.String(32), default='NEW'),
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
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('food_id', sa.Integer(), sa.ForeignKey('foods.id'), nullable=True),
        sa.Column('name_snapshot', sa.String(512), nullable=False),
        sa.Column('price_snapshot', sa.Float(), nullable=False),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('line_total', sa.Float(), nullable=False),
    )

    op.create_table(
        'promos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('discount_percent', sa.Float(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('usage_limit', sa.Integer(), nullable=True),
        sa.Column('used_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(128), unique=True, nullable=False),
        sa.Column('value', sa.String(1024), nullable=True),
    )

    # Seed categories
    cats_table = sa.table('categories',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('is_active', sa.Boolean),
    )
    op.bulk_insert(cats_table, [
        {'id': 1, 'name': 'Lavash', 'is_active': True},
        {'id': 2, 'name': 'Burger', 'is_active': True},
        {'id': 3, 'name': 'Xaggi', 'is_active': True},
        {'id': 4, 'name': 'Shaurma', 'is_active': True},
        {'id': 5, 'name': 'Hotdog', 'is_active': True},
        {'id': 6, 'name': 'Combo', 'is_active': True},
        {'id': 7, 'name': 'Sneki', 'is_active': True},
        {'id': 8, 'name': 'Sous', 'is_active': True},
        {'id': 9, 'name': 'Napitki', 'is_active': True},
    ])

    # Seed foods
    foods_table = sa.table('foods',
        sa.column('category_id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('price', sa.Float),
        sa.column('rating', sa.Float),
        sa.column('is_new', sa.Boolean),
        sa.column('is_active', sa.Boolean),
    )
    op.bulk_insert(foods_table, [
        # Lavash
        {'category_id': 1, 'name': 'Lavash Classic', 'description': 'Классический лаваш с курицей и овощами', 'price': 18000, 'rating': 4.8, 'is_new': False, 'is_active': True},
        {'category_id': 1, 'name': 'Lavash Spicy', 'description': 'Острый лаваш с говядиной и соусом чили', 'price': 22000, 'rating': 4.9, 'is_new': True, 'is_active': True},
        {'category_id': 1, 'name': 'Lavash Mix', 'description': 'Смешанный лаваш с двумя видами мяса', 'price': 25000, 'rating': 4.7, 'is_new': False, 'is_active': True},
        # Burger
        {'category_id': 2, 'name': 'Classic Burger', 'description': 'Классический бургер с говяжьей котлетой', 'price': 28000, 'rating': 4.6, 'is_new': False, 'is_active': True},
        {'category_id': 2, 'name': 'Chicken Burger', 'description': 'Нежный бургер с куриным филе', 'price': 24000, 'rating': 4.7, 'is_new': False, 'is_active': True},
        {'category_id': 2, 'name': 'Double Burger', 'description': 'Двойная котлета, двойной сыр', 'price': 35000, 'rating': 4.9, 'is_new': True, 'is_active': True},
        # Shaurma
        {'category_id': 4, 'name': 'Shaurma Classic', 'description': 'Шаурма с курицей, овощами и соусом', 'price': 20000, 'rating': 4.8, 'is_new': False, 'is_active': True},
        {'category_id': 4, 'name': 'Shaurma XL', 'description': 'Большая шаурма с двойной порцией мяса', 'price': 30000, 'rating': 4.9, 'is_new': True, 'is_active': True},
        {'category_id': 4, 'name': 'Shaurma BBQ', 'description': 'Шаурма с соусом BBQ и говядиной', 'price': 26000, 'rating': 4.7, 'is_new': False, 'is_active': True},
        # Hotdog
        {'category_id': 5, 'name': 'Classic Hotdog', 'description': 'Классический хот-дог с сосиской', 'price': 14000, 'rating': 4.5, 'is_new': False, 'is_active': True},
        {'category_id': 5, 'name': 'Cheese Hotdog', 'description': 'Хот-дог с сыром и горчицей', 'price': 17000, 'rating': 4.6, 'is_new': False, 'is_active': True},
        {'category_id': 5, 'name': 'Mega Hotdog', 'description': 'Большой хот-дог с двойной сосиской', 'price': 22000, 'rating': 4.7, 'is_new': True, 'is_active': True},
        # Combo
        {'category_id': 6, 'name': 'Combo 1', 'description': 'Шаурма + картошка + напиток', 'price': 45000, 'rating': 4.9, 'is_new': False, 'is_active': True},
        {'category_id': 6, 'name': 'Combo 2', 'description': 'Бургер + картошка + напиток', 'price': 50000, 'rating': 4.8, 'is_new': True, 'is_active': True},
        {'category_id': 6, 'name': 'Family Combo', 'description': '2 шаурмы + 2 напитка + снек', 'price': 85000, 'rating': 5.0, 'is_new': True, 'is_active': True},
        # Sneki
        {'category_id': 7, 'name': 'Картошка фри', 'description': 'Хрустящая картошка фри', 'price': 12000, 'rating': 4.7, 'is_new': False, 'is_active': True},
        {'category_id': 7, 'name': 'Луковые кольца', 'description': 'Луковые кольца в хрустящей панировке', 'price': 14000, 'rating': 4.6, 'is_new': False, 'is_active': True},
        {'category_id': 7, 'name': 'Наггетсы', 'description': '10 штук куриных наггетсов', 'price': 18000, 'rating': 4.8, 'is_new': False, 'is_active': True},
        # Sous
        {'category_id': 8, 'name': 'Кетчуп', 'description': 'Классический томатный кетчуп', 'price': 3000, 'rating': 4.5, 'is_new': False, 'is_active': True},
        {'category_id': 8, 'name': 'Майонез', 'description': 'Классический майонез', 'price': 3000, 'rating': 4.5, 'is_new': False, 'is_active': True},
        {'category_id': 8, 'name': 'Соус Чили', 'description': 'Острый соус чили', 'price': 4000, 'rating': 4.7, 'is_new': False, 'is_active': True},
        # Napitki
        {'category_id': 9, 'name': 'Coca-Cola 0.5', 'description': 'Кока-кола 0.5 литра', 'price': 8000, 'rating': 4.8, 'is_new': False, 'is_active': True},
        {'category_id': 9, 'name': 'Fanta 0.5', 'description': 'Фанта апельсин 0.5 литра', 'price': 8000, 'rating': 4.6, 'is_new': False, 'is_active': True},
        {'category_id': 9, 'name': 'Вода 0.5', 'description': 'Минеральная вода без газа', 'price': 5000, 'rating': 4.5, 'is_new': False, 'is_active': True},
    ])


def downgrade() -> None:
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('promos')
    op.drop_table('foods')
    op.drop_table('categories')
    op.drop_table('couriers')
    op.drop_table('app_settings')
    op.drop_table('users')
