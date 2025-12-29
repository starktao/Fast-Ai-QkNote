<template>
  <div>
    <header>
      <h1>Qianwen Bilibili Notes</h1>
      <p>Download audio, transcribe with Qwen Audio, and generate notes with Qwen text models.</p>
    </header>

    <section>
      <div class="section-title">
        <h2>API Configuration</h2>
        <span class="status">{{ configStatus }}</span>
      </div>
      <div class="grid">
        <label>
          API Key
          <input v-model="apiKey" type="password" placeholder="Enter DashScope API key" />
        </label>
      </div>
      <button :disabled="saving" @click="handleSave">
        {{ saving ? "Validating..." : "Validate & Save" }}
      </button>
      <div class="status" v-if="configMask">Saved key: {{ configMask }}</div>
    </section>

    <section>
      <div class="section-title">
        <h2>Generate Notes</h2>
        <span class="status">{{ generateStatus }}</span>
      </div>
      <div class="grid">
        <label>
          Bilibili URL
          <input v-model="videoUrl" type="text" placeholder="https://www.bilibili.com/video/..." />
        </label>
        <label>
          Style
          <select v-model="style">
            <option v-for="item in styles" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          Remark
          <textarea v-model="remark" placeholder="Optional notes for the model"></textarea>
        </label>
      </div>
      <button :disabled="creating" @click="handleCreate">
        {{ creating ? "Starting..." : "Generate" }}
      </button>
    </section>

    <section>
      <div class="section-title">
        <h2>Sessions</h2>
        <button :disabled="loadingSessions" @click="refreshSessions">
          {{ loadingSessions ? "Refreshing..." : "Refresh" }}
        </button>
      </div>
      <div class="sessions">
        <div class="session-list">
          <div
            v-for="item in sessions"
            :key="item.id"
            :class="['session-item', { active: item.id === selectedId }]"
            @click="selectSession(item.id)"
          >
            <div><strong>#{{ item.id }}</strong> {{ item.url }}</div>
            <div class="session-meta">
              <span>{{ item.status }} / {{ item.stage }}</span>
              <span>{{ item.updated_at }}</span>
            </div>
          </div>
          <div v-if="sessions.length === 0" class="status">No sessions yet.</div>
        </div>

        <div class="session-detail">
          <div v-if="selected">
            <div class="step" v-for="step in selected.steps" :key="step.step">
              <span>{{ step.step }}</span>
              <span class="badge">{{ step.status }}</span>
            </div>
            <div class="note-block" v-if="selected.session.error">
              Error: {{ selected.session.error }}
            </div>
            <div class="note-block" v-if="selected.session.transcript">
              <strong>Transcript</strong>
              <div>{{ selected.session.transcript }}</div>
            </div>
            <div class="note-block" v-if="selected.session.note">
              <strong>Note</strong>
              <div>{{ selected.session.note }}</div>
            </div>
          </div>
          <div v-else class="status">Select a session to see details.</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { createSession, getConfig, getSession, listSessions, saveConfig } from "./api";

const apiKey = ref("");
const configMask = ref("");
const configStatus = ref("");
const saving = ref(false);

const videoUrl = ref("");
const style = ref("general");
const remark = ref("");
const generateStatus = ref("");
const creating = ref(false);

const sessions = ref([]);
const selectedId = ref(null);
const selected = ref(null);
const loadingSessions = ref(false);
let poller = null;

const styles = ["general", "lecture", "meeting", "checklist", "mindmap"];

async function loadInitial() {
  const config = await getConfig();
  configMask.value = config.api_key_masked || "";
  configStatus.value = config.has_key ? "API key configured" : "API key not set";
  await refreshSessions();
}

async function handleSave() {
  saving.value = true;
  configStatus.value = "Validating key...";
  try {
    await saveConfig({
      api_key: apiKey.value,
    });
    configStatus.value = "Saved";
    apiKey.value = "";
    const config = await getConfig();
    configMask.value = config.api_key_masked || "";
  } catch (error) {
    configStatus.value = String(error.message || error);
  } finally {
    saving.value = false;
  }
}

async function handleCreate() {
  creating.value = true;
  generateStatus.value = "Starting session...";
  try {
    const result = await createSession({
      url: videoUrl.value,
      style: style.value,
      remark: remark.value,
    });
    generateStatus.value = `Session #${result.id} created.`;
    videoUrl.value = "";
    remark.value = "";
    await refreshSessions();
    await selectSession(result.id);
  } catch (error) {
    generateStatus.value = String(error.message || error);
  } finally {
    creating.value = false;
  }
}

async function refreshSessions() {
  loadingSessions.value = true;
  try {
    const data = await listSessions();
    sessions.value = data.items;
    if (selectedId.value) {
      await selectSession(selectedId.value, false);
    }
  } finally {
    loadingSessions.value = false;
  }
}

async function selectSession(id, scroll = true) {
  selectedId.value = id;
  const data = await getSession(id);
  selected.value = data;
  if (scroll) {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }
}

onMounted(async () => {
  try {
    await loadInitial();
  } catch (error) {
    configStatus.value = String(error.message || error);
  }
  poller = setInterval(refreshSessions, 5000);
});

onUnmounted(() => {
  if (poller) {
    clearInterval(poller);
  }
});
</script>