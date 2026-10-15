/* Script of pyTooling.Sphinx: the copy buttons of the 'unicode-table' directive.

   A copy button is a '<button class="pytooling-copy">', whose attribute 'data-copy' holds the text it copies. A click
   copies the text into the clipboard; the button shows a check mark for a moment, or the stylesheet's failure colour,
   and a status message tells a screen reader what was copied. One listener on the document serves every button. */
(() => {
  "use strict";

  /* How long a button shows that it copied its text, in milliseconds. */
  const FEEDBACK_DURATION = 2000;

  /* The live region announcing the result to a screen reader, created on the first click. */
  let statusRegion = null;

  /* Announce a message to a screen reader. */
  function announce(message) {
    if (statusRegion === null) {
      statusRegion = document.createElement("span");
      statusRegion.className = "pytooling-copy-status";
      statusRegion.setAttribute("role", "status");
      document.body.appendChild(statusRegion);
    }
    statusRegion.textContent = message;
  }

  /* Show a result - class 'copied' or 'copy-failed' - on a button for a moment, and announce it. */
  function showResult(button, result, message) {
    clearTimeout(button.pytoolingCopyTimer);
    button.classList.remove("copied", "copy-failed");
    button.classList.add(result);
    announce(message);
    button.pytoolingCopyTimer = setTimeout(() => button.classList.remove(result), FEEDBACK_DURATION);
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("button.pytooling-copy");
    if (button === null) {
      return;
    }

    const text = button.dataset.copy;
    /* The clipboard is available to a secure context only: a page served by HTTPS or from localhost. */
    if (navigator.clipboard === undefined) {
      showResult(button, "copy-failed", "Copying needs a page served by HTTPS.");
      return;
    }

    navigator.clipboard.writeText(text).then(
      () => showResult(button, "copied", `Copied ${text}`),
      () => showResult(button, "copy-failed", `Copying ${text} failed.`)
    );
  });
})();
