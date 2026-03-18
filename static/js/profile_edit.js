(function () {
  "use strict";

  var photoInput = document.getElementById("id_profile_photo");
  var preview = document.getElementById("profile-photo-preview");
  var fileNameEl = document.getElementById("profile-photo-filename");
  var uploadWrap = document.getElementById("profile-photo-upload");

  function setPhotoFilename(text) {
    if (fileNameEl) fileNameEl.textContent = text;
  }

  if (photoInput && uploadWrap && uploadWrap.getAttribute("data-has-photo") === "1") {
    setPhotoFilename("Using your current photo, choose a new file to replace");
  }

  if (photoInput && preview) {
    photoInput.addEventListener("change", function () {
      var f = photoInput.files && photoInput.files[0];
      if (!f) {
        if (uploadWrap && uploadWrap.getAttribute("data-has-photo") === "1") {
          setPhotoFilename("Using your current photo, choose a new file to replace");
        } else {
          setPhotoFilename("No file selected");
        }
        return;
      }
      if (!/^image\//.test(f.type)) return;
      setPhotoFilename(f.name);
      var reader = new FileReader();
      reader.onload = function () {
        var url = reader.result;
        if (preview.tagName === "IMG") {
          preview.src = url;
        } else {
          var img = document.createElement("img");
          img.id = "profile-photo-preview";
          img.className = "profile-photo-preview";
          img.width = 120;
          img.height = 120;
          img.alt = "Preview";
          img.src = url;
          preview.parentNode.replaceChild(img, preview);
          preview = img;
        }
      };
      reader.readAsDataURL(f);
    });
  }

  function bindSkillsEditor(skillsInput, editor) {
    if (!skillsInput || !editor) return;
    function parseSkills() {
      return skillsInput.value
        .split(",")
        .map(function (s) {
          return s.trim();
        })
        .filter(Boolean);
    }
    function render() {
      editor.innerHTML = "";
      var chips = parseSkills();
      chips.forEach(function (skill) {
        var span = document.createElement("span");
        span.className = "skill-tag skill-tag-removable";
        span.appendChild(document.createTextNode(skill + " "));
        var x = document.createElement("button");
        x.type = "button";
        x.className = "skill-tag-remove";
        x.setAttribute("aria-label", "Remove " + skill);
        x.innerHTML = "&times;";
        x.addEventListener("click", function () {
          skillsInput.value = parseSkills()
            .filter(function (s) {
              return s !== skill;
            })
            .join(", ");
          render();
          skillsInput.dispatchEvent(new Event("input", { bubbles: true }));
        });
        span.appendChild(x);
        editor.appendChild(span);
      });
      var add = document.createElement("input");
      add.type = "text";
      add.className = "skills-tag-add-input";
      add.placeholder = "Add skill, Enter or comma…";
      add.setAttribute("aria-label", "Add skill");
      add.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === ",") {
          e.preventDefault();
          var v = add.value.trim().replace(/,$/, "");
          if (!v) return;
          var arr = parseSkills();
          if (arr.indexOf(v) === -1) arr.push(v);
          skillsInput.value = arr.join(", ");
          add.value = "";
          render();
        }
      });
      editor.appendChild(add);
    }
    skillsInput.addEventListener("input", render);
    render();
  }

  bindSkillsEditor(
    document.getElementById("id_skills"),
    document.getElementById("skills-tag-editor")
  );

  bindSkillsEditor(
    document.getElementById("id_sec_skills-skills"),
    document.getElementById("sec-skills-modal-editor")
  );

  var secBasicPhoto = document.getElementById("id_sec_basic-profile_photo");
  var secBasicPreview = document.getElementById("sec-basic-photo-preview");
  var secBasicFileEl = document.getElementById("sec-basic-photo-filename");
  var secBasicUpload = document.getElementById("sec-basic-photo-upload");
  function setSecBasicPhotoFilename(t) {
    if (secBasicFileEl) secBasicFileEl.textContent = t;
  }
  if (secBasicPhoto && secBasicUpload && secBasicUpload.getAttribute("data-has-photo") === "1") {
    setSecBasicPhotoFilename("Current photo, choose new to replace");
  }
  if (secBasicPhoto && secBasicPreview) {
    secBasicPhoto.addEventListener("change", function () {
      var f = secBasicPhoto.files && secBasicPhoto.files[0];
      if (!f) {
        if (secBasicUpload && secBasicUpload.getAttribute("data-has-photo") === "1") {
          setSecBasicPhotoFilename("Current photo, choose new to replace");
        } else {
          setSecBasicPhotoFilename("No file selected");
        }
        return;
      }
      if (!/^image\//.test(f.type)) return;
      setSecBasicPhotoFilename(f.name);
      var reader = new FileReader();
      reader.onload = function () {
        var url = reader.result;
        var prev = secBasicPreview;
        if (prev.tagName === "IMG") {
          prev.src = url;
        } else {
          var img = document.createElement("img");
          img.id = "sec-basic-photo-preview";
          img.className = "profile-photo-preview";
          img.width = 120;
          img.height = 120;
          img.alt = "";
          img.src = url;
          prev.parentNode.replaceChild(img, prev);
          secBasicPreview = img;
        }
      };
      reader.readAsDataURL(f);
    });
  }

  function wireCopy(btnId, inpId, label) {
    var copyBtn = document.getElementById(btnId);
    var copyInp = document.getElementById(inpId);
    if (!copyBtn || !copyInp) return;
    copyBtn.addEventListener("click", function () {
      copyInp.removeAttribute("hidden");
      copyInp.classList.remove("sp-hidden-copy");
      copyInp.select();
      copyInp.setSelectionRange(0, 99999);
      var ok = label || "Copy";
      try {
        navigator.clipboard.writeText(copyInp.value).then(function () {
          copyBtn.textContent = "Copied!";
          setTimeout(function () {
            copyBtn.textContent = ok;
          }, 2000);
        });
      } catch (e) {
        document.execCommand("copy");
        copyBtn.textContent = "Copied!";
        setTimeout(function () {
          copyBtn.textContent = ok;
        }, 2000);
      }
    });
  }

  wireCopy("copy-public-profile-url", "public-profile-url-input", "Copy");
  wireCopy("copy-public-profile-dashboard", "public-profile-url-dashboard", "Copy link");
})();
