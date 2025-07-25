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

    // Event delegation for cart item actions
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
                    // If not logged in, the server will redirect, handle this gracefully
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
        // The cart is already synced with the server, so just redirect
        window.location.href = '/checkout';
    });

    cartIcon.addEventListener('click', toggleCart);
    closeCartBtn.addEventListener('click', toggleCart);
    cartOverlay.addEventListener('click', toggleCart);

    // Initial load of the cart from the session on page load
    // This assumes the cart is loaded into the session by Flask on login
    fetch('/cart')
        .then(response => response.text()) // Get HTML content
        .then(html => {
            // This is a trick to get the cart data without a dedicated API endpoint
            // It relies on the cart data being available in the session when the page loads
            // A better approach would be a dedicated '/get_cart' endpoint
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            // Assuming the cart data is somehow embedded or can be inferred
            // For now, we'll just render what's in the session on the backend
        })
        .catch(err => console.error("Could not pre-load cart state.", err));
});
