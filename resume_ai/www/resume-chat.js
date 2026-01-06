frappe.ready(() => {

  window.sendQuestion = function () {
    const input = document.getElementById("questionInput");
    const chatBox = document.getElementById("chatBox");
    const question = input.value.trim();

    if (!question) return;

    // Show user message
    chatBox.innerHTML += `
      <div style="margin-bottom:10px">
        <b>You:</b> ${question}
      </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;

    input.value = "";

    // Loading indicator
    const loaderId = "loader-" + Date.now();
    chatBox.innerHTML += `
      <div id="${loaderId}">
        <i>AI is thinking...</i>
      </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;

    fetch("https://cnd.octavision.in/api/method/resume_ai.chat_api.chat_query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Frappe-CSRF-Token": frappe.csrf_token
      },
      body: JSON.stringify({ question })
    })
    .then(res => res.json())
    .then(data => {
      document.getElementById(loaderId).remove();

      if (!data.message || !data.message.success) {
        chatBox.innerHTML += `<div style="color:red">Error</div>`;
        return;
      }

      chatBox.innerHTML += `
        <div style="margin-bottom:10px">
          <b>AI:</b> ${data.message.answer}
        </div>
      `;

      // Show sources
      if (data.message.sources?.length) {
        chatBox.innerHTML += `
          <div style="font-size:12px;color:#555;margin-left:10px">
            <b>Sources:</b>
            <ul>
              ${data.message.sources.map(s =>
                `<li>Candidate: ${s.candidate_id}</li>`
              ).join("")}
            </ul>
          </div>
        `;
      }

      chatBox.scrollTop = chatBox.scrollHeight;
    })
    .catch(err => {
      document.getElementById(loaderId).remove();
      chatBox.innerHTML += `<div style="color:red">${err}</div>`;
    });
  };

});
