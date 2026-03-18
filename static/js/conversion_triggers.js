(function() {
  'use strict';

  function getCsrf() {
    var c = document.cookie.split(';').find(function(x) {
      return x.trim().indexOf('csrftoken=') === 0;
    });
    return c ? c.split('=')[1] : '';
  }

  function track(eventType) {
    var cfg = document.getElementById('lms-conversion-config');
    var url = cfg && cfg.getAttribute('data-track-url');
    if (!url) return;
    var lid = '';
    try {
      lid = sessionStorage.getItem('lms_lead_id') || '';
    } catch (e) {}
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({
        event_type: eventType,
        lead_id: lid ? parseInt(lid, 10) : null,
        email: ''
      })
    }).catch(function() {});
  }

  function openLead() {
    var b = document.querySelector('.js-open-lead-modal');
    if (b) b.click();
  }

  /* 30s on site (session-wide) → lead modal once */
  var sessStart = sessionStorage.getItem('lms_sess_start');
  if (!sessStart) {
    sessionStorage.setItem('lms_sess_start', String(Date.now()));
    sessStart = sessionStorage.getItem('lms_sess_start');
  }
  var elapsed = Date.now() - parseInt(sessStart, 10);
  var wait30 = Math.max(0, 30000 - elapsed);
  if (!sessionStorage.getItem('lms_30s_lead')) {
    setTimeout(function() {
      if (sessionStorage.getItem('lms_30s_lead')) return;
      sessionStorage.setItem('lms_30s_lead', '1');
      var modal = document.getElementById('lead-modal');
      if (modal && !modal.classList.contains('is-open')) {
        openLead();
      }
    }, wait30);
  }

  /* Pricing hover popover (once per session) */
  var pop = document.getElementById('lms-pricing-popover');
  var priceZones = document.querySelectorAll('.lms-pricing-hover');
  if (priceZones.length && pop && !sessionStorage.getItem('lms_pricing_pop')) {
    var shown = false;
    priceZones.forEach(function(priceZone) {
      priceZone.addEventListener(
        'mouseenter',
        function() {
          if (shown) return;
          shown = true;
          sessionStorage.setItem('lms_pricing_pop', '1');
          track('viewed_pricing');
          var r = priceZone.getBoundingClientRect();
          pop.style.left = Math.min(window.innerWidth - 280, Math.max(8, r.left)) + 'px';
          pop.style.top = r.bottom + 8 + window.scrollY + 'px';
          pop.classList.add('is-visible');
          pop.setAttribute('aria-hidden', 'false');
          setTimeout(function() {
            pop.classList.remove('is-visible');
          }, 6000);
        },
        { passive: true }
      );
    });
  }
})();
