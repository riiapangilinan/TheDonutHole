document.addEventListener('DOMContentLoaded', function () {
    const cartIcon = document.getElementById('cartIcon');
    const cartSidebar = document.getElementById('cartSidebar');
    const cartOverlay = document.getElementById('cartOverlay');
    const closeCartBtn = document.querySelector('.close-cart');
    const cartItemsContainer = document.getElementById('cartItems');
    const cartTotalElement = document.getElementById('cartTotal');
    const cartBadge = document.getElementById('cartBadge');
    const checkoutBtn = document.getElementById('checkoutBtn');

    let currentCart = {};

    function toggleCart() {
        cartSidebar.classList.toggle('active');
        cartOverlay.classList.toggle('active');
        document.body.classList.toggle('no-scroll');
    }

    function updateCartUI(cartData) {
        currentCart = cartData.cart || {};
        const totalItems = cartData.cart_count || 0;
        const totalValue = cartData.cart_total || 0;

        cartBadge.textContent = totalItems;
        cartBadge.style.display = totalItems > 0 ? 'block' : 'none';
        cartTotalElement.textContent = `₱${totalValue.toFixed(2)}`;

        renderCartItems();
    }

    function renderCartItems() {
        const cartItems = Object.values(currentCart);
        if (cartItems.length === 0) {
            cartItemsContainer.innerHTML = '<p class="empty-cart">Your cart is empty</p>';
            return;
        }

        cartItemsContainer.innerHTML = cartItems.map(item => `
            <div class="cart-item" data-id="${item.id}">
                <div class="cart-item-info">
                    <h4>${item.name}</h4>
                    <p>₱${item.price.toFixed(2)} x ${item.quantity}</p>
                </div>
                <div class="cart-item-actions">
                    <button class="decrease-quantity" data-item-id="${item.id}">-</button>
                    <span>${item.quantity}</span>
                    <button class="increase-quantity" data-item-id="${item.id}">+</button>
                    <button class="remove-item" data-item-id="${item.id}">&times;</button>
                </div>
            </div>
        `).join('');
    }

    async function handleCartAction(endpoint, itemId, action) {
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_id: itemId, action: action })
            });
            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            if (data.success) {
                updateCartUI(data);
            } else {
                console.error('Cart action failed:', data.error);
            }
        } catch (error) {
            console.error('Error during cart action:', error);
        }
    }

    cartItemsContainer.addEventListener('click', function(event) {
        const target = event.target;
        const itemId = target.dataset.itemId;

        if (target.classList.contains('increase-quantity')) {
            handleCartAction('/update_cart', itemId, 'increase');
        } else if (target.classList.contains('decrease-quantity')) {
            handleCartAction('/update_cart', itemId, 'decrease');
        } else if (target.classList.contains('remove-item')) {
            handleCartAction('/update_cart', itemId, 'remove');
        }
    });

    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', async function () {
            const itemId = parseInt(this.dataset.id);
            
            try {
                const response = await fetch('/add_to_cart', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: itemId })
                });

                if (!response.ok) {
                    if (response.redirected) {
                        window.location.href = response.url;
                        return;
                    }
                    throw new Error('Failed to add to cart');
                }
                
                const data = await response.json();
                if (data.success) {
                    updateCartUI(data);
                    toggleCart();
                } else {
                    console.error('Failed to add item:', data.error);
                }
            } catch (error) {
                console.error('Error adding item to cart:', error);
            }
        });
    });

    checkoutBtn.addEventListener('click', function () {
        if (Object.keys(currentCart).length === 0) {
            alert('Your cart is empty!');
            return;
        }
        window.location.href = '/checkout';
    });

    cartIcon.addEventListener('click', toggleCart);
    closeCartBtn.addEventListener('click', toggleCart);
    cartOverlay.addEventListener('click', toggleCart);

    // Initial load of the cart from the session on page load
    function loadCartOnPageLoad() {
        fetch('/cart')
            .then(response => {
                if (!response.ok) {
                    return Promise.reject('Not logged in or cart is empty');
                }
                return response.text();
            })
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const cartRows = doc.querySelectorAll('table tbody tr');
                
                if (cartRows.length === 0) {
                    updateCartUI({ cart: {}, cart_count: 0, cart_total: 0 });
                    return;
                }

                const cartData = { cart: {}, cart_count: 0, cart_total: 0 };
                let totalItems = 0;
                let totalValue = 0;

                cartRows.forEach(row => {
                    const name = row.cells[0].textContent.trim();
                    const priceText = row.cells[1].textContent.trim().replace('₱', '');
                    const quantityText = row.cells[2].textContent.trim();
                    const id = row.querySelector('input[name="item_id"]').value;

                    const price = parseFloat(priceText);
                    const quantity = parseInt(quantityText, 10);

                    cartData.cart[id] = { id, name, price, quantity };
                    totalItems += quantity;
                    totalValue += price * quantity;
                });

                cartData.cart_count = totalItems;
                cartData.cart_total = totalValue;
                
                updateCartUI(cartData);
            })
            .catch(err => {
                console.log("Cart pre-load skipped (user may not be logged in).");
                updateCartUI({ cart: {}, cart_count: 0, cart_total: 0 });
            });
    }

    loadCartOnPageLoad();
});
