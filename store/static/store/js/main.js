// ═══════════════════════════════════════════
// UDAY MART – Main JavaScript
// ═══════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function () {

  // ── Auto-dismiss messages after 4 seconds ──
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 500);
    }, 4000);
  });

  // ── Search bar category filter enhancement ──
  const searchInput = document.querySelector('.search-input');
  const searchForm = document.querySelector('.search-bar');
  const suggestions = document.getElementById('search-suggestions');
  let searchTimer;
  let activeSuggestion = -1;

  const hideSuggestions = () => {
    if (suggestions) {
      suggestions.hidden = true;
      suggestions.replaceChildren();
    }
    activeSuggestion = -1;
  };

  if (searchInput && searchForm && suggestions) {
    const renderSuggestions = (results, query) => {
      suggestions.replaceChildren();
      if (!results.length) {
        const empty = document.createElement('div');
        empty.className = 'search-suggestion-empty';
        empty.textContent = `No products found for "${query}"`;
        suggestions.appendChild(empty);
      } else {
        results.forEach((result) => {
          const link = document.createElement('a');
          link.className = 'search-suggestion';
          link.href = result.url;
          link.setAttribute('role', 'option');
          if (result.image) {
            const image = document.createElement('img');
            image.src = result.image;
            image.alt = '';
            link.appendChild(image);
          } else {
            const icon = document.createElement('span');
            icon.className = 'search-suggestion-icon';
            icon.textContent = '🛒';
            link.appendChild(icon);
          }
          const text = document.createElement('span');
          const name = document.createElement('strong');
          name.textContent = result.name;
          const brand = document.createElement('span');
          brand.textContent = result.brand;
          text.append(name, brand);
          link.appendChild(text);
          suggestions.appendChild(link);
        });
      }
      suggestions.hidden = false;
    };

    searchInput.addEventListener('input', function () {
      const query = this.value.trim();
      clearTimeout(searchTimer);
      if (query.length < 2) {
        hideSuggestions();
        return;
      }
      searchTimer = setTimeout(async () => {
        const params = new URLSearchParams({ q: query });
        const category = searchForm.querySelector('[name="cat"]').value;
        if (category) params.set('cat', category);
        try {
          const response = await fetch(`/search/suggestions/?${params}`);
          if (!response.ok) throw new Error('Search unavailable');
          const data = await response.json();
          if (searchInput.value.trim() === query) renderSuggestions(data.results, query);
        } catch (error) {
          hideSuggestions();
        }
      }, 250);
    });

    searchInput.addEventListener('keydown', function (event) {
      const items = Array.from(suggestions.querySelectorAll('.search-suggestion'));
      if (event.key === 'ArrowDown' && items.length) {
        event.preventDefault();
        activeSuggestion = Math.min(activeSuggestion + 1, items.length - 1);
      } else if (event.key === 'ArrowUp' && items.length) {
        event.preventDefault();
        activeSuggestion = Math.max(activeSuggestion - 1, 0);
      } else if (event.key === 'Escape') {
        hideSuggestions();
        return;
      } else if (event.key === 'Enter' && activeSuggestion >= 0) {
        event.preventDefault();
        items[activeSuggestion].click();
        return;
      } else {
        return;
      }
      items.forEach((item, index) => item.classList.toggle('is-active', index === activeSuggestion));
      items[activeSuggestion].scrollIntoView({ block: 'nearest' });
    });

    document.addEventListener('click', (event) => {
      if (!searchForm.contains(event.target)) hideSuggestions();
    });
  }

  // ── Back to top smooth scroll ──
  const backToTop = document.querySelector('.back-to-top');
  if (backToTop) {
    backToTop.addEventListener('click', function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ── Add to cart animation feedback ──
  document.querySelectorAll('.add-to-cart-form').forEach(form => {
    form.addEventListener('submit', function () {
      const btn = this.querySelector('.btn-add-cart');
      if (btn) {
        btn.textContent = '✓ Added!';
        btn.style.background = '#067d62';
      }
    });
  });

  // ── Cart quantity auto-submit on change ──
  document.querySelectorAll('.qty-select-sm').forEach(select => {
    select.addEventListener('change', function () {
      this.closest('form').submit();
    });
  });

  // ── Sticky header shadow on scroll ──
  const header = document.querySelector('.header');
  if (header) {
    window.addEventListener('scroll', function () {
      if (window.scrollY > 10) {
        header.style.boxShadow = '0 4px 20px rgba(0,0,0,0.5)';
      } else {
        header.style.boxShadow = '0 2px 12px rgba(0,0,0,0.4)';
      }
    });
  }

  // ── Payment option visual selection ──
  document.querySelectorAll('.payment-option').forEach(option => {
    const radio = option.querySelector('input[type="radio"]');
    if (radio && radio.checked) {
      option.style.borderColor = 'var(--primary)';
      option.style.background = 'var(--primary-light)';
    }
    option.addEventListener('click', function () {
      document.querySelectorAll('.payment-option').forEach(o => {
        o.style.borderColor = '';
        o.style.background = '';
      });
      this.style.borderColor = 'var(--primary)';
      this.style.background = 'var(--primary-light)';
    });
  });

  // ── Product image zoom on hover (detail page) ──
  const mainImage = document.getElementById('mainImage');
  if (mainImage) {
    mainImage.addEventListener('mousemove', function (e) {
      const rect = this.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      this.style.transformOrigin = `${x}% ${y}%`;
      this.style.transform = 'scale(1.4)';
    });
    mainImage.addEventListener('mouseleave', function () {
      this.style.transform = 'scale(1)';
    });
  }

  // ── Star rating interactive (review form) ──
  const ratingSelect = document.querySelector('select[name="rating"]');
  if (ratingSelect) {
    ratingSelect.addEventListener('change', function () {
      console.log('Rating selected:', this.value);
    });
  }

  // ── Navbar active link highlight ──
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.style.background = 'rgba(255,255,255,0.2)';
      link.style.fontWeight = '700';
    }
  });

  // ── Category grid animate on scroll ──
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          entry.target.style.animationDelay = `${i * 0.05}s`;
          entry.target.classList.add('animate-in');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.product-card, .cat-card').forEach(el => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      observer.observe(el);
    });
  }

  // Small helper to animate observed elements
  document.querySelectorAll('.product-card, .cat-card').forEach((el, i) => {
    setTimeout(() => {
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    }, 100 + i * 50);
  });

});

// ── Global: Confirm before removing cart item ──
function confirmRemove(event, message) {
  if (!confirm(message || 'Remove this item from cart?')) {
    event.preventDefault();
  }
}
