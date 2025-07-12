document.addEventListener('DOMContentLoaded', function() {
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
      button.addEventListener('click', function() {
        const itemId = parseInt(this.closest('.cart-item').dataset.id);
        const item = cart.find(i => i.id === itemId);
        if (item) {
          item.quantity++;
          saveCart();
          renderCartItems();
          updateCartTotal();
          updateCartBadge();
        }
      });
    });
    
    document.querySelectorAll('.decrease-quantity').forEach(button => {
      button.addEventListener('click', function() {
        const itemId = parseInt(this.closest('.cart-item').dataset.id);
        const itemIndex = cart.findIndex(i => i.id === itemId);
        if (itemIndex !== -1) {
          if (cart[itemIndex].quantity > 1) {
            cart[itemIndex].quantity--;
          } else {
            cart.splice(itemIndex, 1);
          }
          saveCart();
          renderCartItems();
          updateCartTotal();
          updateCartBadge();
        }
      });
    });
    
    document.querySelectorAll('.remove-item').forEach(button => {
      button.addEventListener('click', function() {
        const itemId = parseInt(this.closest('.cart-item').dataset.id);
        cart = cart.filter(item => item.id !== itemId);
        saveCart();
        renderCartItems();
        updateCartTotal();
        updateCartBadge();
      });
    });
  }
  
  function saveCart() {
    sessionStorage.setItem('cart', JSON.stringify(cart));
  }
  
  document.querySelectorAll('.add-to-cart').forEach(button => {
    button.addEventListener('click', function() {
      const itemId = parseInt(this.dataset.id);
      const menuItem = menuItems.find(item => item.id === itemId);
      
      if (menuItem) {
        const existingItem = cart.find(item => item.id === itemId);
        
        if (existingItem) {
          existingItem.quantity++;
        } else {
          cart.push({
            id: menuItem.id,
            name: menuItem.name,
            price: menuItem.price,
            image: menuItem.image,
            quantity: 1
          });
        }
        
        saveCart();
        renderCartItems();
        updateCartTotal();
        updateCartBadge();
        toggleCart(); 
      }
    });
  });
  
  checkoutBtn.addEventListener('click', function() {
    if (cart.length === 0) {
      alert('Your cart is empty!');
      return;
    }
    
    alert('Proceeding to checkout!');
  });
  
  cartIcon.addEventListener('click', toggleCart);
  closeCartBtn.addEventListener('click', toggleCart);
  cartOverlay.addEventListener('click', toggleCart);
  
  updateCartBadge();
  renderCartItems();
  updateCartTotal();
});

const menuItems = [
  {
        'id': 1,
        'name': 'Original Glazed',
        'price': 35.00,
        'image': 'menu-1.png',
        'description': 'A timeless classic with a golden, melt-in-your-mouth glaze that’s perfectly sweet, fluffy.'
    },
    {
        'id': 2,
        'name': 'Hazelnut Drizzle',
        'price': 70.00,
        'image': 'menu-2.png',
        'description': 'Rich, roasted hazelnut glaze cascading over a delicate donut.'
    },
    {
        'id': 3,
        'name': 'Creme Brulee',
        'price': 80.00,
        'image': 'menu-3.png',
        'description': 'Luscious, custard-filled delight topped with a caramelized sugar that cracks perfectly with every bite.'
    },
    {
        'id': 4,
        'name': 'Orange Pistachio',
        'price': 80.00,
        'image': 'menu-4.png',
        'description': 'Zesty orange-infused glaze, topped with crunchy crushed pistachios.'
    },
    {
        'id': 5,
        'name': 'Fruit Punch Summer',
        'price': 70.00,
        'image': 'menu-5.png',
        'description': 'A sun-kissed celebration of juicy strawberries, blueberries, and raspberries for the summer.'
    },
    {
        'id': 6,
        'name': 'Bundles',
        'price': 150.00,
        'image': 'menu-6.png',
        'description': 'Build-your-own boxes—perfect for gifting, parties, or treating yourself to a sweet sampler.'
    }
  ];
