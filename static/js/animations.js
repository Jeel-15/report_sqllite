/* ═══════════════════════════════════════════════════════════════════════════════
   ANIMATIONS.JS - GSAP Animation Manager
   ═══════════════════════════════════════════════════════════════════════════════ */

class AnimationManager {
  constructor() {
    // Check if GSAP is available
    if (typeof gsap === 'undefined') {
      console.warn('GSAP not loaded. Animations will be skipped.');
      return;
    }

    // Register ScrollTrigger plugin
    if (typeof ScrollTrigger !== 'undefined') {
      gsap.registerPlugin(ScrollTrigger);
    }

    this.init();
  }

  init() {
    this.setupFadeUpAnimation();
    this.setupScaleInAnimation();
    this.setupCounterAnimation();
  }

  setupFadeUpAnimation() {
    // Animate elements with .fade-up class when they come into view
    const fadeElements = document.querySelectorAll('.fade-up');
    
    fadeElements.forEach((el, index) => {
      if (typeof gsap === 'undefined') return;
      
      gsap.to(el, {
        scrollTrigger: {
          trigger: el,
          start: 'top 80%',
          end: 'top 50%',
          toggleActions: 'play none none none',
          once: true
        },
        opacity: 1,
        y: 0,
        duration: 0.6,
        delay: index * 0.1,
        ease: 'power2.out'
      });
    });
  }

  setupScaleInAnimation() {
    // Animate elements with .scale-up class when they come into view
    const scaleElements = document.querySelectorAll('.scale-up');
    
    scaleElements.forEach((el, index) => {
      if (typeof gsap === 'undefined') return;
      
      gsap.to(el, {
        scrollTrigger: {
          trigger: el,
          start: 'top 80%',
          toggleActions: 'play none none none',
          once: true
        },
        opacity: 1,
        scale: 1,
        duration: 0.6,
        delay: index * 0.1,
        ease: 'power2.out'
      });
    });
  }

  setupCounterAnimation() {
    // Animate counters (numbers that count up)
    const counters = document.querySelectorAll('[data-counter]');
    
    counters.forEach(counter => {
      if (typeof gsap === 'undefined') return;
      
      const targetValue = parseInt(counter.dataset.counter);
      const obj = { value: 0 };

      gsap.to(obj, {
        scrollTrigger: {
          trigger: counter,
          start: 'top 80%',
          toggleActions: 'play none none none',
          once: true
        },
        value: targetValue,
        duration: 2,
        ease: 'power2.out',
        onUpdate: function() {
          counter.innerText = Math.round(obj.value).toLocaleString();
        }
      });
    });
  }

  // Helper: Animate element on hover
  static animateOnHover(selector, toVars, duration = 0.3) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(el => {
      if (typeof gsap === 'undefined') return;
      
      el.addEventListener('mouseenter', () => {
        gsap.to(el, { ...toVars, duration });
      });
      
      el.addEventListener('mouseleave', () => {
        // Reset to original state
        gsap.to(el, { ...toVars, duration, reverse: true });
      });
    });
  }

  // Helper: Stagger animation
  static staggerElements(selector, toVars, staggerAmount = 0.1) {
    const elements = document.querySelectorAll(selector);
    if (typeof gsap === 'undefined') return;
    
    gsap.to(elements, {
      ...toVars,
      stagger: staggerAmount,
      ease: 'power2.out'
    });
  }

  // Helper: Timeline animation
  static createTimeline() {
    if (typeof gsap === 'undefined') {
      console.warn('GSAP not available');
      return null;
    }
    return gsap.timeline();
  }
}

// Initialize animation manager when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new AnimationManager();
  });
} else {
  new AnimationManager();
}

/* ═════════════════════════════════════════════════════════════════════════════
   UTILITY FUNCTIONS FOR COMMON ANIMATIONS
   ═════════════════════════════════════════════════════════════════════════════ */

// Pulse animation utility
function animatePulse(selector, duration = 1) {
  const elements = document.querySelectorAll(selector);
  elements.forEach(el => {
    el.style.animation = `pulse ${duration}s ease-in-out infinite`;
  });
}

// Bounce animation utility
function animateBounce(selector) {
  const elements = document.querySelectorAll(selector);
  elements.forEach(el => {
    el.style.animation = 'bounce 0.6s ease infinite';
  });
}

// Fade in animation utility
function animateFadeIn(element, duration = 0.3, delay = 0) {
  if (typeof gsap === 'undefined') {
    element.style.opacity = '1';
    return;
  }
  
  gsap.to(element, {
    opacity: 1,
    duration,
    delay,
    ease: 'power2.out'
  });
}

// Fade out animation utility
function animateFadeOut(element, duration = 0.3, delay = 0) {
  if (typeof gsap === 'undefined') {
    element.style.opacity = '0';
    return;
  }
  
  gsap.to(element, {
    opacity: 0,
    duration,
    delay,
    ease: 'power2.out'
  });
}

// Slide up animation utility
function animateSlideUp(element, duration = 0.4, delay = 0) {
  if (typeof gsap === 'undefined') {
    element.style.transform = 'translateY(0)';
    element.style.opacity = '1';
    return;
  }
  
  gsap.to(element, {
    y: 0,
    opacity: 1,
    duration,
    delay,
    ease: 'power2.out'
  });
}

// Slide down animation utility
function animateSlideDown(element, duration = 0.4, delay = 0) {
  if (typeof gsap === 'undefined') {
    element.style.transform = 'translateY(0)';
    element.style.opacity = '1';
    return;
  }
  
  gsap.to(element, {
    y: 0,
    opacity: 1,
    duration,
    delay,
    ease: 'power2.out'
  });
}

// Scale animation utility
function animateScale(element, scale = 1, duration = 0.3) {
  if (typeof gsap === 'undefined') {
    element.style.transform = `scale(${scale})`;
    return;
  }
  
  gsap.to(element, {
    scale,
    duration,
    ease: 'power2.out'
  });
}
