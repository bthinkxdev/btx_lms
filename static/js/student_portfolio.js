(function () {
  "use strict";

  function getShareUrl() {
    var el = document.getElementById("sp-share-url");
    return el ? el.getAttribute("data-url") || el.value || window.location.href : window.location.href;
  }

  function getShareTitle() {
    var el = document.getElementById("sp-share-title");
    return el ? el.getAttribute("data-title") || document.title : document.title;
  }

  var copyBtn = document.getElementById("sp-copy-link");
  var copyMsg = document.getElementById("sp-copy-feedback");
  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      var url = getShareUrl();
      function done(ok) {
        if (copyMsg) {
          copyMsg.textContent = ok ? "Link copied to clipboard." : "Copy the URL from the address bar.";
        }
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () {
          done(true);
        }).catch(function () {
          done(false);
        });
      } else {
        var ta = document.createElement("textarea");
        ta.value = url;
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand("copy");
          done(true);
        } catch (e) {
          done(false);
        }
        document.body.removeChild(ta);
      }
    });
  }

  var waShare = document.getElementById("sp-share-whatsapp");
  if (waShare) {
    waShare.addEventListener("click", function (e) {
      e.preventDefault();
      var text = encodeURIComponent(getShareTitle() + ", " + getShareUrl());
      window.open("https://wa.me/?text=" + text, "_blank", "noopener,noreferrer");
    });
  }

  var liShare = document.getElementById("sp-share-linkedin");
  if (liShare) {
    liShare.addEventListener("click", function (e) {
      e.preventDefault();
      var u = encodeURIComponent(getShareUrl());
      window.open(
        "https://www.linkedin.com/sharing/share-offsite/?url=" + u,
        "_blank",
        "noopener,noreferrer"
      );
    });
  }
})();
