// ============================================================
// FIESTA WebApp — script.js
// ============================================================

const tg = window.Telegram?.WebApp;
if (tg) { tg.expand(); tg.ready(); }

const API_BASE = "https://uzbegbabc-production.up.railway.app";  // Same origin (FastAPI serves this)
const MIN_ORDER = 50000;

// State
let state = {
  categories: [],
  foods: [],
  cart: {},           // { food_id: { food, qty } }
  selectedCat: 'all',
  sortBy: '',
  search: '',
  promoCode: null,
  promoDiscount: 0,
  location: null,
};

// ============================================================
// DOM Refs
// ============================================================
const $ = id => document.getElementById(id);
const foodsContainer = $('foodsContainer');
const loadingEl = $('loadingEl');
const categoriesScroll = $('categoriesScroll');
const cartPanel = $('cartPanel');
const cartCount = $('cartCount');
const cartTotal = $('cartTotal');
const checkoutBtn = $('checkoutBtn');
const filterModal = $('filterModal');
const filterBtn = $('filterBtn');
const closeFilterBtn = $('closeFilterBtn');
const applyFilter = $('applyFilter');
const checkoutModal = $('checkoutModal');
const closeCheckoutBtn = $('closeCheckoutBtn');
const submitOrderBtn = $('submitOrderBtn');
const searchInput = $('searchInput');
const geoBtn = $('geoBtn');
const geoStatus = $('geoStatus');
const promoInput = $('promoInput');
const promoApplyBtn = $('promoApplyBtn');
const promoResult = $('promoResult');

// ============================================================
// API
// ============================================================
function getInitData() {
  return tg?.initData || '';
}

async function apiFetch(endpoint) {
  const sep = endpoint.includes('?') ? '&' : '?';
  const init_data = encodeURIComponent(getInitData());
  const url = `${API_BASE}${endpoint}${sep}init_data=${init_data}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

// ============================================================
// Init
// ============================================================
async function init() {
  // Pre-fill user name if available
  if (tg?.initDataUnsafe?.user) {
    const u = tg.initDataUnsafe.user;
    $('customerName').value = [u.first_name, u.last_name].filter(Boolean).join(' ');
  }

  try {
    const [cats, foods] = await Promise.all([
      apiFetch('/api/categories'),
      apiFetch('/api/foods'),
    ]);
    state.categories = cats;
    state.foods = foods;
    renderCategories();
    renderFoods();
  } catch (e) {
    loadingEl.textContent = '⚠️ Ошибка загрузки. Попробуйте позже.';
    console.error(e);
  }
}

// ============================================================
// Categories
// ============================================================
function renderCategories() {
  // Remove existing (except "Все")
  const allBtn = categoriesScroll.querySelector('[data-id="all"]');
  categoriesScroll.innerHTML = '';
  categoriesScroll.appendChild(allBtn);

  state.categories.forEach(cat => {
    const btn = document.createElement('button');
    btn.className = 'cat-btn';
    btn.dataset.id = cat.id;
    btn.textContent = cat.name;
    categoriesScroll.appendChild(btn);
  });

  categoriesScroll.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.selectedCat = btn.dataset.id;
      categoriesScroll.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderFoods();
    });
  });
}

// ============================================================
// Foods
// ============================================================
function getFilteredFoods() {
  let foods = [...state.foods];

  if (state.selectedCat !== 'all') {
    foods = foods.filter(f => String(f.category_id) === String(state.selectedCat));
  }

  if (state.search.trim()) {
    const q = state.search.toLowerCase();
    foods = foods.filter(f => f.name.toLowerCase().includes(q) || (f.description || '').toLowerCase().includes(q));
  }

  if (state.sortBy === 'rating') foods.sort((a, b) => b.rating - a.rating);
  else if (state.sortBy === 'new') foods.sort((a, b) => b.id - a.id);
  else if (state.sortBy === 'price_asc') foods.sort((a, b) => a.price - b.price);
  else if (state.sortBy === 'price_desc') foods.sort((a, b) => b.price - a.price);

  return foods;
}

function renderFoods() {
  const foods = getFilteredFoods();
  foodsContainer.innerHTML = '';

  if (!foods.length) {
    foodsContainer.innerHTML = `<div class="empty-state"><div class="emoji">🍽️</div><div>Ничего не найдено</div></div>`;
    return;
  }

  foods.forEach(food => {
    const card = createFoodCard(food);
    foodsContainer.appendChild(card);
  });
}

function createFoodCard(food) {
  const card = document.createElement('div');
  card.className = 'food-card';
  card.dataset.id = food.id;

  const imgHtml = food.image_url
    ? `<img class="food-img" src="${escHtml(food.image_url)}" alt="${escHtml(food.name)}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
    : '';

  const placeholder = `<div class="food-img-placeholder" ${food.image_url ? 'style="display:none"' : ''}>🍔</div>`;
  const badge = food.is_new ? `<span class="badge-new">NEW</span>` : '';
  const inCart = state.cart[food.id];
  const qty = inCart ? inCart.qty : 0;

  card.innerHTML = `
    ${imgHtml}${placeholder}
    <div class="food-info">
      ${badge ? `<div class="food-badge">${badge}</div>` : ''}
      <div class="food-name">${escHtml(food.name)}</div>
      ${food.description ? `<div class="food-desc">${escHtml(food.description)}</div>` : ''}
      <div class="food-bottom">
        <div>
          <div class="food-price">${fmt(food.price)}</div>
          <div class="food-rating">⭐ ${food.rating.toFixed(1)}</div>
        </div>
        <div class="cart-ctrl" id="ctrl_${food.id}">
          ${qty === 0
            ? `<button class="add-btn" data-id="${food.id}">+ Добавить</button>`
            : `<div class="qty-ctrl">
                <button class="qty-btn" data-action="dec" data-id="${food.id}">−</button>
                <span class="qty-num">${qty}</span>
                <button class="qty-btn" data-action="inc" data-id="${food.id}">+</button>
              </div>`
          }
        </div>
      </div>
    </div>
  `;

  // Events
  card.querySelector('.add-btn')?.addEventListener('click', () => changeQty(food, 1));
  card.querySelectorAll('.qty-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const delta = btn.dataset.action === 'inc' ? 1 : -1;
      changeQty(food, delta);
    });
  });

  return card;
}

function updateCardCtrl(food) {
  const ctrl = document.getElementById(`ctrl_${food.id}`);
  if (!ctrl) return;
  const qty = state.cart[food.id]?.qty || 0;
  ctrl.innerHTML = qty === 0
    ? `<button class="add-btn" data-id="${food.id}">+ Добавить</button>`
    : `<div class="qty-ctrl">
        <button class="qty-btn" data-action="dec" data-id="${food.id}">−</button>
        <span class="qty-num">${qty}</span>
        <button class="qty-btn" data-action="inc" data-id="${food.id}">+</button>
      </div>`;
  ctrl.querySelector('.add-btn')?.addEventListener('click', () => changeQty(food, 1));
  ctrl.querySelectorAll('.qty-btn').forEach(btn => {
    btn.addEventListener('click', () => changeQty(food, btn.dataset.action === 'inc' ? 1 : -1));
  });
}

// ============================================================
// Cart
// ============================================================
function changeQty(food, delta) {
  const current = state.cart[food.id]?.qty || 0;
  const newQty = current + delta;
  if (newQty <= 0) {
    delete state.cart[food.id];
  } else {
    state.cart[food.id] = { food, qty: newQty };
  }
  updateCardCtrl(food);
  updateCartPanel();
}

function cartItems() {
  return Object.values(state.cart);
}

function cartRawTotal() {
  return cartItems().reduce((sum, { food, qty }) => sum + food.price * qty, 0);
}

function cartFinalTotal() {
  const raw = cartRawTotal();
  if (state.promoDiscount > 0) {
    return raw * (1 - state.promoDiscount / 100);
  }
  return raw;
}

function updateCartPanel() {
  const items = cartItems();
  const total = cartRawTotal();
  const count = items.reduce((s, { qty }) => s + qty, 0);

  if (count === 0) {
    cartPanel.style.display = 'none';
    return;
  }
  cartPanel.style.display = 'flex';
  cartCount.textContent = count;
  cartTotal.textContent = fmt(total);
  checkoutBtn.disabled = total < MIN_ORDER;
  checkoutBtn.title = total < MIN_ORDER ? `Минимум ${fmt(MIN_ORDER)}` : '';
}

// ============================================================
// Checkout
// ============================================================
function renderCheckout() {
  const items = cartItems();
  const list = $('cartItemsList');
  list.innerHTML = items.map(({ food, qty }) => `
    <div class="cart-item-row">
      <span class="cart-item-name">${escHtml(food.name)}</span>
      <span class="cart-item-qty">x${qty}</span>
      <span class="cart-item-price">${fmt(food.price * qty)}</span>
    </div>
  `).join('');

  const raw = cartRawTotal();
  const final = cartFinalTotal();
  const discount = raw - final;

  $('orderTotalValue').textContent = fmt(raw);
  if (state.promoDiscount > 0) {
    $('discountRow').style.display = 'flex';
    $('discountValue').textContent = `−${fmt(discount)} (${state.promoDiscount}%)`;
    $('finalRow').style.display = 'flex';
    $('finalValue').textContent = fmt(final);
  } else {
    $('discountRow').style.display = 'none';
    $('finalRow').style.display = 'none';
  }
}

checkoutBtn.addEventListener('click', () => {
  renderCheckout();
  checkoutModal.style.display = 'flex';
});

closeCheckoutBtn.addEventListener('click', () => {
  checkoutModal.style.display = 'none';
});

// ============================================================
// Geo
// ============================================================
geoBtn.addEventListener('click', () => {
  geoStatus.textContent = '⏳ Определяем...';
  geoStatus.className = 'geo-status';
  if (!navigator.geolocation) {
    geoStatus.textContent = '❌ Geolocation не поддерживается';
    return;
  }
  navigator.geolocation.getCurrentPosition(
    pos => {
      state.location = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      geoStatus.textContent = `✅ Локация: ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`;
      geoStatus.className = 'geo-status ok';
    },
    err => {
      geoStatus.textContent = '❌ Не удалось получить локацию. Разрешите доступ.';
    },
    { timeout: 10000 }
  );
});

// ============================================================
// Promo
// ============================================================
promoApplyBtn.addEventListener('click', async () => {
  const code = promoInput.value.trim();
  if (!code) return;
  promoResult.textContent = '⏳ Проверяем...';
  promoResult.className = 'promo-result';
  try {
    const data = await apiFetch(`/api/promo/validate?code=${encodeURIComponent(code)}`);
    state.promoCode = data.code;
    state.promoDiscount = data.discount_percent;
    promoResult.textContent = `✅ Промо-код применён! Скидка ${data.discount_percent}%`;
    promoResult.className = 'promo-result success';
    renderCheckout();
  } catch (e) {
    state.promoCode = null;
    state.promoDiscount = 0;
    promoResult.textContent = '❌ Промо-код не найден или истёк';
    promoResult.className = 'promo-result error';
  }
});

// ============================================================
// Submit Order
// ============================================================
submitOrderBtn.addEventListener('click', async () => {
  const name = $('customerName').value.trim();
  const phone = $('customerPhone').value.trim();

  if (!name) { alert('Введите ваше имя'); return; }
  if (!phone) { alert('Введите номер телефона'); return; }
  if (!state.location) { alert('Укажите местоположение для доставки'); return; }

  const items = cartItems().map(({ food, qty }) => ({
    food_id: food.id,
    name: food.name,
    qty: qty,
    price: food.price,
  }));

  const raw = cartRawTotal();
  const final = cartFinalTotal();

  const payload = {
    type: 'order_create',
    items,
    total: Math.round(final),
    customer_name: name,
    phone,
    comment: $('customerComment').value.trim() || null,
    location: state.location,
    promo_code: state.promoCode || null,
    created_at_client: new Date().toISOString(),
  };

  submitOrderBtn.disabled = true;
  submitOrderBtn.textContent = '⏳ Отправляем...';

  try {
    if (tg) {
      tg.sendData(JSON.stringify(payload));
      tg.close();
    } else {
      alert('Заказ: ' + JSON.stringify(payload, null, 2));
      submitOrderBtn.disabled = false;
      submitOrderBtn.textContent = '✅ Подтвердить заказ';
    }
  } catch (e) {
    console.error(e);
    submitOrderBtn.disabled = false;
    submitOrderBtn.textContent = '✅ Подтвердить заказ';
    alert('Ошибка при отправке заказа.');
  }
});

// ============================================================
// Filter Modal
// ============================================================
filterBtn.addEventListener('click', () => { filterModal.style.display = 'flex'; });
closeFilterBtn.addEventListener('click', () => { filterModal.style.display = 'none'; });
filterModal.addEventListener('click', e => { if (e.target === filterModal) filterModal.style.display = 'none'; });
checkoutModal.addEventListener('click', e => { if (e.target === checkoutModal) checkoutModal.style.display = 'none'; });

applyFilter.addEventListener('click', () => {
  const selected = document.querySelector('input[name="sort"]:checked');
  state.sortBy = selected ? selected.value : '';
  filterModal.style.display = 'none';
  renderFoods();
});

// ============================================================
// Search
// ============================================================
let searchTimer;
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.search = searchInput.value;
    renderFoods();
  }, 250);
});

// ============================================================
// Helpers
// ============================================================
function fmt(n) {
  return Math.round(n).toLocaleString('ru-RU') + ' сум';
}

function escHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

// ============================================================
// Start
// ============================================================
init();
