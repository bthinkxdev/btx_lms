(function () {
  'use strict';

  var refCount = 0;
  var root = null;
  var msgEl = null;

  function ensureRoot() {
    if (root) return;
    root = document.createElement('div');
    root.id = 'lms-global-loader';
    root.setAttribute('role', 'status');
    root.setAttribute('aria-live', 'polite');
    root.setAttribute('aria-hidden', 'true');
    root.innerHTML =
      '<div class="lms-global-loader-backdrop" aria-hidden="true"></div>' +
      '<div class="lms-global-loader-panel">' +
      '<div class="lms-global-loader-spinner" aria-hidden="true"></div>' +
      '<p class="lms-global-loader-msg"></p>' +
      '</div>';
    document.body.appendChild(root);
    msgEl = root.querySelector('.lms-global-loader-msg');
  }

  function show(message) {
    ensureRoot();
    refCount += 1;
    if (msgEl) {
      msgEl.textContent = message || 'Please wait…';
    }
    root.classList.add('is-visible');
    root.setAttribute('aria-hidden', 'false');
    root.setAttribute('aria-busy', 'true');
    document.body.classList.add('lms-loader-active');
  }

  function hide() {
    refCount = Math.max(0, refCount - 1);
    if (refCount === 0 && root) {
      root.classList.remove('is-visible');
      root.setAttribute('aria-hidden', 'true');
      root.removeAttribute('aria-busy');
      document.body.classList.remove('lms-loader-active');
    }
  }

  /** Reset overlay (e.g. after navigation quirks). */
  function forceHide() {
    refCount = 0;
    if (root) {
      root.classList.remove('is-visible');
      root.setAttribute('aria-hidden', 'true');
      root.removeAttribute('aria-busy');
    }
    document.body.classList.remove('lms-loader-active');
  }

  window.LmsLoader = {
    show: show,
    hide: hide,
    forceHide: forceHide
  };

  function formSkipsLoader(form) {
    var id = form.id || '';
    if (
      id === 'login-email-form' ||
      id === 'login-otp-form' ||
      id === 'lead-capture-form'
    ) {
      return true;
    }
    if (form.classList.contains('js-section-profile-form')) {
      return true;
    }
    if (form.hasAttribute('data-no-loader')) {
      return true;
    }
    var method = (form.getAttribute('method') || 'get').toLowerCase();
    if (method !== 'post') {
      return true;
    }
    return false;
  }

  function defaultFormMessage(form) {
    var m = form.getAttribute('data-loader-message');
    if (m) {
      return m;
    }
    var btn = form.querySelector('button[type="submit"], input[type="submit"]');
    if (btn) {
      var t = (btn.textContent || btn.value || '').trim();
      if (t) {
        return t + '…';
      }
    }
    return 'Please wait…';
  }

  function bindFormLoaders() {
    document.querySelectorAll('form').forEach(function (form) {
      if (formSkipsLoader(form)) {
        return;
      }
      form.addEventListener('submit', function () {
        if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
          return;
        }
        show(defaultFormMessage(form));
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindFormLoaders);
  } else {
    bindFormLoaders();
  }
})();
