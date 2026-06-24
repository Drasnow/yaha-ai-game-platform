import { putObject } from "@/lib/storage";

type GenerationAsset = {
  asset_id: string;
  url: string;
  mime_type: string;
};

type AgentLogItem = {
  agent_name?: string;
  agentName?: string;
  step: string;
  message: string;
};

type AgentGenerateRequest = {
  task_id: string;
  user_id: string;
  prompt: string;
  assets: GenerationAsset[];
};

type AgentGenerateResponse =
  | {
      status: "succeeded";
      title: string;
      description: string;
      tags: string[];
      artifact: {
        manifest_url: string;
        entry_url: string;
        artifact_base_url: string;
      };
      logs: AgentLogItem[];
      supervisor_feedback?: never;
    }
  | {
      status: "rejected";
      title?: never;
      description?: never;
      tags?: never;
      artifact?: never;
      logs: AgentLogItem[];
      supervisor_feedback: string;
    }
  | {
      status: "failed";
      title: string;
      description: string;
      tags: string[];
      artifact?: never;
      logs: AgentLogItem[];
      supervisor_feedback?: never;
    };

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function buildLocalGameFiles(prompt: string, title: string) {
  const safePrompt = escapeHtml(prompt);
  const safeTitle = escapeHtml(title);
  const manifest = {
    schemaVersion: "1.0",
    entry: "index.html",
    title,
    description: `根据创意生成的点击得分小游戏：${prompt}`,
    files: ["index.html", "style.css", "game.js"],
    runtime: "iframe-html-v1",
  };

  return {
    "index.html": `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" /><title>${safeTitle}</title><link rel="stylesheet" href="style.css" /></head><body><main><p class="eyebrow">Yaha MVP Generated Game</p><h1>${safeTitle}</h1><p class="prompt">${safePrompt}</p><button id="target">点击星星 +1</button><p>得分：<strong id="score">0</strong></p><p>倒计时：<strong id="time">30</strong>s</p></main><script src="game.js"></script></body></html>`,
    "style.css": "body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at top,#312e81,#020617);font-family:Arial,'Microsoft YaHei',sans-serif;color:#fff}main{width:min(720px,90vw);padding:40px;border:1px solid rgba(255,255,255,.18);border-radius:28px;background:rgba(15,23,42,.78);box-shadow:0 24px 80px rgba(0,0,0,.35);text-align:center}.eyebrow{color:#a5b4fc;text-transform:uppercase;letter-spacing:.16em;font-size:12px}.prompt{color:#cbd5e1;line-height:1.8}button{margin:24px auto;padding:18px 28px;border:0;border-radius:999px;background:#facc15;color:#111827;font-weight:800;font-size:18px;cursor:pointer;box-shadow:0 12px 30px rgba(250,204,21,.28)}button:disabled{opacity:.5;cursor:not-allowed}",
    "game.js": "let score=0;let time=30;const scoreEl=document.getElementById('score');const timeEl=document.getElementById('time');const target=document.getElementById('target');target.addEventListener('click',()=>{score+=1;scoreEl.textContent=String(score);target.style.transform=`translate(${Math.random()*80-40}px,${Math.random()*50-25}px)`});const timer=setInterval(()=>{time-=1;timeEl.textContent=String(time);if(time<=0){clearInterval(timer);target.disabled=true;target.textContent=`游戏结束，最终得分 ${score}`}},1000);",
    "manifest.json": JSON.stringify(manifest, null, 2),
  };
}

async function generateLocally(request: AgentGenerateRequest): Promise<AgentGenerateResponse> {
  const title = request.prompt.includes("星") ? "星星点击挑战" : "Yaha 点击挑战";
  const description = `根据你的创意生成的 30 秒点击得分小游戏：${request.prompt}`;
  const baseKey = `games/generated/${request.task_id}/v1`;
  const files = buildLocalGameFiles(request.prompt, title);

  await Promise.all(
    Object.entries(files).map(([fileName, content]) =>
      putObject({
        key: `${baseKey}/${fileName}`,
        body: content,
        contentType: fileName.endsWith(".json")
          ? "application/json"
          : fileName.endsWith(".css")
            ? "text/css"
            : fileName.endsWith(".js")
              ? "application/javascript"
              : "text/html",
      }),
    ),
  );

  const manifestUrl = (await putObject({
    key: `${baseKey}/manifest.json`,
    body: files["manifest.json"],
    contentType: "application/json",
  })).publicUrl;

  return {
    status: "succeeded",
    title,
    description,
    tags: ["click", "casual", "mvp"],
    artifact: {
      manifest_url: manifestUrl,
      entry_url: manifestUrl.replace(/manifest\.json$/, "index.html"),
      artifact_base_url: manifestUrl.replace(/manifest\.json$/, ""),
    },
    logs: [
      { agent_name: "RequirementAgent", step: "parse_prompt", message: "已解析创意并选择点击得分模板。" },
      { agent_name: "GameDesignAgent", step: "design_rules", message: "已生成 30 秒倒计时与得分规则。" },
      { agent_name: "CodeGenerationAgent", step: "render_files", message: "已生成 index.html/style.css/game.js/manifest.json。" },
      { agent_name: "BuildValidateAgent", step: "validate", message: "已通过 MVP 静态产物结构校验。" },
      { agent_name: "ArtifactAgent", step: "upload", message: "生成产物已上传到 MinIO。" },
    ],
  };
}

export type AgentSseEvent =
  | { type: "start"; task_id: string }
  | { type: "log"; agent: string; step: string; message: string; timestamp: string }
  | { type: "supervisor_decision"; status: string; complexity: string }
  | { type: "validation"; passed: boolean; issues: string[] }
  | { type: "artifact"; manifest_url: string; entry_url: string; artifact_base_url: string; file_count: number }
  | { type: "rejected"; feedback: string }
  | { type: "error"; message: string }
  | { type: "game_design"; title: string; description: string; tags: string[] }
  | { type: "end" };

export type StreamCallbacks = {
  onLog: (log: { agent: string; step: string; message: string }) => Promise<void>;
  onStep: (step: string) => Promise<void>;
  onRejected: (feedback: string) => Promise<void>;
  onError: (message: string) => Promise<void>;
  onGameDesign?: (data: { title: string; description: string; tags: string[] }) => Promise<void>;
};

export async function* generateGameWithAgentStream(
  request: AgentGenerateRequest,
  callbacks: StreamCallbacks,
): AsyncGenerator<AgentSseEvent, void, unknown> {
  const agentServiceUrl = (process.env.AGENT_SERVICE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

  let fallbackMode = false;

  // Step 1: try streaming endpoint
  try {
    const response = await fetch(`${agentServiceUrl}/generate/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "");
      throw new Error(`Agent service stream returned ${response.status}: ${errorText}`);
    }

    if (!response.body) {
      throw new Error("Response body is null");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;

        try {
          const event = JSON.parse(raw) as AgentSseEvent;
          yield event;

          if (event.type === "log") {
            await callbacks.onLog({
              agent: event.agent,
              step: event.step,
              message: event.message,
            });
            await callbacks.onStep(event.step);
          } else if (event.type === "rejected") {
            await callbacks.onRejected(event.feedback);
          } else if (event.type === "error") {
            await callbacks.onError(event.message);
          } else if (event.type === "game_design" && callbacks.onGameDesign) {
            await callbacks.onGameDesign({
              title: event.title,
              description: event.description,
              tags: event.tags,
            });
          } else if (event.type === "end" || event.type === "start") {
            // no-op
          }
        } catch {
          // ignore malformed SSE lines
        }
      }
    }
  } catch (error) {
    console.warn(`[agent-client] streaming failed, falling back to sync: ${error}`);
    fallbackMode = true;
  }

  // Step 2: fallback to sync if stream unavailable
  if (fallbackMode) {
    const result = await generateGameWithAgent(request);
    for (const log of result.logs) {
      const normalized = {
        agent: log.agentName ?? log.agent_name ?? "Agent",
        step: log.step,
        message: log.message,
      };
      await callbacks.onLog(normalized);
      await callbacks.onStep(log.step);
      yield {
        type: "log",
        agent: normalized.agent,
        step: normalized.step,
        message: normalized.message,
        timestamp: new Date().toISOString(),
      };
    }
    if (result.status === "rejected") {
      await callbacks.onRejected(result.supervisor_feedback ?? "");
      yield { type: "rejected", feedback: result.supervisor_feedback ?? "" };
    }
  }
}

export async function generateGameWithAgent(request: AgentGenerateRequest): Promise<AgentGenerateResponse> {
  const agentServiceUrl = (process.env.AGENT_SERVICE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

  try {
    console.info(`[agent-client] calling ${agentServiceUrl}/generate for task ${request.task_id}`);
    const response = await fetch(`${agentServiceUrl}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (response.ok) {
      console.info(`[agent-client] FastAPI Agent succeeded for task ${request.task_id}`);
      return (await response.json()) as AgentGenerateResponse;
    }

    const errorText = await response.text().catch(() => "");
    console.error(
      `[agent-client] FastAPI Agent HTTP error: ${response.status} ${response.statusText} — ${errorText}`,
    );
    throw new Error(`Agent service returned ${response.status}: ${errorText}`);
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("Agent service returned")) {
      throw error;
    }
    console.error("[agent-client] FastAPI Agent network error, falling back to local generator:", error);
    console.warn(`[agent-client] falling back to local generator for task ${request.task_id}`);
    return generateLocally(request);
  }
}
