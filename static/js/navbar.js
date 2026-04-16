/* ═══════════════════════════════════════════════════════════════════════════════
   NAVBAR.JS - Navbar Controller & UI Management
   ═══════════════════════════════════════════════════════════════════════════════ */

class NavbarController {
  constructor() {
    this.navbarEl = document.getElementById('nav') || document.getElementById('mainNavbar');
    this.menuToggle = document.getElementById('nav-menu-toggle') || document.querySelector('.nav-menu-toggle');
    this.menuDrawer = document.getElementById('nav-menu-drawer') || document.querySelector('.nav-menu-drawer');
    this.menuLinks = document.querySelectorAll('.nav-menu-link, .nav-menu-cta');
    
    // Scroll threshold values
    this.MORPH_IN_Y = 88;
    this.MORPH_OUT_Y = 56;
    this.lastScrollY = 0;
    this.isMenuOpen = false;
    this.rafPending = false;
    
    this.init();
  }

  init() {
    if (!this.navbarEl) return;

    // Scroll listener (rAF-throttled for smoother animation)
    window.addEventListener('scroll', () => this.scheduleScrollUpdate(), { passive: true });
    
    // Mobile menu toggle
    if (this.menuToggle) {
      this.menuToggle.addEventListener('click', () => this.toggleMenu());
    }
    
    // Close menu when clicking links
    this.menuLinks.forEach(link => {
      link.addEventListener('click', () => this.closeMenu());
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', (e) => this.handleOutsideClick(e));
    
    // Custom cursor setup
    this.setupCustomCursor();
    
    // Scroll progress bar setup
    this.setupProgressBar();

    // Apply correct navbar state immediately on load.
    this.handleScroll();
  }

  scheduleScrollUpdate() {
    if (this.rafPending) return;
    this.rafPending = true;
    window.requestAnimationFrame(() => {
      this.rafPending = false;
      this.handleScroll();
    });
  }

  handleScroll() {
    if (!this.navbarEl) return;

    const scrollY = window.scrollY;
    
    if (scrollY > this.MORPH_IN_Y && !this.navbarEl.classList.contains('scrolled')) {
      this.morphNavbar();
    } else if (scrollY < this.MORPH_OUT_Y && this.navbarEl.classList.contains('scrolled')) {
      this.unmorphNavbar();
    }
    
    this.lastScrollY = scrollY;
    this.updateProgressBar();
  }

  morphNavbar() {
    // Add morphed state when scrolling past threshold
    this.navbarEl.classList.add('scrolled');
    this.navbarEl.classList.add('morphed');
  }

  unmorphNavbar() {
    // Remove morphed state when scrolling back up
    this.navbarEl.classList.remove('scrolled');
    this.navbarEl.classList.remove('morphed');
  }

  toggleMenu() {
    if (this.isMenuOpen) {
      this.closeMenu();
    } else {
      this.openMenu();
    }
  }

  openMenu() {
    this.isMenuOpen = true;
    this.menuToggle.classList.add('active');
    this.menuDrawer.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  closeMenu() {
    this.isMenuOpen = false;
    this.menuToggle.classList.remove('active');
    this.menuDrawer.classList.remove('active');
    document.body.style.overflow = '';
  }

  handleOutsideClick(e) {
    if (!this.menuToggle || !this.menuDrawer) return;
    
    const isClickInsideMenu = this.menuDrawer.contains(e.target);
    const isClickOnToggle = this.menuToggle.contains(e.target);
    
    if (!isClickInsideMenu && !isClickOnToggle && this.isMenuOpen) {
      this.closeMenu();
    }
  }

  setupCustomCursor() {
    const cursor = document.getElementById('cursor');
    const cursorRing = document.getElementById('cursor-ring');
    
    if (!cursor || !cursorRing) return;

    let cursorX = 0;
    let cursorY = 0;
    let cursorRafPending = false;

    const flushCursorPosition = () => {
      cursorRafPending = false;
      cursor.style.transform = `translate(${cursorX - 5}px, ${cursorY - 5}px)`;
      cursorRing.style.transform = `translate(${cursorX - 18}px, ${cursorY - 18}px)`;
    };

    window.addEventListener('mousemove', (e) => {
      cursorX = e.clientX;
      cursorY = e.clientY;

      if (cursorRafPending) return;
      cursorRafPending = true;
      window.requestAnimationFrame(flushCursorPosition);
    });
    
    // Enlarge cursor on interactive elements
    const interactiveElements = document.querySelectorAll(
      'a, button, input, textarea, select, [role="button"], .cursor-hover'
    );
    
    interactiveElements.forEach(el => {
      el.addEventListener('mouseenter', () => cursorRing.classList.add('hovered'));
      el.addEventListener('mouseleave', () => cursorRing.classList.remove('hovered'));
    });
    
    // Hide custom cursor on touch events
    document.addEventListener('touchstart', () => {
      cursor.style.display = 'none';
      cursorRing.style.display = 'none';
    });
  }

  setupProgressBar() {
    const progressBar = document.getElementById('progress');
    if (!progressBar) return;

    progressBar.style.transformOrigin = '0 50%';
    
    this.updateProgressBar = function() {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrollPercent = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      progressBar.style.transform = `scaleX(${scrollPercent / 100})`;
    };
  }

  updateProgressBar() {
    // Placeholder: will be overwritten in setupProgressBar
  }
}

// Initialize navbar controller when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new NavbarController();
  });
} else {
  new NavbarController();
}
