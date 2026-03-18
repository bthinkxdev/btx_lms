(function () {
  "use strict";

  var nav = document.getElementById("portfolio-nav");
  var menu = document.getElementById("portfolio-nav-menu");
  var toggle = document.getElementById("portfolio-nav-toggle");
  var offset = 72;

  function smoothScrollTo(hash) {
    if (!hash || hash === "#") return;
    var el = document.querySelector(hash);
    if (!el) return;
    var top = el.getBoundingClientRect().top + window.pageYOffset - offset;
    window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
  }

  document.querySelectorAll("a[data-smooth]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      var href = a.getAttribute("href");
      if (href && href.charAt(0) === "#") {
        e.preventDefault();
        smoothScrollTo(href);
        if (menu && toggle) {
          menu.classList.remove("is-open");
          toggle.setAttribute("aria-expanded", "false");
          toggle.setAttribute("aria-label", "Open menu");
        }
      }
    });
  });

  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
  }

  if (nav) {
    var onScroll = function () {
      nav.classList.toggle("is-scrolled", window.scrollY > 24);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* Subtle scroll reveal */
  var reveals = document.querySelectorAll(".prt-reveal");
  if (reveals.length) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      reveals.forEach(function (el) {
        el.classList.add("prt-reveal--in");
      });
    } else {
      var io = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (en) {
            if (en.isIntersecting) {
              en.target.classList.add("prt-reveal--in");
              io.unobserve(en.target);
            }
          });
        },
        { rootMargin: "0px 0px -6% 0px", threshold: 0.06 }
      );
      reveals.forEach(function (el) {
        io.observe(el);
      });
    }
  }
})();
