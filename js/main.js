/* =====================================================================
   Tatiane Cavalcanti — interações (vanilla, sem dependências)
   Progressive enhancement: html.js é marcado no <head>; sem JS a página
   já nasce completa. Aqui só entram animações e conveniências.
   ===================================================================== */
(function () {
  'use strict';

  var root = document.documentElement;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hero = document.querySelector('.hero');
  var revealEls = document.querySelectorAll('[data-reveal]');

  /* ---------- 1. entrada do hero ---------- */
  function enterHero() {
    if (!hero) return;
    // dois rAF: garante que o estado inicial (opacity 0) foi pintado antes de transicionar
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { hero.classList.add('in'); });
    });
  }

  /* ---------- 2. reveal on scroll ---------- */
  function setupReveal() {
    if (!revealEls.length) return;
    if (reduce || !('IntersectionObserver' in window)) {
      revealEls.forEach(function (el) { el.classList.add('in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('in');
        io.unobserve(entry.target); // revela uma vez só
      });
    // margem inferior pequena e fixa: o último elemento da página (footer) precisa conseguir cruzá-la
    }, { threshold: 0.05, rootMargin: '0px 0px -24px 0px' });
    revealEls.forEach(function (el) { io.observe(el); });
  }

  /* ---------- 3. parallax leve na foto (só transform, scroll passivo + rAF) ---------- */
  function setupParallax() {
    if (reduce || !hero) return;
    var pic = hero.querySelector('.hero__pic');
    if (!pic) return;
    var ticking = false;
    function update() {
      ticking = false;
      var y = window.scrollY || window.pageYOffset;
      if (y > 700) return; // hero já saiu da tela
      pic.style.transform = 'translate3d(0,' + (y * -0.08).toFixed(1) + 'px,0)';
    }
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
  }

  /* ---------- 4. feedback de toque nos botões ---------- */
  function setupPress() {
    var buttons = document.querySelectorAll('.btn');
    function release(e) { e.currentTarget.classList.remove('is-pressed'); }
    buttons.forEach(function (btn) {
      btn.addEventListener('pointerdown', function () { btn.classList.add('is-pressed'); }, { passive: true });
      ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (ev) {
        btn.addEventListener(ev, release, { passive: true });
      });
    });
  }

  /* ---------- 5. toast ---------- */
  var toast = document.getElementById('toast');
  var toastTimer = null;
  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.classList.remove('show');
      // limpa depois do fade (.25s) para a região aria-live não guardar texto obsoleto
      setTimeout(function () { if (!toast.classList.contains('show')) toast.textContent = ''; }, 300);
    }, 2000);
  }

  /* ---------- 6. copiar contato ---------- */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    // fallback (http / navegadores antigos)
    return new Promise(function (resolve, reject) {
      var prev = document.activeElement;
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      ta.setSelectionRange(0, ta.value.length); // iOS
      try { document.execCommand('copy') ? resolve() : reject(); }
      catch (err) { reject(err); }
      document.body.removeChild(ta);
      if (prev && prev.focus) prev.focus();
    });
  }
  function setupCopy() {
    var buttons = document.querySelectorAll('[data-copy]');
    buttons.forEach(function (btn) {
      btn.hidden = false;
      btn.addEventListener('click', function () {
        copyText(btn.getAttribute('data-copy')).then(function () {
          btn.classList.add('is-done');
          showToast('Copiado!');
          setTimeout(function () { btn.classList.remove('is-done'); }, 1500);
        }, function () {
          showToast('Não foi possível copiar');
        });
      });
    });
  }

  /* ---------- 7. compartilhar cartão ---------- */
  function setupShare() {
    var btn = document.getElementById('share');
    if (!btn) return;
    var data = {
      title: document.title,
      text: 'Tatiane Cavalcanti — UGC Creator e Furo Humanizado',
      url: location.href.split('#')[0]
    };
    btn.hidden = false;
    btn.addEventListener('click', function () {
      if (navigator.share) {
        navigator.share(data).catch(function () { /* usuário cancelou */ });
      } else {
        copyText(data.url).then(function () { showToast('Link copiado!'); },
                                function () { showToast('Não foi possível copiar'); });
      }
    });
  }

  /* ---------- init ---------- */
  function init() {
    root.classList.add('ready'); // cancela a rede de segurança do <head>
    try {
      if (reduce) root.classList.add('reduce-motion');
      enterHero();
      setupReveal();
      setupParallax();
      setupPress();
      setupCopy();
      setupShare();
    } catch (err) {
      root.classList.remove('js'); // qualquer erro: página estática completa
      throw err;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
