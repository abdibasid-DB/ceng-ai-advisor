import { expect, test } from "@playwright/test";

const source = {
  source_id: "src_1", title: "Engineering Handbook", source_name: "University",
  publication_date: "2025-09-01", category: "curriculum", source_type: "guide",
  evidence_labels: ["S1"], best_similarity_score: 0.875,
  supporting_passages: ["Computer engineers design hardware and software."],
};

async function mockApi(page, { delay = 0, fail = false, answer = "## Engineering\n\nStudy **hardware** and software [S1].\n\n- Circuits\n- Programming\n\n`[S1]`" } = {}) {
  const requests = [];
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/sources")) return route.fulfill({ json: { count: 12, indexed_count: 9, sources: [source] } });
    if (path.endsWith("/readiness")) return route.fulfill({ json: { status: "ready" } });
    const request = route.request().postDataJSON();
    requests.push(request);
    if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
    if (fail) return route.fulfill({ status: 503, json: { error: "Model unavailable" } });
    return route.fulfill({ contentType: "application/x-ndjson", body: JSON.stringify({
      event: "final", data: { session_id: request.session_id, status: "answered",
        answer,
        sources: [{ ...source, publication_date: undefined }] },
    }) });
  });
  return requests;
}

for (const width of [375, 768, 1280]) {
  test(`purpose panel is collapsible and fits at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockApi(page);
    await page.goto("/#advisor");
    const panel = page.locator(".advisor-purpose");
    const toggle = panel.locator("summary");
    await expect(panel.locator("ol")).toBeHidden();
    await toggle.focus();
    await page.keyboard.press("Enter");
    await expect(panel.locator("ol li")).toHaveCount(4);
    await expect(panel).toContainText("prospective OSTİM Computer Engineering students");
    await expect(panel).toContainText("no commercial AI API");
    await expect(panel).toContainText("does not have enough information");
    await expect(panel.locator("ol")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const bounds = await panel.boundingBox();
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    await page.screenshot({ path: `node_modules/.cache/purpose-${width}.png`, fullPage: true });
    await toggle.click();
    await expect(panel.locator("ol")).toBeHidden();
  });

  test(`home, chat, citations and history at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const requests = await mockApi(page);
    await page.goto("/");
    await expect(page.locator(".summary-number")).toHaveText("12");
    await expect(page.locator(".summary-panel")).toContainText("9 indexed");
    await page.getByRole("button", { name: "Ask in Advisor" }).first().click();
    await expect(page.locator(".message-text h2")).toHaveText("Engineering");
    await expect(page.locator(".message-text strong")).toHaveText("hardware");
    await expect(page.locator(".citation-badge")).toHaveCount(1);
    await expect(page.locator(".source-card")).toContainText("2025-09-01");
    await expect(page.locator(".source-card")).toContainText("0.875");
    await page.locator(".citation-badge").click();
    await expect(page.locator(".source-card")).toBeFocused();
    await page.evaluate(() => { window.copiedAnswer = ""; Object.defineProperty(navigator, "clipboard", {
      value: { writeText: async (text) => { window.copiedAnswer = text; } }, configurable: true,
    }); });
    await page.getByRole("button", { name: "Copy answer" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Copied" })).toBeVisible();
    expect(await page.evaluate(() => window.copiedAnswer)).toContain("**hardware**");
    await page.getByRole("button", { name: "New Conversation", exact: true }).click();
    await page.getByLabel("Ask a question", { exact: true }).fill("What careers are available?");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await expect(page.locator(".message-text h2")).toBeVisible();
    expect(requests[0].session_id).not.toBe(requests[1].session_id);
    await page.getByRole("complementary", { name: "Conversation history" }).getByRole("button", { name: "What is Computer Engineering?", exact: true }).click();
    await page.getByLabel("Ask a question", { exact: true }).fill("What should I study next?");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await expect(page.locator(".assistant-message")).toHaveCount(2);
    expect(requests[2].session_id).toBe(requests[0].session_id);
    await page.reload();
    await expect(page.locator(".assistant-message")).toHaveCount(2);
    await page.screenshot({ path: `node_modules/.cache/advisor-${width}.png`, fullPage: true });
    for (const id of ["home", "advisor", "computer-engineering", "sources", "about-project"]) {
      await page.locator(`.site-nav a[href="#${id}"]`).click();
      await expect(page.locator(".site-nav a[aria-current='page']")).toHaveAttribute("href", `#${id}`);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `${id} page width at ${width}px`).toBe(true);
      const overflow = await page.evaluate(() => [...document.querySelectorAll("body *")]
        .filter((element) => element.getBoundingClientRect().right > window.innerWidth + 1)
        .map((element) => `${element.tagName}.${element.className}: ${element.textContent.slice(0, 90)}`));
      expect(overflow, `${id} overflows at ${width}px`).toEqual([]);
    }
    expect(requests).toHaveLength(3);
  });
}

test("theme follows system by default and remembers a manual choice", async ({ page }) => {
  await mockApi(page);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByLabel("Theme").selectOption("dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("final answers reveal in 1.6 seconds; clicking skips and citations still work", async ({ page }) => {
  await mockApi(page);
  await page.goto("/#advisor");
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  const ask = async () => {
    await page.getByLabel("Ask a question", { exact: true }).fill("Explain engineering");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await expect(page.getByRole("button", { name: "Skip animation" })).toBeVisible();
  };
  await ask();
  const answer = page.locator(".assistant-message .message-text").first();
  await expect(answer).toHaveAttribute("data-animating", "true");
  await page.clock.runFor(800);
  expect((await answer.textContent()).length).toBeGreaterThan(0);
  await expect(answer).not.toContainText("Programming");
  await page.clock.runFor(850);
  await expect(answer).toHaveAttribute("data-animating", "false");
  await expect(answer).toContainText("Programming");
  await expect(page.getByRole("button", { name: "Skip animation" })).toHaveCount(0);
  await page.locator(".citation-badge").click();
  await expect(page.locator(".source-card")).toBeFocused();

  await ask();
  await page.clock.runFor(200);
  await page.locator(".assistant-message .message-text").last().click();
  await expect(page.locator(".assistant-message .message-text").last()).toHaveAttribute("data-animating", "false");
  await expect(page.locator(".assistant-message .message-text").last()).toContainText("Programming");
  await page.locator(".citation-badge").last().click();
  await expect(page.locator(".source-card").last()).toBeFocused();
  await page.reload();
  await expect(page.locator('[data-animating="true"]')).toHaveCount(0);
});

test("skip control works with the keyboard and reduced motion finishes an active reveal", async ({ page }) => {
  await mockApi(page);
  await page.goto("/#advisor");
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  for (const method of ["keyboard", "reduced-motion"]) {
    await page.getByLabel("Ask a question", { exact: true }).fill("Explain engineering");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    const skip = page.getByRole("button", { name: "Skip animation" });
    await expect(skip).toBeVisible();
    if (method === "keyboard") {
      await skip.focus();
      await page.keyboard.press("Enter");
    } else {
      await page.emulateMedia({ reducedMotion: "reduce" });
    }
    await expect(page.locator(".assistant-message .message-text").last()).toContainText("Programming");
    await expect(skip).toHaveCount(0);
  }
});

test("reduced motion renders full code with syntax colors following the app theme", async ({ page }) => {
  const codeAnswer = "Use `const` here.\n\n```javascript\nconst greeting = \"Hello\"; // example\nconsole.log(greeting);\n```\n\n[S1]\n\n```unknown-language\nplain <example>\n```";
  await mockApi(page, { answer: codeAnswer });
  await page.emulateMedia({ reducedMotion: "reduce", colorScheme: "light" });
  await page.goto("/#advisor");
  await page.getByLabel("Ask a question", { exact: true }).fill("Show code");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".assistant-message .message-text")).toHaveAttribute("data-animating", "false");
  await expect(page.getByRole("button", { name: "Skip animation" })).toHaveCount(0);
  await expect(page.locator("pre .hljs-keyword")).toHaveText("const");
  await expect(page.locator("pre .hljs-string")).toHaveText('"Hello"');
  await expect(page.locator("p > code")).toHaveText("const");
  await expect(page.locator(".language-unknown-language")).toHaveText("plain <example>\n");
  const keyword = page.locator(".hljs-keyword");
  const lightColor = await keyword.evaluate((element) => getComputedStyle(element).color);
  await page.getByLabel("Theme").selectOption("dark");
  await expect(keyword).not.toHaveCSS("color", lightColor);
  for (const width of [375, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.locator(".message-text").last().screenshot({ path: `node_modules/.cache/code-dark-${width}.png` });
  }
  await page.locator(".citation-badge").click();
  await expect(page.locator(".source-card")).toBeFocused();
});

test("switching conversations while a reply is pending keeps the reply in its original chat", async ({ page }) => {
  await mockApi(page, { delay: 800 });
  await page.goto("/#advisor");
  await page.getByLabel("Ask a question", { exact: true }).fill("What is Computer Engineering?");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByText("Searching the knowledge base…", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "New Conversation", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Start with a question" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeDisabled();
  await page.locator(".history-panel").getByRole("button", { name: /What is Computer Engineering/ }).click();
  await expect(page.locator(".message-text h2")).toBeVisible();
});

test("service errors end progress and allow another question", async ({ page }) => {
  await mockApi(page, { fail: true });
  await page.goto("/#advisor");
  await page.getByLabel("Ask a question", { exact: true }).fill("What is Computer Engineering?");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".status-error")).toContainText("Model unavailable");
  await expect(page.locator(".loading-message")).toHaveCount(0);
  await expect(page.getByLabel("Ask a question", { exact: true })).toBeEnabled();
});

test("help is friendly and all five examples send questions in the same chat", async ({ page }) => {
  await mockApi(page);
  const examples = [
    "What is Computer Engineering at OSTIM Technical University?",
    "What courses are taught in Computer Engineering?",
    "Do I need programming experience before starting Computer Engineering?",
    "How do internships work at OSTIM Technical University?",
    "What careers can Computer Engineering graduates pursue?",
  ];
  const requests = [];
  await page.route("**/api/v1/chat/stream", async (route) => {
    const request = route.request().postDataJSON();
    requests.push(request);
    const isHelp = requests.length === 1;
    await route.fulfill({ contentType: "application/x-ndjson", body: JSON.stringify({
      event: "final", data: {
        session_id: request.session_id, status: isHelp ? "help" : "answered",
        answer: isHelp ? "Hi! I'm a local advisor for prospective OSTİM Computer Engineering students. Try an example:" : "A sourced answer.",
        example_questions: isHelp ? examples : [], sources: [], llm_called: !isHelp,
      },
    }) });
  });
  await page.goto("/#advisor");
  await page.getByLabel("Ask a question", { exact: true }).fill("What can I ask you?");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const help = page.locator(".status-help");
  await expect(help).toContainText("prospective OSTİM");
  await expect(help.locator(".message-status")).toHaveCount(0);
  await expect(page.locator(".status-out_of_scope")).toHaveCount(0);
  await expect(help.getByRole("button", { name: /\?$/ })).toHaveCount(5);
  await page.reload();
  for (const [index, question] of examples.entries()) {
    await help.getByRole("button", { name: question, exact: true }).click();
    await expect(page.locator(".user-message").last()).toHaveText(question);
    await expect(page.locator(".status-answered")).toHaveCount(index + 1);
    await expect(help.getByRole("button", { name: examples[0], exact: true })).toBeEnabled();
    expect(requests[index + 1].question).toBe(question);
    expect(requests[index + 1].session_id).toBe(requests[0].session_id);
  }
});

test("unrelated questions still display the out-of-scope warning", async ({ page }) => {
  await mockApi(page);
  await page.route("**/api/v1/chat/stream", (route) => route.fulfill({
    contentType: "application/x-ndjson", body: JSON.stringify({ event: "final", data: {
      status: "out_of_scope", answer: "Please ask about Computer Engineering.", sources: [], example_questions: [],
    } }),
  }));
  await page.goto("/#advisor");
  await page.getByLabel("Ask a question", { exact: true }).fill("pizza");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".status-out_of_scope .message-status")).toHaveText("Out of scope");
  await expect(page.getByLabel("Help example questions")).toHaveCount(0);
});

test("stream metadata drives retrieval progress before the final answer", async ({ page }) => {
  await mockApi(page);
  await page.addInitScript(() => {
    const originalFetch = window.fetch;
    window.fetch = (url, options) => {
      if (!String(url).endsWith("/chat/stream")) return originalFetch(url, options);
      return Promise.resolve(new Response(new ReadableStream({ start(controller) {
        const encoder = new TextEncoder();
        window.emitAdvisorEvent = (event, data, close = false) => {
          const line = JSON.stringify({ event, data }) + (close ? "" : "\n");
          // Split records across chunks to exercise the NDJSON parser.
          controller.enqueue(encoder.encode(line.slice(0, 13)));
          controller.enqueue(encoder.encode(line.slice(13)));
          if (close) controller.close();
        };
      } }), { headers: { "Content-Type": "application/x-ndjson" } }));
    };
  });
  await page.goto("/#advisor");
  await page.getByLabel("Ask a question", { exact: true }).fill("What is Computer Engineering?");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByText("Searching the knowledge base…", { exact: true })).toBeVisible();
  await page.evaluate(() => window.emitAdvisorEvent("metadata", {
    retrieved_context: [{ label: "S1", title: "Engineering Handbook" }, { label: "S2", title: "Engineering Handbook" }], llm_called: true,
  }));
  await expect(page.getByText("Found 2 passages from: Engineering Handbook", { exact: true })).toBeVisible();
  await expect(page.getByText("Writing the answer with the local model…", { exact: true })).toBeVisible();
  await page.evaluate(() => window.emitAdvisorEvent("token", { text: "Unvalidated draft" }));
  await expect(page.getByText("Unvalidated draft", { exact: true })).toHaveCount(0);
  await page.evaluate(() => window.emitAdvisorEvent("final", { status: "answered", answer: "Verified answer", sources: [] }, true));
  await expect(page.locator(".message-text").getByText("Verified answer", { exact: true })).toBeVisible();
  await expect(page.locator(".loading-message")).toHaveCount(0);
});
