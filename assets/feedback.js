(() => {
  const boxes = document.querySelectorAll(".feedback[data-page]");
  if (!boxes.length) return;

  const submittedKey = page => `calculation-feedback:${page}`;

  async function postFeedback(payload) {
    const res = await fetch("/api/feedback", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  }

  boxes.forEach(box => {
    const page = box.dataset.page;
    const title = box.dataset.title || document.title;
    const status = box.querySelector(".feedback-status");
    const detail = box.querySelector(".feedback-detail");
    const textarea = box.querySelector("textarea");

    try {
      if (localStorage.getItem(submittedKey(page))) {
        box.classList.add("is-sent");
        status.textContent = "フィードバックありがとうございました。";
      }
    } catch (_) {}

    const markSent = () => {
      box.classList.add("is-sent");
      status.textContent = "フィードバックありがとうございました。";
      try { localStorage.setItem(submittedKey(page), "1"); } catch (_) {}
    };

    box.querySelector('[data-feedback="helpful"]').addEventListener("click", async () => {
      status.textContent = "送信中…";
      try {
        await postFeedback({page_slug: page, page_title: title, feedback: "helpful", comment: null});
        markSent();
      } catch (_) {
        status.textContent = "送信できませんでした。時間をおいてもう一度お試しください。";
      }
    });

    box.querySelector('[data-feedback="needs_more"]').addEventListener("click", () => {
      detail.hidden = false;
      textarea.focus();
      status.textContent = "";
    });

    box.querySelector(".feedback-submit").addEventListener("click", async () => {
      const comment = textarea.value.trim();
      status.textContent = "送信中…";
      try {
        await postFeedback({
          page_slug: page,
          page_title: title,
          feedback: "needs_more",
          comment: comment || null
        });
        markSent();
      } catch (_) {
        status.textContent = "送信できませんでした。時間をおいてもう一度お試しください。";
      }
    });
  });
})();