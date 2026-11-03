/*!
 * prismal-webchat loader (SPEC-WCB-EMB-001/003/004).
 *
 *   <script src="<webchat origin>/embed.js" async></script>
 *
 * Injects a launcher bubble that toggles an iframe of the webchat's bare
 * `/chat` route. It knows only its own origin (taken from this script tag):
 * no secret, tenant or upstream server address ever lives here. Whether a
 * page may frame the chat is decided by the webchat's CSP header, not here.
 *
 * Page API:   window.PrismalChat.open() / .close() / .toggle()
 * From chat:  postMessage({type: "prismal-chat:open" | "prismal-chat:close"})
 *             accepted only from the chat's own origin.
 */
(function () {
  "use strict";
  if (window.PrismalChat) {
    return;
  }

  var OPEN = "prismal-chat:open";
  var CLOSE = "prismal-chat:close";
  var script = document.currentScript;
  if (!script || !script.src) {
    return;
  }
  var chatOrigin = new URL(script.src, window.location.href).origin;
  var chatUrl = chatOrigin + "/chat";

  var launcher = document.createElement("button");
  var frame = null;
  var isOpen = false;

  function style(el, props) {
    for (var key in props) {
      el.style[key] = props[key];
    }
  }

  function ensureFrame() {
    if (frame) {
      return frame;
    }
    frame = document.createElement("iframe");
    frame.src = chatUrl;
    frame.title = "Chat";
    frame.id = "prismal-chat-frame";
    style(frame, {
      position: "fixed",
      right: "20px",
      bottom: "88px",
      width: "min(380px, calc(100vw - 40px))",
      height: "min(600px, calc(100vh - 120px))",
      border: "1px solid #3F4348",
      borderRadius: "8px",
      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.18)",
      background: "#EDE7DA",
      zIndex: "2147483646",
      display: "none",
    });
    document.body.appendChild(frame);
    return frame;
  }

  function setOpen(open) {
    isOpen = open;
    ensureFrame().style.display = open ? "block" : "none";
    launcher.setAttribute("aria-expanded", open ? "true" : "false");
    launcher.setAttribute("aria-label", open ? "Close chat" : "Open chat");
    if (open) {
      frame.focus();
    } else {
      launcher.focus();
    }
  }

  launcher.type = "button";
  launcher.id = "prismal-chat-launcher";
  launcher.setAttribute("aria-controls", "prismal-chat-frame");
  launcher.setAttribute("aria-expanded", "false");
  launcher.setAttribute("aria-label", "Open chat");
  launcher.innerHTML =
    '<svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true" fill="none" ' +
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M4 5h16v11H9l-5 4z"/></svg>';
  style(launcher, {
    position: "fixed",
    right: "20px",
    bottom: "20px",
    width: "56px",
    height: "56px",
    borderRadius: "50%",
    border: "1px solid #3F4348",
    background: "#EDE7DA",
    color: "#3F4348",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 4px 16px rgba(0, 0, 0, 0.18)",
    zIndex: "2147483647",
  });
  launcher.addEventListener("click", function () {
    setOpen(!isOpen);
  });

  window.addEventListener("message", function (event) {
    if (event.origin !== chatOrigin) {
      return;
    }
    var data = event.data;
    if (!data || typeof data !== "object") {
      return;
    }
    if (data.type === OPEN) {
      setOpen(true);
    } else if (data.type === CLOSE) {
      setOpen(false);
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && isOpen) {
      setOpen(false);
    }
  });

  window.PrismalChat = {
    open: function () {
      setOpen(true);
    },
    close: function () {
      setOpen(false);
    },
    toggle: function () {
      setOpen(!isOpen);
    },
  };

  function mount() {
    document.body.appendChild(launcher);
  }
  if (document.body) {
    mount();
  } else {
    document.addEventListener("DOMContentLoaded", mount);
  }
})();
