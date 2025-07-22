document.addEventListener('DOMContentLoaded', function () {
  let cart = JSON.parse(sessionStorage.getItem('cart')) || [];

  const cartIcon = document.getElementById('cartIcon');
  const cartSidebar = document.getElementById('cartSidebar');
  const cartOverlay = document.getElementById('cartOverlay');
  const closeCartBtn = document.querySelector('.close-cart');
  const cartItemsContainer = document.getElementById('cartItems');
  const cartTotalElement = document.getElementById('cartTotal');
  const cartBadge = document.getElementById('cartBadge');
  const checkoutBtn = document.getElementById('checkoutBtn');

  function toggleCart() {
    cartSidebar.classList.toggle('active');
    cartOverlay.classList.toggle('active');
    document.body.classList.toggle('no-scroll');
  }

  function updateCartBadge() {
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    cartBadge.textContent = totalItems;
    cartBadge.style.display = totalItems > 0 ? 'block' : 'none';
  }

  function updateCartTotal() {
    const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    cartTotalElement.textContent = `₱${total.toFixed(2)}`;
  }

  function renderCartItems() {
    if (cart.length === 0) {
      cartItemsContainer.innerHTML = '<p class="empty-cart">Your cart is empty</p>';
      return;
    }

    cartItemsContainer.innerHTML = cart.map(item => `
      <div class="cart-item" data-id="${item.id}">
        <div class="cart-item-info">
          <h4>${item.name}</h4>
          <p>₱${item.price.toFixed(2)} x ${item.quantity}</p>
        </div>
        <div class="cart-item-actions">
          <button class="decrease-quantity">-</button>
          <span>${item.quantity}</span>
          <button class="increase-quantity">+</button>
          <button class="remove-item">&times;</button>
        </div>
      </div>
    `).join('');

    document.querySelectorAll('.increase-quantity').forEach(button => {
      button.addEventListener('click', function () {
        const itemId = parseInt(this.closest('.cart-item').dataset.id);
        const item = cart.find(i => i.id === itemId);
        if (item) {
          item.quantity++;
          saveCart();
        }
      });
    });

    document.querySelectorAll('.decrease-quantity').forEach(button => {
      button.addEventListener('click', function () {
        const itemId = parseInt(this.closest('.cart-item').dataset.id);
        const index = cart.findIndex(i => i.id === itemId);
        if (index !== -1) {
          if (cart[index].quantity > 1) {
            cart[index].quantity--;
          } else {
            cart.splice(index, 1);
          }
          saveCart();
        }
      });
    });

    document.querySelectorAll('.remove-item').forEach(button => {
      button.addEventListener('click', function () {
        const itemId = parseInt(this.closest('.cart-item').dataset.id);
        cart = cart.filter(item => item.id !== itemId);
        saveCart();
      });
    });
  }

  function saveCart() {
    sessionStorage.setItem('cart', JSON.stringify(cart));
    syncCartWithServer();
    renderCartItems();
    updateCartTotal();
    updateCartBadge();
  }

  function syncCartWithServer() {
    fetch('/save-cart-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cart: cart })
    });
  }

  document.querySelectorAll('.add-to-cart').forEach(button => {
    button.addEventListener('click', function () {
      const itemId = parseInt(this.dataset.id);
      const name = this.dataset.name;
      const price = parseFloat(this.dataset.price);
      const image = this.dataset.image;

      const existingItem = cart.find(item => item.id === itemId);
      if (existingItem) {
        existingItem.quantity++;
      } else {
        cart.push({
          id: itemId,
          name: name,
          price: price,
          image: image || '',
          quantity: 1
        });
      }

      saveCart();
      toggleCart();
    });
  });

  checkoutBtn.addEventListener('click', function () {
    if (cart.length === 0) {
      alert('Your cart is empty!');
      return;
    }

    syncCartWithServer();
    window.location.href = '/checkout';
  });

  cartIcon.addEventListener('click', toggleCart);
  closeCartBtn.addEventListener('click', toggleCart);
  cartOverlay.addEventListener('click', toggleCart);

  updateCartBadge();
  renderCartItems();
  updateCartTotal();
});
