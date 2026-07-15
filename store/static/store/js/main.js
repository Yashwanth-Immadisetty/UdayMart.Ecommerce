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
  if (searchInput) {
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        this.closest('form').submit();
      }
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
