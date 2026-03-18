(function () {
  "use strict";

  function getCookie(name) {
    var v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return v ? v.pop() : "";
  }

  var openModalId = null;

  function openSectionModal(modalId) {
    if (!modalId) return;
    var el = document.getElementById(modalId);
    if (!el) return;
    closeAllSectionModals();
    el.removeAttribute("hidden");
    el.setAttribute("aria-hidden", "false");
    document.body.classList.add("sp-modal-open");
    openModalId = modalId;
    var nudge = document.getElementById("profile-nudge-modal");
    if (nudge) nudge.style.display = "none";
  }

  function closeSectionModal() {
    if (!openModalId) return;
    var el = document.getElementById(openModalId);
    if (el) {
      el.setAttribute("hidden", "");
      el.setAttribute("aria-hidden", "true");
      var err = el.querySelector(".sp-section-modal-errors");
      if (err) {
        err.hidden = true;
        err.textContent = "";
      }
    }
    openModalId = null;
    document.body.classList.remove("sp-modal-open");
  }

  function closeAllSectionModals() {
    document.querySelectorAll(".sp-section-modal").forEach(function (m) {
      m.setAttribute("hidden", "");
      m.setAttribute("aria-hidden", "true");
      var err = m.querySelector(".sp-section-modal-errors");
      if (err) {
        err.hidden = true;
        err.textContent = "";
      }
    });
    openModalId = null;
    document.body.classList.remove("sp-modal-open");
  }

  document.querySelectorAll("[data-open-section-modal]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var id = btn.getAttribute("data-open-section-modal");
      if (!id) return;
      var modalId = id.indexOf("modal-") === 0 ? id : "modal-section-" + id;
      openSectionModal(modalId);
    });
  });

  document.querySelectorAll(".js-section-modal-close, .js-section-modal-backdrop").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (el.classList.contains("js-section-modal-backdrop")) {
        e.stopPropagation();
      }
      closeSectionModal();
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && openModalId) {
      closeSectionModal();
    }
  });

  document.querySelectorAll(".js-section-profile-form").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var modal = form.closest(".sp-section-modal");
      var errBox = modal ? modal.querySelector(".sp-section-modal-errors") : null;
      var saveBtn = form.querySelector(".js-section-save");
      if (errBox) {
        errBox.hidden = true;
        errBox.textContent = "";
      }
      if (saveBtn) saveBtn.disabled = true;
      if (window.LmsLoader) window.LmsLoader.show("Saving profile…");
      var willReload = false;
      var fd = new FormData(form);
      var url = form.getAttribute("action") || window.location.pathname;
      fetch(url, {
        method: "POST",
        body: fd,
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest",
        },
      })
        .then(function (r) {
          return r.json().then(function (data) {
            return { ok: r.ok, status: r.status, data: data };
          });
        })
        .then(function (res) {
          if (res.ok && res.data && res.data.ok) {
            willReload = true;
            window.location.reload();
            return;
          }
          var parts = [];
          if (res.data && res.data.errors) {
            Object.keys(res.data.errors).forEach(function (k) {
              (res.data.errors[k] || []).forEach(function (msg) {
                parts.push(k + ": " + msg);
              });
            });
          }
          if (errBox) {
            errBox.textContent = parts.length ? parts.join(" ") : "Could not save.";
            errBox.hidden = false;
          }
        })
        .catch(function () {
          if (errBox) {
            errBox.textContent = "Network error. Try again.";
            errBox.hidden = false;
          }
        })
        .finally(function () {
          if (!willReload && window.LmsLoader) window.LmsLoader.hide();
          if (saveBtn) saveBtn.disabled = false;
        });
    });
  });
})();
