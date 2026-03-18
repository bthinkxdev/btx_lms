(function() {
  'use strict';

  // Mobile nav toggle
  var navToggle = document.getElementById('nav-toggle');
  var navbarMenu = document.getElementById('navbar-menu');
  if (navToggle && navbarMenu) {
    navToggle.addEventListener('click', function() {
      var expanded = navToggle.getAttribute('aria-expanded') === 'true';
      navToggle.setAttribute('aria-expanded', !expanded);
      navbarMenu.classList.toggle('nav-open');
      document.body.classList.toggle('nav-open', !expanded);
    });
    // Close on resize if open
    window.addEventListener('resize', function() {
      if (window.innerWidth > 768) {
        navToggle.setAttribute('aria-expanded', 'false');
        navbarMenu.classList.remove('nav-open');
        document.body.classList.remove('nav-open');
      }
    });
    // Close on link click (for same-page anchors or after nav)
    navbarMenu.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', function() {
        navToggle.setAttribute('aria-expanded', 'false');
        navbarMenu.classList.remove('nav-open');
        document.body.classList.remove('nav-open');
      });
    });
  }

  // Sidebar toggle functionality
  var sidebarToggle = document.getElementById('sidebar-toggle');
  var sidebar = document.getElementById('sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function() {
      sidebar.classList.toggle('collapsed');
      sidebarToggle.setAttribute('aria-expanded', !sidebar.classList.contains('collapsed'));
    });
    if (window.matchMedia('(max-width: 767px)').matches) {
      sidebar.classList.add('collapsed');
      sidebarToggle.setAttribute('aria-expanded', 'false');
    }
  }

  // Autoplay muted: home hero, /courses/ banner, course detail sidebar
  document.querySelectorAll('.lms-autoplay-muted-video').forEach(function (v) {
    v.muted = true;
    v.setAttribute('muted', '');
    var go = function () {
      var p = v.play();
      if (p && typeof p.catch === 'function') {
        p.catch(function () {});
      }
    };
    if (v.readyState >= 2) {
      go();
    } else {
      v.addEventListener('canplay', go, { once: true });
    }
  });
  var heroVideo =
    document.querySelector('.home-hero .hero-video') ||
    document.querySelector('.hero-video');
  var videoOverlay = document.querySelector('.video-play-overlay');

  if (heroVideo && videoOverlay) {
    // Hide overlay when video starts playing
    heroVideo.addEventListener('play', function() {
      videoOverlay.style.opacity = '0';
      videoOverlay.style.pointerEvents = 'none';
    });
    
    // Show overlay when video is paused
    heroVideo.addEventListener('pause', function() {
      videoOverlay.style.opacity = '1';
      videoOverlay.style.pointerEvents = 'all';
    });
    
    // Show overlay when video ends
    heroVideo.addEventListener('ended', function() {
      videoOverlay.style.opacity = '1';
      videoOverlay.style.pointerEvents = 'all';
    });
    
    // Click on overlay to play video
    videoOverlay.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      if (heroVideo.paused) {
        heroVideo.play();
      }
    });
  }

  // Email OTP login modal
  var loginModal = document.getElementById('login-modal');
  var openLoginButtons = document.querySelectorAll('.js-open-login-modal');
  var closeLoginButtons = document.querySelectorAll('.js-close-login-modal');
  var emailForm = document.getElementById('login-email-form');
  var otpForm = document.getElementById('login-otp-form');
  var messagesBox = document.getElementById('login-modal-messages');
  var emailInput = document.getElementById('login-email-input');
  var otpInput = document.getElementById('login-otp-input');
  var nextInput = document.getElementById('login-next-input');
  var otpEmailHidden = document.getElementById('login-otp-email-hidden');
  var otpNextHidden = document.getElementById('login-otp-next-hidden');
  var resendBtn = document.getElementById('login-resend-btn');

  function getCsrfToken() {
    var cookie = document.cookie.split(';').find(function(c) {
      return c.trim().startsWith('csrftoken=');
    });
    if (!cookie) return '';
    return cookie.split('=')[1];
  }

  var enrollSlugInput = document.getElementById('login-enroll-course-slug');
  var loginModalTitle = document.getElementById('login-modal-title');
  var loginModalSubtitle = loginModal ? loginModal.querySelector('.login-modal-subtitle') : null;

  function resetLoginModalCopy() {
    if (loginModalTitle) loginModalTitle.textContent = 'Login with email';
    if (loginModalSubtitle) {
      loginModalSubtitle.textContent = 'Enter your email to receive a one-time login code.';
    }
  }

  function showLoginModal(nextUrl) {
    if (!loginModal) return;
    if (nextUrl) {
      nextInput.value = nextUrl;
      otpNextHidden.value = nextUrl;
    }
    messagesBox.textContent = '';
    messagesBox.className = 'login-modal-messages';
    otpForm.hidden = true;
    emailForm.hidden = false;
    emailInput.value = '';
    otpInput.value = '';
    loginModal.classList.add('is-open');
    loginModal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('nav-open');
    setTimeout(function() {
      if (emailInput) {
        emailInput.focus();
      }
    }, 50);
  }

  function closeLoginModal() {
    if (!loginModal) return;
    loginModal.classList.remove('is-open');
    loginModal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('nav-open');
    if (enrollSlugInput) enrollSlugInput.value = '';
    resetLoginModalCopy();
  }

  openLoginButtons.forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      var nextUrl = btn.getAttribute('data-next') || (window.location.pathname + window.location.search);
      showLoginModal(nextUrl);
    });
  });

  closeLoginButtons.forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      closeLoginModal();
    });
  });

  if (loginModal) {
    var backdrop = loginModal.querySelector('.login-modal-backdrop');
    if (backdrop) {
      backdrop.addEventListener('click', function(e) {
        e.preventDefault();
        closeLoginModal();
      });
    }
  }

  function setLoginMessage(text, type) {
    if (!messagesBox) return;
    messagesBox.textContent = text || '';
    var base = 'login-modal-messages';
    if (type) {
      base += ' login-modal-messages-' + type;
    }
    messagesBox.className = base;
  }

  if (emailForm) {
    emailForm.addEventListener('submit', function(e) {
      e.preventDefault();
      var email = (emailInput && emailInput.value || '').trim();
      if (!email) {
        setLoginMessage('Please enter your email.', 'error');
        return;
      }
      setLoginMessage('Sending code...', 'info');
      var sendBtn = emailForm.querySelector('button[type="submit"]');
      if (sendBtn) sendBtn.disabled = true;
      if (window.LmsLoader) window.LmsLoader.show('Sending code to your email…');
      fetch('/auth/request-otp/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken': getCsrfToken()
        },
        body: new URLSearchParams({ email: email }).toString()
      })
        .then(function(res) {
          return res.json().then(function(data) {
            return { status: res.status, data: data };
          });
        })
        .then(function(result) {
          var data = result.data || {};
          if (!data.ok) {
            setLoginMessage(data.error || 'Unable to send code.', 'error');
            return;
          }
          otpEmailHidden.value = email;
          otpNextHidden.value = nextInput.value;
          emailForm.hidden = true;
          otpForm.hidden = false;
          setLoginMessage('We sent a code to your email. Check your inbox.', 'success');
          setTimeout(function() {
            if (otpInput) {
              otpInput.focus();
            }
          }, 50);
        })
        .catch(function() {
          setLoginMessage('Something went wrong. Please try again.', 'error');
        })
        .finally(function() {
          if (window.LmsLoader) window.LmsLoader.hide();
          if (sendBtn) sendBtn.disabled = false;
        });
    });
  }

  if (otpForm) {
    otpForm.addEventListener('submit', function(e) {
      e.preventDefault();
      var email = (otpEmailHidden && otpEmailHidden.value || '').trim();
      var code = (otpInput && otpInput.value || '').trim();
      if (!email || !code) {
        setLoginMessage('Please enter the code we sent.', 'error');
        return;
      }
      setLoginMessage('Verifying code...', 'info');
      var verifyBtn = otpForm.querySelector('button[type="submit"]');
      if (verifyBtn) verifyBtn.disabled = true;
      if (window.LmsLoader) window.LmsLoader.show('Verifying code…');
      fetch('/auth/verify-otp/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken': getCsrfToken()
        },
        body: new URLSearchParams({ email: email, code: code }).toString()
      })
        .then(function(res) {
          return res.json().then(function(data) {
            return { status: res.status, data: data };
          });
        })
        .then(function(result) {
          var data = result.data || {};
          if (!data.ok) {
            setLoginMessage(data.error || 'Invalid code.', 'error');
            if (window.LmsLoader) window.LmsLoader.hide();
            return;
          }
          var slug = enrollSlugInput && enrollSlugInput.value ? enrollSlugInput.value.trim() : '';
          if (slug) {
            if (window.LmsLoader) window.LmsLoader.hide();
            if (data.csrfToken) {
              document.cookie =
                'csrftoken=' + encodeURIComponent(data.csrfToken) + ';path=/;SameSite=Lax';
            }
            closeLoginModal();
            if (enrollSlugInput) enrollSlugInput.value = '';
            resetLoginModalCopy();
            startRazorpayPayment(null, slug);
            return;
          }
          var nextUrl = (otpNextHidden && otpNextHidden.value) || window.location.href;
          window.location.href = nextUrl;
        })
        .catch(function() {
          setLoginMessage('Something went wrong. Please try again.', 'error');
          if (window.LmsLoader) window.LmsLoader.hide();
        })
        .finally(function() {
          if (verifyBtn) verifyBtn.disabled = false;
        });
    });
  }

  if (resendBtn && emailForm) {
    resendBtn.addEventListener('click', function(e) {
      e.preventDefault();
      var email = (otpEmailHidden && otpEmailHidden.value) || (emailInput && emailInput.value) || '';
      email = email.trim();
      if (!email) {
        emailForm.hidden = false;
        otpForm.hidden = true;
        setLoginMessage('Please enter your email again to request a new code.', 'info');
        return;
      }
      setLoginMessage('Resending code...', 'info');
      resendBtn.disabled = true;
      if (window.LmsLoader) window.LmsLoader.show('Sending new code…');
      fetch('/auth/request-otp/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken': getCsrfToken()
        },
        body: new URLSearchParams({ email: email }).toString()
      })
        .then(function(res) {
          return res.json().then(function(data) {
            return { status: res.status, data: data };
          });
        })
        .then(function(result) {
          var data = result.data || {};
          if (!data.ok) {
            setLoginMessage(data.error || 'Unable to resend code.', 'error');
            return;
          }
          setLoginMessage('We sent you a new code. Check your inbox.', 'success');
        })
        .catch(function() {
          setLoginMessage('Something went wrong. Please try again.', 'error');
        })
        .finally(function() {
          if (window.LmsLoader) window.LmsLoader.hide();
          resendBtn.disabled = false;
        });
    });
  }

  document.querySelectorAll('.js-open-enroll-flow').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      var slug = btn.getAttribute('data-course-slug') || '';
      if (enrollSlugInput) enrollSlugInput.value = slug;
      if (loginModalTitle) loginModalTitle.textContent = 'Continue to secure payment';
      if (loginModalSubtitle) {
        loginModalSubtitle.textContent = 'We’ll email you a one-time code, then open Razorpay checkout.';
      }
      showLoginModal(window.location.pathname + window.location.search);
    });
  });

  // Razorpay enrollment
  var razorpayButtons = document.querySelectorAll('.js-razorpay-enroll');

  function lmsTrackEvent(eventType) {
    var cfg = document.getElementById('lms-conversion-config');
    var turl = cfg && cfg.getAttribute('data-track-url');
    if (!turl || !eventType) return;
    var lid = '';
    try {
      lid = sessionStorage.getItem('lms_lead_id') || '';
    } catch (e) {}
    fetch(turl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({
        event_type: eventType,
        lead_id: lid ? parseInt(lid, 10) : null,
        email: ''
      })
    }).catch(function() {});
  }

  function lmsCaptureRefFromUrl() {
    var params = new URLSearchParams(window.location.search);
    var ref = params.get('ref');
    if (!ref) return;
    var cfg = document.getElementById('lms-conversion-config');
    var rurl = cfg && cfg.getAttribute('data-ref-url');
    if (!rurl) return;
    fetch(rurl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({ code: ref.trim() })
    }).catch(function() {});
  }
  lmsCaptureRefFromUrl();

  function showUpsellThenRedirect(upsell, redirectUrl) {
    var modal = document.getElementById('lms-upsell-modal');
    if (!modal || !upsell || !upsell.title) {
      window.location.href = redirectUrl;
      return;
    }
    var titleEl = document.getElementById('upsell-title');
    var bodyEl = document.getElementById('upsell-body');
    var ctaEl = document.getElementById('upsell-cta');
    if (titleEl) titleEl.textContent = upsell.title;
    if (bodyEl) bodyEl.textContent = upsell.body || '';
    if (ctaEl) {
      ctaEl.href = upsell.cta_url || '#';
      ctaEl.textContent = upsell.cta_label || 'Learn more';
    }
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('nav-open');
    function go() {
      modal.classList.remove('is-open');
      modal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('nav-open');
      window.location.href = redirectUrl;
    }
    document.querySelectorAll('.js-close-upsell').forEach(function(b) {
      b.onclick = function(e) {
        e.preventDefault();
        go();
      };
    });
  }

  function startRazorpayPayment(button, slugOverride) {
    var slug = slugOverride || (button && button.getAttribute('data-course-slug'));
    if (!slug) return;
    if (typeof Razorpay === 'undefined') {
      alert('Payment system is not available right now. Please try again later.');
      return;
    }
    var btn = button;
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Processing...';
    }
    if (window.LmsLoader) window.LmsLoader.show('Preparing checkout…');

    fetch('/courses/' + encodeURIComponent(slug) + '/create-order/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'X-CSRFToken': getCsrfToken()
      },
      body: ''
    })
      .then(function(res) {
        return res.json().then(function(data) {
          return { status: res.status, data: data };
        });
      })
      .then(function(result) {
        var data = result.data || {};
        if (!data.ok) {
          if (window.LmsLoader) window.LmsLoader.hide();
          if (btn) {
            btn.disabled = false;
            btn.textContent = 'Pay & Enroll';
          }
          alert(data.error || 'Unable to start payment. Please try again.');
          return;
        }

        if (window.LmsLoader) window.LmsLoader.hide();
        lmsTrackEvent('checkout_started');
        try {
          sessionStorage.setItem('lms_checkout_pending', JSON.stringify({ slug: slug }));
        } catch (errCheckout) {}

        var options = {
          key: data.key_id,
          amount: data.amount,
          currency: data.currency,
          name: 'BThinkX',
          description: data.course_title || 'Course enrollment',
          order_id: data.order_id,
          prefill: {
            email: data.user_email || '',
            name: data.user_name || ''
          },
          handler: function(response) {
            if (window.LmsLoader) window.LmsLoader.show('Confirming payment…');
            fetch('/payments/razorpay/verify/', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'X-CSRFToken': getCsrfToken()
              },
              body: new URLSearchParams({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                slug: slug
              }).toString()
            })
              .then(function(res) {
                return res.json().then(function(data) {
                  return { status: res.status, data: data };
                });
              })
              .then(function(result) {
                var data = result.data || {};
                if (!data.ok) {
                  if (window.LmsLoader) window.LmsLoader.hide();
                  alert(data.error || 'Payment verification failed.');
                  if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Pay & Enroll';
                  }
                  return;
                }
                try {
                  sessionStorage.removeItem('lms_checkout_pending');
                } catch (errPaid) {}
                var redir = data.redirect_url || '/dashboard/';
                if (window.LmsLoader) window.LmsLoader.hide();
                showUpsellThenRedirect(data.upsell, redir);
              })
              .catch(function() {
                if (window.LmsLoader) window.LmsLoader.hide();
                alert('Something went wrong while verifying payment.');
                if (btn) {
                  btn.disabled = false;
                  btn.textContent = 'Pay & Enroll';
                }
              });
          },
          theme: {
            color: '#6440FB'
          }
        };

        var rzp = new Razorpay(options);
        rzp.on('payment.failed', function() {
          lmsTrackEvent('checkout_abandoned');
          if (window.LmsLoader) window.LmsLoader.forceHide();
          if (btn) {
            btn.disabled = false;
            btn.textContent = 'Pay & Enroll';
          }
        });
        rzp.open();
      })
      .catch(function() {
        if (window.LmsLoader) window.LmsLoader.hide();
        if (btn) {
          btn.disabled = false;
          btn.textContent = 'Pay & Enroll';
        }
        alert('Unable to start payment. Please try again.');
      });
  }

  razorpayButtons.forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      startRazorpayPayment(btn);
    });
  });

  /* Lead capture modal */
  var leadModal = document.getElementById('lead-modal');
  var leadForm = document.getElementById('lead-capture-form');
  var leadMessages = document.getElementById('lead-modal-messages');
  var leadSourceInput = document.getElementById('lead-source-input');
  var convCfg = document.getElementById('lms-conversion-config');

  function openLeadModal(source) {
    if (!leadModal) return;
    if (leadSourceInput) leadSourceInput.value = source || 'lead_magnet';
    var mentorRow = document.getElementById('lead-modal-mentor-row');
    if (mentorRow) {
      mentorRow.hidden = (source || '') !== 'exit_intent';
    }
    if (leadMessages) {
      leadMessages.textContent = '';
      leadMessages.className = 'lead-modal-messages';
    }
    leadModal.classList.add('is-open');
    leadModal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('nav-open');
  }

  function closeLeadModal() {
    if (!leadModal) return;
    leadModal.classList.remove('is-open');
    leadModal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('nav-open');
  }

  document.querySelectorAll('.js-open-lead-modal').forEach(function(b) {
    b.addEventListener('click', function(e) {
      e.preventDefault();
      openLeadModal(b.getAttribute('data-source') || 'lead_magnet');
    });
  });
  document.querySelectorAll('.js-close-lead-modal').forEach(function(b) {
    b.addEventListener('click', function(e) {
      e.preventDefault();
      closeLeadModal();
    });
  });

  if (leadForm && convCfg) {
    leadForm.addEventListener('submit', function(e) {
      e.preventDefault();
      var url = convCfg.getAttribute('data-lead-url');
      var payload = {
        name: (document.getElementById('lead-name') || {}).value || '',
        email: (document.getElementById('lead-email') || {}).value || '',
        phone: (document.getElementById('lead-phone') || {}).value || '',
        source: (leadSourceInput && leadSourceInput.value) || 'web',
        variant: convCfg.getAttribute('data-ab-variant') || 'a'
      };
      function leadPhoneDigits(v) {
        return String(v || '').replace(/\D/g, '');
      }
      function validateLeadWhatsApp(v) {
        var d = leadPhoneDigits(v);
        if (d.length < 10) {
          return 'Enter your WhatsApp number (at least 10 digits).';
        }
        if (d.length > 15) {
          return 'WhatsApp number is too long.';
        }
        if (d.length === 11 && d.charAt(0) === '0') {
          d = d.slice(1);
        }
        if (d.length < 10) {
          return 'Enter a valid WhatsApp number.';
        }
        if (/^(\d)\1{9,}$/.test(d)) {
          return 'Please enter a real WhatsApp number.';
        }
        return '';
      }
      var phoneErr = validateLeadWhatsApp(payload.phone);
      if (phoneErr) {
        if (leadMessages) {
          leadMessages.textContent = phoneErr;
          leadMessages.className = 'lead-modal-messages lead-modal-messages-error';
        }
        var phEl = document.getElementById('lead-phone');
        if (phEl) phEl.focus();
        return;
      }
      var em = payload.email.trim();
      if (em && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)) {
        if (leadMessages) {
          leadMessages.textContent = 'Please enter a valid email or leave it blank.';
          leadMessages.className = 'lead-modal-messages lead-modal-messages-error';
        }
        return;
      }
      if (leadMessages) {
        leadMessages.textContent = 'Sending…';
        leadMessages.className = 'lead-modal-messages';
      }
      var leadSubmit = leadForm.querySelector('button[type="submit"], input[type="submit"]');
      if (leadSubmit) leadSubmit.disabled = true;
      if (window.LmsLoader) window.LmsLoader.show('Sending your details…');
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(payload)
      })
        .then(function(r) { return r.json().then(function(d) { return { ok: r.ok, d: d }; }); })
        .then(function(x) {
          if (!x.d || !x.d.ok) {
            if (leadMessages) {
              leadMessages.textContent = (x.d && x.d.error) || 'Something went wrong.';
              leadMessages.className = 'lead-modal-messages lead-modal-messages-error';
            }
            return;
          }
          if (x.d.lead_id) {
            try {
              sessionStorage.setItem('lms_lead_id', String(x.d.lead_id));
            } catch (err) {}
          }
          if (leadMessages) {
            leadMessages.textContent = x.d.message || 'Thanks! You’re on the list.';
            leadMessages.className = 'lead-modal-messages lead-modal-messages-success';
          }
          if (x.d.magnet_url) {
            window.open(x.d.magnet_url, '_blank');
          }
          setTimeout(closeLeadModal, 1800);
        })
        .catch(function() {
          if (leadMessages) {
            leadMessages.textContent = 'Network error. Try again.';
            leadMessages.className = 'lead-modal-messages lead-modal-messages-error';
          }
        })
        .finally(function() {
          if (window.LmsLoader) window.LmsLoader.hide();
          if (leadSubmit) leadSubmit.disabled = false;
        });
    });
  }

  /* Exit intent, once per tab session */
  document.addEventListener('mouseout', function(ev) {
    if (sessionStorage.getItem('lms_exit_lead')) return;
    if (!leadModal) return;
    if (ev.clientY < 15 && (!ev.relatedTarget || ev.relatedTarget === document.body)) {
      sessionStorage.setItem('lms_exit_lead', '1');
      openLeadModal('exit_intent');
    }
  });

  /* Countdown timers */
  function pad(n) { return n < 10 ? '0' + n : String(n); }
  function tickCountdown(el) {
    var endIso = el.getAttribute('data-end');
    if (!endIso) return;
    var end = new Date(endIso).getTime();
    var digits = el.querySelector('.cd-digits');
    function tick() {
      var now = Date.now();
      var sec = Math.max(0, Math.floor((end - now) / 1000));
      if (!digits) return;
      if (sec <= 0) {
        digits.textContent = 'Ended';
        return;
      }
      var d = Math.floor(sec / 86400);
      var h = Math.floor((sec % 86400) / 3600);
      var m = Math.floor((sec % 3600) / 60);
      var s = sec % 60;
      digits.textContent = (d > 0 ? d + 'd ' : '') + pad(h) + ':' + pad(m) + ':' + pad(s);
    }
    tick();
    setInterval(tick, 1000);
  }
  document.querySelectorAll('[data-end].course-countdown, #home-countdown[data-end]').forEach(tickCountdown);

  /* A/B cookie (180 days) */
  if (convCfg && !document.cookie.match(/(?:^|; )lms_ab=/)) {
    var ab = Math.random() < 0.5 ? 'a' : 'b';
    document.cookie = 'lms_ab=' + ab + ';path=/;max-age=' + (60 * 60 * 24 * 180);
    convCfg.setAttribute('data-ab-variant', ab);
  }

  var copyRefBtn = document.getElementById('copy-referral-link');
  var refLinkInput = document.getElementById('dashboard-referral-link');
  if (copyRefBtn && refLinkInput) {
    copyRefBtn.addEventListener('click', function() {
      refLinkInput.select();
      try {
        document.execCommand('copy');
        copyRefBtn.textContent = 'Copied!';
        setTimeout(function() {
          copyRefBtn.textContent = 'Copy';
        }, 2000);
      } catch (err) {}
    });
  }

  var copyCertBtn = document.getElementById('cert-copy-link');
  var certUrlInput = document.getElementById('cert-public-url');
  if (copyCertBtn && certUrlInput) {
    copyCertBtn.addEventListener('click', function() {
      certUrlInput.select();
      try {
        document.execCommand('copy');
        copyCertBtn.textContent = 'Copied!';
        setTimeout(function() { copyCertBtn.textContent = 'Copy link'; }, 2000);
      } catch (err) {}
    });
  }

  // Day quiz: one-question-at-a-time navigation
  (function() {
    var quizForm = document.querySelector('.day-quiz-form');
    if (!quizForm) return;

    var items = Array.prototype.slice.call(
      quizForm.querySelectorAll('.quiz-question-item')
    );
    if (!items.length) return;

    var prevBtn = quizForm.querySelector('.quiz-prev-btn');
    var nextBtn = quizForm.querySelector('.quiz-next-btn');
    var submitBtn = quizForm.querySelector('.quiz-submit-btn');
    var progressEl = quizForm.querySelector('.quiz-progress');

    if (!prevBtn || !nextBtn || !submitBtn || !progressEl) return;

    var current = 0;

    function updateView() {
      items.forEach(function(item, index) {
        if (index === current) {
          item.classList.remove('quiz-question-hidden');
        } else {
          item.classList.add('quiz-question-hidden');
        }
      });

      prevBtn.disabled = current === 0;
      nextBtn.style.display = current === items.length - 1 ? 'none' : 'inline-flex';
      submitBtn.style.display = current === items.length - 1 ? 'block' : 'none';
      progressEl.textContent = 'Question ' + (current + 1) + ' of ' + items.length;

      // Ensure current question is visible
      items[current].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    prevBtn.addEventListener('click', function(e) {
      e.preventDefault();
      if (current > 0) {
        current -= 1;
        updateView();
      }
    });

    nextBtn.addEventListener('click', function(e) {
      e.preventDefault();
      if (current < items.length - 1) {
        current += 1;
        updateView();
      }
    });

    // Initialize
    updateView();
  })();

  /* Live activity toasts (10–20s interval, random message) */
  (function liveActivityToasts() {
    var cfg = document.getElementById('lms-conversion-config');
    if (!cfg || cfg.getAttribute('data-activity-enabled') !== '1') return;
    var url = cfg.getAttribute('data-activity-url');
    if (!url) return;
    var toast = document.createElement('div');
    toast.id = 'lms-activity-toast';
    toast.className = 'lms-activity-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);
    var pool = [];
    function pickAndShow() {
      if (!pool.length) return;
      toast.textContent = pool[Math.floor(Math.random() * pool.length)];
      toast.classList.add('is-visible');
      setTimeout(function() {
        toast.classList.remove('is-visible');
      }, 5000);
    }
    function scheduleNext() {
      var ms = 10000 + Math.random() * 10000;
      setTimeout(function() {
        pickAndShow();
        scheduleNext();
      }, ms);
    }
    fetch(url)
      .then(function(res) { return res.json(); })
      .then(function(d) {
        if (!d || !d.enabled || !d.messages || !d.messages.length) return;
        pool = d.messages;
        setTimeout(scheduleNext, 8000 + Math.random() * 7000);
      })
      .catch(function() {});
  })();

  /* Checkout abandoned, reminder bar (sessionStorage) */
  (function checkoutReminderBar() {
    var bar = document.getElementById('lms-checkout-reminder');
    var link = document.getElementById('lms-checkout-reminder-link');
    var dismiss = document.querySelector('.lms-checkout-reminder-dismiss');
    if (!bar || !link) return;
    try {
      var raw = sessionStorage.getItem('lms_checkout_pending');
      if (!raw) return;
      var o = JSON.parse(raw);
      if (!o || !o.slug) return;
      link.href = '/courses/' + encodeURIComponent(o.slug) + '/#enroll';
      bar.hidden = false;
    } catch (errBar) {}
    if (dismiss) {
      dismiss.addEventListener('click', function() {
        try {
          sessionStorage.removeItem('lms_checkout_pending');
        } catch (e) {}
        bar.hidden = true;
      });
    }
  })();
})();
