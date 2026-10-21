// examples/herdr-ask-user-bridge.ts  (copy to ~/.pi/agent/extensions/)
// Bridges rpiv-ask-user-question events to the Herdr pi integration, so a pane
// waiting for an ask-user answer shows as "blocked" in Herdr.
// Kept separate from herdr-agent-state.ts, which `herdr integration install pi` overwrites.
export default function (pi: any) {
  const labels = new Map<string, string>();

  pi.events.on("rpiv:ask-user:prompt", (d: any) => {
    if (d?.toolCallId) labels.set(d.toolCallId, String(d.questions?.[0]?.question ?? "").slice(0, 200));
  });

  pi.events.on("rpiv:ask-user:blocked", (d: any) => {
    const id = d?.toolCallId;
    const label = (id && labels.get(id)) || "ask-user";
    if (!d?.active && id) labels.delete(id);
    pi.events.emit("herdr:blocked", { active: !!d?.active, label });
  });
}
