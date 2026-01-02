<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <img class="brand-logo" src="/mynote-icon.png" alt="Fast-Ai-QkNote logo" />
        <div>
          <h1>Fast-Ai-QkNote</h1>
        </div>
      </div>
      <div class="lang-switch">
        <span class="status">{{ t("language") }}</span>
        <div class="dropdown" ref="langDropdownRef" @click.stop>
          <button
            type="button"
            class="dropdown-trigger"
            :class="{ 'select-pulse': langPulse }"
            :aria-expanded="langOpen"
            @click="toggleLang"
          >
            <span>{{ currentLanguageLabel }}</span>
            <span class="dropdown-caret">&#9662;</span>
          </button>
          <Transition name="dropdown">
            <ul v-if="langOpen" class="dropdown-menu" role="listbox">
              <li v-for="option in languageOptions" :key="option.value">
                <button
                  type="button"
                  class="dropdown-option"
                  :class="{ active: option.value === language }"
                  @click="setLanguage(option.value)"
                >
                  {{ option.label }}
                </button>
              </li>
            </ul>
          </Transition>
        </div>
      </div>
    </header>

    <div class="app-shell" :class="{ 'is-focus': focusMode }">
      <aside class="panel left">
        <section class="panel-card">
          <div class="section-title">
            <h2>{{ t("controlCenter") }}</h2>
          </div>

          <div class="subsection">
            <div class="subsection-title">
              <h3>{{ t("apiConfig") }}</h3>
              <span class="status">{{ configStatusText }}</span>
            </div>
            <div class="grid">
              <label v-if="showApiKeyInput">
                {{ t("apiKey") }}
                <input v-model="apiKey" type="password" :placeholder="t('apiKeyPlaceholder')" />
              </label>
            </div>
            <button :disabled="saving" @click="handleSave">
              {{ saving ? t("validating") : apiKeyButtonLabel }}
            </button>
            <div class="status" v-if="configMask">{{ t("savedKey") }} {{ configMask }}</div>
          </div>

          <div class="divider"></div>

          <div class="subsection">
            <div class="subsection-title">
              <h3>{{ t("generateNotes") }}</h3>
              <span class="status">{{ generateStatusText }}</span>
            </div>
            <div class="grid">
              <label>
                {{ t("bilibiliUrl") }}
                <input v-model="videoUrl" type="text" :placeholder="t('bilibiliPlaceholder')" />
              </label>
              <label>
                {{ t("style") }}
                <div class="dropdown" ref="styleDropdownRef" @click.stop>
                  <button
                    type="button"
                    class="dropdown-trigger"
                    :class="{ 'select-pulse': stylePulse }"
                    :aria-expanded="styleOpen"
                    @click="toggleStyle"
                  >
                    <span>{{ currentStyleLabel }}</span>
                    <span class="dropdown-caret">&#9662;</span>
                  </button>
                  <Transition name="dropdown">
                    <ul v-if="styleOpen" class="dropdown-menu" role="listbox">
                      <li v-for="item in styles" :key="item.value">
                        <button
                          type="button"
                          class="dropdown-option"
                          :class="{ active: item.value === style }"
                          @click="setStyle(item.value)"
                        >
                          {{ item.label[language] }}
                        </button>
                      </li>
                    </ul>
                  </Transition>
                </div>
              </label>
              <label>
                {{ t("remark") }}
                <textarea v-model="remark" :placeholder="t('remarkPlaceholder')"></textarea>
              </label>
              <div class="toggle-row">
                <label class="switch">
                  <input id="include-joke" type="checkbox" v-model="includeJoke" />
                  <span class="switch-track" aria-hidden="true"></span>
                </label>
                <label class="toggle-text" for="include-joke">
                  <span class="toggle-title">{{ t("jokeToggle") }}</span>
                  <span class="toggle-hint">{{ t("jokeHint") }}</span>
                </label>
              </div>
            </div>
            <button :disabled="creating" @click="handleCreate">
              {{ creating ? t("starting") : t("generate") }}
            </button>
          </div>
        </section>
      </aside>

      <main class="panel center">
        <section class="panel-card">
          <div class="section-title">
            <h2>{{ t("workspace") }}</h2>
            <div class="workspace-actions">
              <button class="ghost-btn" @click="toggleFocus">
                {{ focusMode ? t("exitFocus") : t("focus") }}
              </button>
              <span class="status" v-if="selected">{{ t("session") }} #{{ selected.session.id }}</span>
            </div>
          </div>

          <Transition name="fade-slide" mode="out-in">
            <div v-if="selected" :key="selected.session.id" class="session-detail" ref="detailRef">
              <div class="detail-header">
                <div class="step-list">
                  <div
                    v-for="step in displaySteps"
                    :key="step.step"
                    class="step-pill"
                    :class="stepStatusClass(step.status)"
                    :title="formatStatus(step.status)"
                  >
                    <span class="step-label">{{ formatStage(step.step) }}</span>
                  </div>
                </div>
                <div class="detail-actions">
                  <button
                    class="ghost-btn"
                    :class="{ 'is-copied': copyState === 'copied' }"
                    :disabled="!selected.session.note"
                    @click="copyNote"
                  >
                    {{ copyButtonLabel }}
                  </button>
                  <button class="ghost-btn" :disabled="!selected.session.note" @click="exportPdf">
                    {{ t("exportPdf") }}
                  </button>
                </div>
              </div>
              <div class="note-block error" v-if="selected.session.error">
                {{ t("error") }}: {{ selected.session.error }}
              </div>

              <div class="toggle-group" v-if="selected.session.transcript || selected.session.note">
                <button
                  class="toggle-btn"
                  :class="{ active: detailTab === 'note' }"
                  :disabled="!selected.session.note"
                  @click="detailTab = 'note'"
                >
                  {{ t("note") }}
                </button>
                <button
                  class="toggle-btn"
                  :class="{ active: detailTab === 'transcript' }"
                  :disabled="!selected.session.transcript"
                  @click="detailTab = 'transcript'"
                >
                  {{ t("transcript") }}
                </button>
              </div>

              <Transition name="fade-slide" mode="out-in">
                <div class="note-block" v-if="detailTab === 'transcript'" key="transcript">
                  <strong>{{ t("transcript") }}</strong>
                  <div v-html="renderMarkdown(selected.session.transcript || t('noTranscript'))"></div>
                </div>
                <div class="note-block" v-else key="note">
                  <div class="note-header">
                    <span class="note-label">{{ t("sourceLink") }}</span>
                    <a
                      v-if="selected.session.url"
                      class="note-link"
                      :href="selected.session.url"
                      target="_blank"
                      rel="noopener"
                    >
                      {{ selected.session.url }}
                    </a>
                  </div>
                  <div v-html="renderMarkdown(selected.session.note || t('noNote'))"></div>
                </div>
              </Transition>
            </div>
            <div v-else key="empty" class="status">{{ t("selectSession") }}</div>
          </Transition>
        </section>
      </main>

      <aside class="panel right">
        <section class="panel-card">
          <div class="section-title">
            <h2>{{ t("sessions") }}</h2>
            <button :disabled="loadingSessions" @click="refreshSessions">
              {{ loadingSessions ? t("refreshing") : t("refresh") }}
            </button>
          </div>
          <div class="session-search">
            <input
              v-model="searchQuery"
              class="session-search-input"
              type="text"
              :placeholder="t('searchPlaceholder')"
            />
          </div>
          <div class="session-list">
            <div
              v-for="item in filteredSessions"
              :key="item.id"
              :class="['session-item', { active: item.id === selectedId }]"
              :ref="(el) => setSessionRef(item.id, el)"
              @click="selectSession(item.id)"
            >
              <div class="session-row">
                <div class="session-title">
                  <strong>#{{ item.id }}</strong> {{ item.title || item.url }}
                </div>
                <button class="session-delete" @click.stop="openDelete(item)">
                  {{ t("delete") }}
                </button>
              </div>
              <div class="session-meta">
                <span>{{ formatStatus(item.status) }} / {{ formatStage(item.stage) }}</span>
                <span>{{ item.updated_at }}</span>
              </div>
            </div>
            <div v-if="filteredSessions.length === 0" class="status">{{ t("noSessions") }}</div>
          </div>
        </section>
      </aside>
    </div>
  </div>
  <div v-if="selected" class="print-area">
    <h1 class="print-title">{{ printTitle }}</h1>
    <div class="print-link" v-if="printLink">
      <span class="print-label">{{ t("sourceLink") }}</span>
      <a :href="printLink" target="_blank" rel="noopener">{{ printLink }}</a>
    </div>
    <div class="print-body" v-html="renderMarkdown(selected.session.note || t('noNote'))"></div>
  </div>
  <Transition name="fade-slide">
    <div v-if="confirmOpen" class="modal-backdrop">
      <div class="modal-card">
        <h3>{{ t("confirmDeleteTitle") }}</h3>
        <p class="modal-text">{{ t("confirmDeleteBody") }}</p>
        <p class="modal-note" v-if="confirmTarget">
          {{ confirmTarget.title || confirmTarget.url }}
        </p>
        <div class="modal-actions">
          <button class="qk-button qk-ghost" :disabled="deleting" @click="closeDelete">
            {{ t("cancel") }}
          </button>
          <button class="qk-button" :disabled="deleting" @click="confirmDelete">
            {{ deleting ? t("deleting") : t("confirm") }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import DOMPurify from "dompurify";
import { marked } from "marked";

import { createSession, deleteSession, getConfig, getSession, listSessions, saveConfig } from "./api";

marked.setOptions({ breaks: true, gfm: true });

const language = ref("zh");
const langPulse = ref(false);
const langOpen = ref(false);
const styleOpen = ref(false);
const langDropdownRef = ref(null);
const styleDropdownRef = ref(null);
const copyState = ref("idle");
const focusMode = ref(false);
const searchQuery = ref("");
const confirmOpen = ref(false);
const confirmTarget = ref(null);
const deleting = ref(false);
const languageOptions = [
  { value: "zh", label: "中文" },
  { value: "en", label: "English" },
];
const translations = {
  en: {
    title: "Fast-Ai-QkNote",
    subtitle: "Download audio, transcribe with Qwen Audio, and generate notes with Qwen text models.",
    language: "Language",
    controlCenter: "Control Center",
    apiConfig: "API Configuration",
    apiKey: "API Key",
    apiKeyPlaceholder: "Enter DashScope API key",
    apiKeyMissing: "API key is required",
    validating: "Validating...",
    validateSave: "Validate & Save",
    editApiKey: "Edit API Key",
    savedKey: "Saved key:",
    generateNotes: "Generate Notes",
    bilibiliUrl: "Bilibili URL",
    bilibiliPlaceholder: "https://www.bilibili.com/video/...",
    style: "Style",
    jokeToggle: "Tell a joke",
    jokeHint: "A short joke at the end to aid understanding.",
    remark: "Remark",
    remarkPlaceholder: "Optional notes for the model",
    starting: "Starting...",
    generate: "Generate",
    workspace: "Note Workspace",
    session: "Session",
    sessions: "Sessions",
    refresh: "Refresh",
    refreshing: "Refreshing...",
    noSessions: "No sessions yet.",
    searchPlaceholder: "Search by title",
    delete: "Delete",
    confirmDeleteTitle: "Delete this session?",
    confirmDeleteBody: "This will permanently delete the session record and audio files.",
    confirm: "Delete",
    cancel: "Cancel",
    deleting: "Deleting...",
    selectSession: "Select a session to see details.",
    error: "Error",
    transcript: "Transcript",
    note: "Note",
    noTranscript: "No transcript yet.",
    noNote: "No note yet.",
    sourceLink: "Source link:",
    copyNote: "Copy Note",
    exportPdf: "Export PDF",
    copied: "Copied",
    copyFailed: "Copy Failed",
    focus: "Focus",
    exitFocus: "Exit Focus",
    configConfigured: "API key configured",
    configNotSet: "API key not set",
    configValidating: "Validating key...",
    configSaved: "Saved",
    sessionStarting: "Starting session...",
    sessionCreated: "Session #{id} created.",
    ready: "Ready",
  },
  zh: {
    title: "千问 Bilibili 笔记",
    subtitle: "下载音频，用千问语音转写，再用千问文本模型生成笔记。",
    language: "语言",
    controlCenter: "控制中心",
    apiConfig: "模型配置",
    apiKey: "API 密钥",
    apiKeyPlaceholder: "输入 DashScope API Key",
    apiKeyMissing: "请输入 API Key",
    validating: "校验中...",
    validateSave: "校验并保存",
    savedKey: "已保存密钥：",
    generateNotes: "生成笔记",
    bilibiliUrl: "Bilibili 链接",
    bilibiliPlaceholder: "https://www.bilibili.com/video/...",
    style: "风格",
    jokeToggle: "讲个笑话",
    jokeHint: "笔记末尾一个便于理解的笑话",
    remark: "备注",
    remarkPlaceholder: "给模型的可选说明",
    starting: "创建中...",
    generate: "生成",
    workspace: "笔记区域",
    session: "会话",
    sessions: "会话记录",
    refresh: "刷新",
    refreshing: "刷新中...",
    noSessions: "暂无会话。",
    searchPlaceholder: "按标题查找",
    delete: "删除",
    confirmDeleteTitle: "确认删除该会话？",
    confirmDeleteBody: "这将永久删除会话记录与音频文件。",
    confirm: "删除",
    cancel: "取消",
    deleting: "删除中...",
    selectSession: "选择会话以查看详情。",
    error: "错误",
    transcript: "转写",
    note: "笔记",
    noTranscript: "暂无转写内容。",
    noNote: "暂无笔记内容。",
    sourceLink: "原链接（点击跳转）：",
    copyNote: "复制笔记",
    exportPdf: "导出 PDF",
    copied: "已复制",
    copyFailed: "复制失败",
    focus: "专注",
    exitFocus: "退出专注",
    configConfigured: "API 已配置",
    configNotSet: "未配置 API",
    configValidating: "校验密钥中...",
    configSaved: "已保存",
    editApiKey: "修改apikey",
    sessionStarting: "正在创建会话...",
    sessionCreated: "会话 #{id} 已创建。",
    ready: "就绪",
  },
};

function t(key, params = {}) {
  const value = translations[language.value][key] || key;
  return value.replace(/\{(\w+)\}/g, (_, token) => String(params[token] ?? ""));
}

const apiKey = ref("");
const configMask = ref("");
const saving = ref(false);
const editingApiKey = ref(false);

const configStatusKey = ref("configNotSet");
const configStatusParams = ref({});
const configStatusRaw = ref("");
const configStatusText = computed(() =>
  configStatusKey.value ? t(configStatusKey.value, configStatusParams.value) : configStatusRaw.value,
);

const showApiKeyInput = computed(() => !configMask.value || editingApiKey.value);

const apiKeyButtonLabel = computed(() => {
  if (!configMask.value || editingApiKey.value) {
    return t("validateSave");
  }
  return t("editApiKey");
});

const videoUrl = ref("");
const style = ref("video_faithful");
const remark = ref("");
const includeJoke = ref(true);
const creating = ref(false);

const generateStatusKey = ref("ready");
const generateStatusParams = ref({});
const generateStatusRaw = ref("");
const generateStatusText = computed(() =>
  generateStatusKey.value ? t(generateStatusKey.value, generateStatusParams.value) : generateStatusRaw.value,
);

const sessions = ref([]);
const selectedId = ref(null);
const selected = ref(null);
const loadingSessions = ref(false);
const detailTab = ref("note");
const detailRef = ref(null);
const stylePulse = ref(false);
const sessionRefs = new Map();
let sessionsStream = null;
let detailStream = null;
let langPulseTimer = null;
let stylePulseTimer = null;
let copyTimer = null;
const INCLUDE_JOKE_KEY = "qknote.includeJoke";

const styles = [
  { value: "video_faithful", label: { en: "Video faithful", zh: "贴近视频" } },
  { value: "understand_memory", label: { en: "Understand & remember", zh: "理解记忆" } },
  { value: "concise", label: { en: "Concise", zh: "简明扼要" } },
  { value: "moments", label: { en: "Moments", zh: "朋友圈风格" } },
];

const currentLanguageLabel = computed(() => {
  return languageOptions.find((option) => option.value === language.value)?.label || "中文";
});

const currentStyleLabel = computed(() => {
  const item = styles.find((entry) => entry.value === style.value);
  return item ? item.label[language.value] : styles[0].label[language.value];
});

const copyButtonLabel = computed(() => {
  if (copyState.value === "copied") {
    return t("copied");
  }
  if (copyState.value === "failed") {
    return t("copyFailed");
  }
  return t("copyNote");
});

const printTitle = computed(() => {
  const session = selected.value?.session;
  return session?.title || session?.url || "Fast-Ai-QkNote";
});

const printLink = computed(() => {
  return selected.value?.session?.url || "";
});

const filteredSessions = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) {
    return sessions.value;
  }
  return sessions.value.filter((item) => {
    const title = (item.title || "").toLowerCase();
    return title.includes(query);
  });
});

const statusLabels = {
  pending: { en: "pending", zh: "等待" },
  running: { en: "running", zh: "进行中" },
  completed: { en: "completed", zh: "完成" },
  failed: { en: "failed", zh: "失败" },
};

const stageLabels = {
  download: { en: "download", zh: "下载" },
  transcribe: { en: "transcribe", zh: "转写" },
  note: { en: "note", zh: "笔记" },
};

const stepOrder = ["download", "transcribe", "note"];
const displaySteps = computed(() => {
  const map = new Map();
  (selected.value?.steps || []).forEach((item) => {
    map.set(item.step, item.status);
  });
  return stepOrder.map((step) => ({
    step,
    status: map.get(step) || "pending",
  }));
});

function formatStatus(value) {
  return statusLabels[value]?.[language.value] || value;
}

function formatStage(value) {
  return stageLabels[value]?.[language.value] || value;
}

function setConfigStatusKey(key, params = {}) {
  configStatusKey.value = key;
  configStatusParams.value = params;
  configStatusRaw.value = "";
}

function setConfigStatusRaw(message) {
  configStatusKey.value = "";
  configStatusParams.value = {};
  configStatusRaw.value = message;
}

function normalizeApiKey(value) {
  return value.trim().replace(/^Bearer\s+/i, "");
}

function setGenerateStatusKey(key, params = {}) {
  generateStatusKey.value = key;
  generateStatusParams.value = params;
  generateStatusRaw.value = "";
}

function setGenerateStatusRaw(message) {
  generateStatusKey.value = "";
  generateStatusParams.value = {};
  generateStatusRaw.value = message;
}

function setDetailTab(session) {
  if (session?.note) {
    detailTab.value = "note";
  } else if (session?.transcript) {
    detailTab.value = "transcript";
  } else {
    detailTab.value = "note";
  }
}

function triggerPulse(targetRef, timerRef) {
  targetRef.value = false;
  requestAnimationFrame(() => {
    targetRef.value = true;
  });
  if (timerRef) {
    clearTimeout(timerRef);
  }
  return setTimeout(() => {
    targetRef.value = false;
  }, 320);
}

function handleLangChange() {
  langPulseTimer = triggerPulse(langPulse, langPulseTimer);
}

function handleStyleChange() {
  stylePulseTimer = triggerPulse(stylePulse, stylePulseTimer);
}

function toggleLang() {
  langOpen.value = !langOpen.value;
  if (langOpen.value) {
    styleOpen.value = false;
  }
}

function toggleStyle() {
  styleOpen.value = !styleOpen.value;
  if (styleOpen.value) {
    langOpen.value = false;
  }
}

function setLanguage(value) {
  if (language.value !== value) {
    language.value = value;
    handleLangChange();
  }
  langOpen.value = false;
}

function setStyle(value) {
  if (style.value !== value) {
    style.value = value;
    handleStyleChange();
  }
  styleOpen.value = false;
}

function closeDropdowns() {
  langOpen.value = false;
  styleOpen.value = false;
}

function handleDocumentClick(event) {
  const target = event.target;
  if (langDropdownRef.value && langDropdownRef.value.contains(target)) {
    return;
  }
  if (styleDropdownRef.value && styleDropdownRef.value.contains(target)) {
    return;
  }
  closeDropdowns();
}

function handleDocumentKeydown(event) {
  if (event.key === "Escape") {
    closeDropdowns();
  }
}

function toggleFocus() {
  focusMode.value = !focusMode.value;
}

function openDelete(item) {
  confirmTarget.value = item;
  confirmOpen.value = true;
}

function closeDelete() {
  if (deleting.value) {
    return;
  }
  confirmOpen.value = false;
  confirmTarget.value = null;
}

async function confirmDelete() {
  if (!confirmTarget.value) {
    return;
  }
  deleting.value = true;
  try {
    await deleteSession(confirmTarget.value.id);
    sessions.value = sessions.value.filter((item) => item.id !== confirmTarget.value.id);
    if (selectedId.value === confirmTarget.value.id) {
      stopDetailStream();
      selectedId.value = null;
      selected.value = null;
    }
    confirmOpen.value = false;
    confirmTarget.value = null;
  } finally {
    deleting.value = false;
  }
}

function setCopyState(state) {
  copyState.value = state;
  if (copyTimer) {
    clearTimeout(copyTimer);
    copyTimer = null;
  }
  if (state !== "idle") {
    copyTimer = setTimeout(() => {
      copyState.value = "idle";
    }, 1500);
  }
}

function resetCopyState() {
  if (copyTimer) {
    clearTimeout(copyTimer);
    copyTimer = null;
  }
  copyState.value = "idle";
}

function fallbackCopy(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.top = "-1000px";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand("copy");
    setCopyState("copied");
  } catch {
    setCopyState("failed");
  } finally {
    document.body.removeChild(textarea);
  }
}

async function copyNote() {
  const note = selected.value?.session?.note;
  if (!note) {
    return;
  }
  const url = selected.value?.session?.url;
  const parts = [];
  if (url) {
    parts.push(`${t("sourceLink")} ${url}`);
  }
  parts.push(note);
  const text = parts.join("\n\n");
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      setCopyState("copied");
    } else {
      fallbackCopy(text);
    }
  } catch {
    fallbackCopy(text);
  }
}

function exportPdf() {
  const session = selected.value?.session;
  if (!session?.note) {
    return;
  }
  const originalTitle = document.title;
  const nextTitle = session.title || session.url || "Fast-Ai-QkNote";
  const restoreTitle = () => {
    document.title = originalTitle;
    window.removeEventListener("afterprint", restoreTitle);
  };
  window.addEventListener("afterprint", restoreTitle, { once: true });
  document.title = nextTitle;
  window.print();
  setTimeout(restoreTitle, 1000);
}

function stepStatusClass(status) {
  return {
    "is-pending": status === "pending",
    "is-running": status === "running",
    "is-completed": status === "completed",
    "is-failed": status === "failed",
  };
}

function renderMarkdown(value) {
  if (value === null || value === undefined) {
    return "";
  }
  const raw = marked.parse(String(value));
  return DOMPurify.sanitize(raw);
}

function setSessionRef(id, el) {
  if (el) {
    sessionRefs.set(id, el);
  } else {
    sessionRefs.delete(id);
  }
}

function scrollSessionIntoView(id) {
  const node = sessionRefs.get(id);
  if (!node || typeof node.scrollIntoView !== "function") {
    return;
  }
  requestAnimationFrame(() => {
    node.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

function resetDetailScroll() {
  if (!detailRef.value) {
    return;
  }
  detailRef.value.scrollTo({ top: 0, behavior: "smooth" });
}

function startSessionsStream() {
  if (sessionsStream) {
    sessionsStream.close();
  }
  sessionsStream = new EventSource("/api/sessions/stream");
  sessionsStream.addEventListener("sessions", (event) => {
    const data = JSON.parse(event.data || "{}");
    sessions.value = data.items || [];
  });
}

function stopSessionsStream() {
  if (sessionsStream) {
    sessionsStream.close();
    sessionsStream = null;
  }
}

function startDetailStream(sessionId) {
  if (detailStream) {
    detailStream.close();
  }
  detailStream = new EventSource(`/api/sessions/${sessionId}/stream`);
  detailStream.addEventListener("session", (event) => {
    const data = JSON.parse(event.data || "{}");
    if (data.session) {
      selected.value = data;
      setDetailTab(data.session);
      resetCopyState();
    }
  });
}

function stopDetailStream() {
  if (detailStream) {
    detailStream.close();
    detailStream = null;
  }
}

async function loadInitial() {
  const config = await getConfig();
  configMask.value = config.api_key_masked || "";
  setConfigStatusKey(config.has_key ? "configConfigured" : "configNotSet");
  setGenerateStatusKey("ready");
  editingApiKey.value = false;
}

async function handleSave() {
  if (configMask.value && !editingApiKey.value) {
    editingApiKey.value = true;
    return;
  }
  saving.value = true;
  setConfigStatusKey("configValidating");
  const normalizedKey = normalizeApiKey(apiKey.value);
  if (!normalizedKey) {
    setConfigStatusRaw(t("apiKeyMissing"));
    saving.value = false;
    return;
  }
  try {
    await saveConfig({
      api_key: normalizedKey,
    });
    apiKey.value = "";
    const config = await getConfig();
    configMask.value = config.api_key_masked || "";
    setConfigStatusKey(config.has_key ? "configConfigured" : "configNotSet");
    editingApiKey.value = false;
  } catch (error) {
    setConfigStatusRaw(String(error.message || error));
  } finally {
    saving.value = false;
  }
}

async function handleCreate() {
  creating.value = true;
  setGenerateStatusKey("sessionStarting");
  try {
    const result = await createSession({
      url: videoUrl.value,
      style: style.value,
      remark: remark.value,
      include_joke: includeJoke.value,
    });
    setGenerateStatusKey("sessionCreated", { id: result.id });
    videoUrl.value = "";
    remark.value = "";
    await refreshSessions();
    await selectSession(result.id);
  } catch (error) {
    setGenerateStatusRaw(String(error.message || error));
  } finally {
    creating.value = false;
  }
}

async function refreshSessions() {
  loadingSessions.value = true;
  try {
    const data = await listSessions();
    sessions.value = data.items;
  } finally {
    loadingSessions.value = false;
  }
}

async function selectSession(id, scroll = true) {
  selectedId.value = id;
  startDetailStream(id);
  const data = await getSession(id);
  selected.value = data;
  setDetailTab(data.session);
  resetCopyState();
  await nextTick();
  resetDetailScroll();
  if (scroll) {
    scrollSessionIntoView(id);
  }
}

onMounted(async () => {
  try {
    const storedJoke = localStorage.getItem(INCLUDE_JOKE_KEY);
    if (storedJoke !== null) {
      includeJoke.value = storedJoke === "true";
    }
  } catch {}
  try {
    await loadInitial();
  } catch (error) {
    setConfigStatusRaw(String(error.message || error));
  }
  startSessionsStream();
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleDocumentKeydown);
});

watch(includeJoke, (value) => {
  try {
    localStorage.setItem(INCLUDE_JOKE_KEY, value ? "true" : "false");
  } catch {}
});

onUnmounted(() => {
  stopSessionsStream();
  stopDetailStream();
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleDocumentKeydown);
});
</script>
