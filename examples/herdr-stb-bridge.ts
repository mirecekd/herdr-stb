// examples/herdr-stb-bridge.ts  (copy to ~/.pi/agent/extensions/, replaces herdr-ask-user-bridge.ts)
// Connects @juicesharp/rpiv-ask-user-question to Herdr and to herdr-stb:
//  - a pane waiting for an answer shows as "blocked" in Herdr (emits herdr:blocked),
//  - the open questions are written to ~/.config/herdr-stb/questions/ so the service can offer them in Telegram,
//  - answers the service drops into ~/.config/herdr-stb/answers/ are handed back to ask-user.
// Kept separate from herdr-agent-state.ts, which `herdr integration install pi` overwrites.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const base = path.join(os.homedir(), ".config", "herdr-stb");
const qdir = path.join(base, "questions");
const adir = path.join(base, "answers");

export default function (pi: any) {
  const open = new Map<string, { file: string; label: string }>();
  const pane = process.env.HERDR_PANE_ID;
  let timer: ReturnType<typeof setInterval> | undefined;

  const rm = (f: string) => { try { fs.unlinkSync(f); } catch { /* already gone */ } };
  const forget = (id: string) => {
    const o = open.get(id);
    if (!o) return;
    rm(path.join(qdir, o.file));
    rm(path.join(adir, o.file));
    open.delete(id);
  };
  const syncTimer = () => {
    if (open.size && !timer) timer = setInterval(poll, 1000);
    if (!open.size && timer) { clearInterval(timer); timer = undefined; }
  };

  function poll() {
    for (const [id, o] of open) {
      const f = path.join(adir, o.file);
      let raw: string;
      try { raw = fs.readFileSync(f, "utf8"); } catch { continue; }
      rm(f);
      try { pi.events.emit("rpiv:ask-user:answer", { ...JSON.parse(raw), toolCallId: id }); } catch { /* bad file, ignore */ }
    }
  }

  pi.events.on("rpiv:ask-user:prompt", (d: any) => {
    const id = d?.toolCallId;
    if (!id) return;
    const file = String(id).replace(/[^A-Za-z0-9_.-]/g, "_") + ".json";
    open.set(id, { file, label: String(d.questions?.[0]?.question ?? "").slice(0, 200) });
    if (pane) {
      fs.mkdirSync(qdir, { recursive: true });
      fs.mkdirSync(adir, { recursive: true });
      fs.writeFileSync(path.join(qdir, file),
        JSON.stringify({ toolCallId: id, pane, pid: process.pid, questions: d.questions }), { mode: 0o600 });
    }
    syncTimer();
  });

  pi.events.on("rpiv:ask-user:blocked", (d: any) => {
    const id = d?.toolCallId;
    const label = (id && open.get(id)?.label) || "ask-user";
    if (!d?.active && id) { forget(id); syncTimer(); }
    pi.events.emit("herdr:blocked", { active: !!d?.active, label });
  });

  pi.on("session_shutdown", () => {
    for (const id of [...open.keys()]) forget(id);
    syncTimer();
  });
}
