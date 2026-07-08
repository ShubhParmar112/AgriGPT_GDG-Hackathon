// AgriGPT shared front-end behaviour: password visibility, recommend form, crop cards, i18n.

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

const I18N = JSON.parse(document.getElementById("i18n-data")?.textContent || "{}");
const GEO_I18N = JSON.parse(document.getElementById("geo-i18n-data")?.textContent || "{}");
let currentLang = document.documentElement.dataset.lang || "en";

function t(key) {
  return (I18N[currentLang] && I18N[currentLang][key]) || (I18N.en && I18N.en[key]) || key;
}

// category is "states" | "soils" | "seasons"; englishValue is the
// <option value="..."> (always the original English dataset value).
function tGeo(category, englishValue) {
  const table = GEO_I18N[category] && GEO_I18N[category][currentLang];
  return (table && table[englishValue]) || englishValue;
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.setAttribute("placeholder", t(el.dataset.i18nPlaceholder));
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
    if (el.id === "theme-toggle") return; // kept in sync by initThemeToggle itself
    el.setAttribute("aria-label", t(el.dataset.i18nAria));
  });
  document.querySelectorAll("[data-i18n-options]").forEach((select) => {
    const category = select.dataset.i18nOptions;
    Array.from(select.options).forEach((option) => {
      if (!option.value) return; // leave the "Choose..." placeholder to data-i18n
      option.textContent = tGeo(category, option.value);
    });
  });

  const themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) {
    const isDark = document.documentElement.classList.contains("dark");
    themeBtn.setAttribute("aria-label", t(isDark ? "theme_toggle_light" : "theme_toggle_dark"));
  }
}

function initThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    const isDark = document.documentElement.classList.toggle("dark");
    const theme = isDark ? "dark" : "light";
    btn.setAttribute("aria-label", t(isDark ? "theme_toggle_light" : "theme_toggle_dark"));

    try {
      await fetch("/theme/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ theme }),
      });
    } catch (err) {
      // Non-fatal — the toggle still applies for this page view even if the save fails.
    }
  });
}

function initLanguageSelector() {
  const select = document.getElementById("language-select");
  if (!select) return;

  select.addEventListener("change", async () => {
    currentLang = select.value;
    document.documentElement.lang = currentLang;
    document.documentElement.dataset.lang = currentLang;
    applyTranslations();

    // Crop cards already on screen have their AI-translated text baked
    // in from the previous language's /recommend/ call — re-fetch them
    // so they don't stay stuck in the old language.
    const resultsSection = document.getElementById("results-section");
    if (lastRecommendPayload && resultsSection && !resultsSection.classList.contains("hidden")) {
      fetchAndRenderCrops(lastRecommendPayload.state, lastRecommendPayload.soil, lastRecommendPayload.season, { scroll: false });
    }

    try {
      await fetch("/language/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ language: currentLang }),
      });
    } catch (err) {
      // Non-fatal — the switch still applies for this page view even if the save fails.
    }
  });
}

function bindPasswordToggle(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const btn = document.querySelector(`[data-toggle-password="${inputId}"]`);
  if (!btn) return;

  btn.addEventListener("click", () => {
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    btn.classList.toggle("text-deep-green", !showing);
  });
}

function dotScale(level, max = 3) {
  let dots = "";
  for (let i = 1; i <= max; i++) {
    dots += i <= level
      ? '<span class="w-2.5 h-2.5 rounded-full bg-deep-green inline-block"></span>'
      : '<span class="w-2.5 h-2.5 rounded-full bg-gray-200 dark:bg-slate-600 inline-block"></span>';
  }
  return `<span class="flex items-center gap-1">${dots}</span>`;
}

function rupeeScale(level, max = 3) {
  const filled = "₹".repeat(level);
  const empty = '<span class="text-gray-300 dark:text-slate-600">' + "₹".repeat(max - level) + "</span>";
  return `<span class="font-bold text-deep-green dark:text-light-green">${filled}</span>${empty}`;
}

function difficultyLabel(level) {
  return t(["difficulty_easy", "difficulty_moderate", "difficulty_hard"][level - 1] || "difficulty_moderate");
}

const SUITABILITY_KEYS = {
  "Highly Recommended": "suitability_highly_recommended",
  "Recommended": "suitability_recommended",
  "Suitable": "suitability_suitable",
};

function suitabilityLabel(label) {
  const key = SUITABILITY_KEYS[label];
  return key ? t(key) : label;
}

function cropCardTemplate(crop, index) {
  const detailRow = (icon, label, value) => `
    <div class="flex items-start gap-2">
      <span class="text-lg leading-none">${icon}</span>
      <div>
        <p class="text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500">${label}</p>
        <p class="font-semibold text-gray-700 dark:text-gray-200">${value}</p>
      </div>
    </div>`;

  return `
  <div class="crop-card card-interactive bg-white dark:bg-slate-800 rounded-3xl shadow-card overflow-hidden animate-pop" style="animation-delay:${index * 60}ms">
    <button type="button" class="crop-card-toggle w-full text-left p-5 flex items-start gap-4 tap-target">
      <div class="w-16 h-16 shrink-0 rounded-2xl bg-light-green/40 dark:bg-slate-700 flex items-center justify-center text-3xl">${crop.emoji}</div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-xl font-bold text-gray-800 dark:text-gray-100 truncate">${crop.display_name || crop.name}</h3>
          <svg class="chevron-icon w-5 h-5 text-gray-400 dark:text-gray-500 shrink-0" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 9l6 6 6-6"/>
          </svg>
        </div>
        <span class="inline-block mt-2 text-sm font-semibold px-3 py-1 rounded-full ${crop.suitability.badgeClass}">${suitabilityLabel(crop.suitability.label)}</span>
        <div class="mt-3">
          <div class="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500 mb-1">
            <span>${t("crop_confidence")}</span>
            <span class="font-semibold text-deep-green-dark dark:text-light-green">${crop.confidence}%</span>
          </div>
          <div class="h-2 rounded-full bg-gray-100 dark:bg-slate-700 overflow-hidden">
            <div class="h-full rounded-full bg-deep-green confidence-fill" style="width:0%" data-target-width="${crop.confidence}%"></div>
          </div>
        </div>
      </div>
    </button>

    <div class="crop-details">
      <div>
        <div class="px-5 pb-5 pt-1 border-t border-gray-100 dark:border-slate-700">
          <div class="grid grid-cols-2 gap-4 text-sm sm:text-base pt-4">
            ${detailRow("🌱", t("crop_sowing"), crop.sowing)}
            ${detailRow("🌾", t("crop_harvest"), crop.harvest)}
            ${detailRow("💧", t("crop_water"), crop.water)}
            ${detailRow("☀️", t("crop_climate"), crop.climate)}
            ${detailRow("🟫", t("crop_soil"), crop.soil)}
            <div class="flex items-start gap-2">
              <span class="text-lg leading-none">📈</span>
              <div>
                <p class="text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500">${t("crop_difficulty")}</p>
                <p class="font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2">${difficultyLabel(crop.difficulty)} ${dotScale(crop.difficulty)}</p>
              </div>
            </div>
            <div class="flex items-start gap-2">
              <span class="text-lg leading-none">💰</span>
              <div>
                <p class="text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500">${t("crop_profitability")}</p>
                <p class="font-semibold text-gray-700 dark:text-gray-200">${rupeeScale(crop.profitability)}</p>
              </div>
            </div>
          </div>
          <div class="mt-4 bg-soft-beige dark:bg-slate-700 rounded-2xl p-4">
            <p class="text-xs uppercase tracking-wide text-gray-400 dark:text-gray-400 mb-1">${t("crop_tip")}</p>
            <p class="text-gray-700 dark:text-gray-200">${crop.tips}</p>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}

function renderCropResults(crops, { scroll = true } = {}) {
  const grid = document.getElementById("crop-results-grid");
  const section = document.getElementById("results-section");
  if (!grid || !section) return;

  grid.innerHTML = crops.map(cropCardTemplate).join("");
  section.classList.remove("hidden");

  // animate confidence bars in on the next paint
  requestAnimationFrame(() => {
    grid.querySelectorAll(".confidence-fill").forEach((bar) => {
      bar.style.width = bar.dataset.targetWidth;
    });
  });

  grid.querySelectorAll(".crop-card-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest(".crop-card").classList.toggle("expanded");
    });
  });

  if (scroll) section.scrollIntoView({ behavior: "smooth", block: "start" });
}

// Remembered so a language switch can re-fetch already-displayed crop
// results in the new language (their AI-translated text is baked in
// server-side at fetch time, so a client-only re-render can't update it).
let lastRecommendPayload = null;

async function fetchAndRenderCrops(state, soil, season, { scroll = true } = {}) {
  const btn = document.getElementById("recommend-btn");
  const icon = document.getElementById("recommend-btn-icon");
  const label = document.getElementById("recommend-btn-label");
  const errorBox = document.getElementById("recommend-error");
  if (!btn || !icon || !label || !errorBox) return;

  errorBox.classList.add("hidden");
  btn.disabled = true;
  icon.outerHTML = '<span id="recommend-btn-icon" class="spinner"></span>';
  label.textContent = t("recommend_btn_loading");

  try {
    const response = await fetch("/recommend/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ state, soil, season }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || t("error_generic"));

    lastRecommendPayload = { state, soil, season };
    renderCropResults(data.results, { scroll });
  } catch (err) {
    errorBox.textContent = `⚠️ ${err.message}`;
    errorBox.classList.remove("hidden");
  } finally {
    btn.disabled = false;
    document.getElementById("recommend-btn-icon").outerHTML = '<span id="recommend-btn-icon">🌱</span>';
    label.textContent = t("recommend_btn_label");
  }
}

function initRecommendForm() {
  const form = document.getElementById("recommend-form");
  if (!form) return;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const state = document.getElementById("state").value;
    const soil = document.getElementById("soil").value;
    const season = document.getElementById("season").value;
    fetchAndRenderCrops(state, soil, season);
  });
}

const AGRIMITRA_AVATAR = `
  <div class="w-8 h-8 rounded-full bg-light-green/60 dark:bg-slate-700 flex items-center justify-center shrink-0">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" class="w-5 h-5">
      <path d="M12 21c0-5.5 3.5-9 8-9-.5 5.5-4 9-8 9Z" fill="#2E7D32"/>
      <path d="M12 21c0-6-4-10-9-10 .5 6 4.5 10 9 10Z" fill="#2E7D32" fill-opacity="0.6"/>
      <path d="M12 21V9" stroke="#2E7D32" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
  </div>`;

function askAIUserBubble(text, initial) {
  return `
  <div class="flex justify-end items-end gap-2 animate-pop">
    <div class="max-w-[80%] bg-deep-green text-white rounded-2xl rounded-br-md px-4 py-3 shadow-sm">
      <p class="whitespace-pre-line">${text}</p>
    </div>
    <div class="w-8 h-8 rounded-full bg-gray-300 dark:bg-slate-600 flex items-center justify-center text-sm font-bold text-gray-700 dark:text-gray-100 shrink-0">${initial}</div>
  </div>`;
}

function askAIReplyBubble(text) {
  return `
  <div class="flex justify-start items-end gap-2 animate-pop">
    ${AGRIMITRA_AVATAR}
    <div class="max-w-[80%] bg-soft-beige dark:bg-slate-700 text-gray-800 dark:text-gray-100 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
      <p class="whitespace-pre-line">${text}</p>
    </div>
  </div>`;
}

function askAITypingBubble() {
  return `
  <div class="flex justify-start items-end gap-2" id="ask-ai-typing">
    ${AGRIMITRA_AVATAR}
    <div class="bg-soft-beige dark:bg-slate-700 text-gray-400 dark:text-gray-300 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-1 shadow-sm">
      <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
    </div>
  </div>`;
}

function initAskAI() {
  const form = document.getElementById("ask-ai-form");
  if (!form) return;

  const input = document.getElementById("ask-ai-input");
  const btn = document.getElementById("ask-ai-btn");
  const label = document.getElementById("ask-ai-btn-label");
  const errorBox = document.getElementById("ask-ai-error");
  const log = document.getElementById("ask-ai-log");
  const chips = document.getElementById("ask-ai-chips");
  const userInitial = document.getElementById("ask-ai-user-initial").dataset.initial || "U";

  const conversation = [];

  const scrollToBottom = () => { log.scrollTop = log.scrollHeight; };

  async function sendQuestion(question) {
    if (!question) return;

    chips?.remove();
    errorBox.classList.add("hidden");
    log.insertAdjacentHTML("beforeend", askAIUserBubble(question, userInitial));
    conversation.push({ role: "user", content: question });
    scrollToBottom();

    input.value = "";
    btn.disabled = true;
    label.textContent = t("ask_ai_sending");
    log.insertAdjacentHTML("beforeend", askAITypingBubble());
    scrollToBottom();

    try {
      const response = await fetch("/ask-ai/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ messages: conversation }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || t("error_generic"));

      document.getElementById("ask-ai-typing")?.remove();
      log.insertAdjacentHTML("beforeend", askAIReplyBubble(data.answer));
      conversation.push({ role: "assistant", content: data.answer });
      scrollToBottom();
    } catch (err) {
      document.getElementById("ask-ai-typing")?.remove();
      conversation.pop();
      errorBox.textContent = `⚠️ ${err.message}`;
      errorBox.classList.remove("hidden");
    } finally {
      btn.disabled = false;
      label.textContent = t("ask_ai_send");
    }
  }

  document.querySelectorAll(".ask-ai-chip").forEach((chip) => {
    chip.addEventListener("click", () => sendQuestion(chip.textContent.trim()));
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    sendQuestion(input.value.trim());
  });
}
