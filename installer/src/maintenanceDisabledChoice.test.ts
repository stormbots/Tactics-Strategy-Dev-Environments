import { expect, it } from "../testing/unitApi";
import {
  disabledChoiceKey,
  readDisabledChoice,
  saveDisabledChoice,
  type ChoiceContext,
} from "./maintenanceDisabledChoice";
import type { Schedule } from "./model";
const now = Date.parse("2026-11-18T20:00:00Z");
const context: ChoiceContext = {
  machineId: "c".repeat(64),
  identifier: "skyview-student-dev-update.timer",
  definitionId: "a".repeat(64),
};
const record = (changes: Partial<Schedule> = {}): Schedule => ({
  status: "disabled",
  active: false,
  identifier: context.identifier,
  inspectionScope: "schedule",
  inspectionReason: "verified",
  frequency: "Weekly",
  nextRun: null,
  lastRun: null,
  lastResult: "failure",
  resultDetail: "Earlier failure",
  catchUp: true,
  logFolder: "/logs",
  logsAvailable: false,
  note: "",
  observedAt: new Date(now - 1000).toISOString(),
  createdAt: null,
  lastSuccess: null,
  ...changes,
});
function storage() {
  const data = new Map<string, string>();
  return {
    data,
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => {
      data.set(key, value);
    },
  };
}

it("opening a disabled finding reads without saving or changing observations", async () => {
  const store = storage(),
    r = record(),
    before = JSON.stringify(r);
  expect(await readDisabledChoice(context, r, store, now)).toBe(false);
  expect(store.data.size).toBe(0);
  expect(JSON.stringify(r)).toBe(before);
});
it("an explicit saved choice is local display data and keeps Disabled and history intact", async () => {
  const store = storage(),
    r = record(),
    before = JSON.stringify(r);
  expect(await saveDisabledChoice(context, r, store, now)).toEqual({
    saved: true,
  });
  expect(await readDisabledChoice(context, r, store, now)).toBe(true);
  expect(JSON.stringify(r)).toBe(before);
  const raw = store.getItem(disabledChoiceKey)!;
  expect(raw).not.toContain(context.machineId);
  expect(Object.keys(JSON.parse(raw)).sort()).toEqual([
    "chosenAt",
    "context",
    "decision",
    "observedAt",
    "schema",
  ]);
});
it("choices do not apply to another device, schedule or definition", async () => {
  const store = storage();
  await saveDisabledChoice(context, record(), store, now);
  for (const changes of [
    { machineId: "d".repeat(64) },
    { definitionId: "b".repeat(64) },
    { identifier: "\\Skyview Robotics - Dev Tool Updates" },
  ]) {
    const next = { ...context, ...changes };
    expect(
      await readDisabledChoice(
        next,
        record({ identifier: next.identifier }),
        store,
        now,
      ),
    ).toBe(false);
  }
});
it("unreadable, missing, enabled and history-only evidence cannot settle a decision", async () => {
  const store = storage();
  await saveDisabledChoice(context, record(), store, now);
  for (const changes of [
    { status: "enabled" as const },
    { status: "missing" as const },
    { status: "unavailable" as const },
    { inspectionScope: "history" as const },
    { inspectionReason: "accessDenied" as const },
    { inspectionReason: undefined },
  ]) {
    expect(await readDisabledChoice(context, record(changes), store, now)).toBe(
      false,
    );
    expect(
      (await saveDisabledChoice(context, record(changes), store, now)).saved,
    ).toBe(false);
  }
});
it("stale or future observations cannot save or apply a choice", async () => {
  const store = storage();
  for (const time of [now - 300_001, now + 1]) {
    const r = record({ observedAt: new Date(time).toISOString() });
    expect((await saveDisabledChoice(context, r, store, now)).saved).toBe(
      false,
    );
    expect(await readDisabledChoice(context, r, store, now)).toBe(false);
  }
  expect(store.data.size).toBe(0);
});
it("malformed, oversized or future records cannot manufacture a saved decision", async () => {
  const store = storage();
  await saveDisabledChoice(context, record(), store, now);
  const valid = JSON.parse(store.getItem(disabledChoiceKey)!);
  for (const raw of [
    "{bad",
    "x".repeat(1025),
    JSON.stringify({ ...valid, schema: true }),
    JSON.stringify({ ...valid, decision: "enable" }),
    JSON.stringify({ ...valid, context: [valid.context] }),
    JSON.stringify({ ...valid, nativePermit: true }),
    JSON.stringify({ ...valid, chosenAt: new Date(now + 1).toISOString() }),
  ]) {
    store.setItem(disabledChoiceKey, raw);
    expect(await readDisabledChoice(context, record(), store, now)).toBe(false);
  }
});
it("storage or readback failures stay unsaved and do not become successful choices", async () => {
  for (const store of [
    {
      getItem: () => null,
      setItem: () => {
        throw new Error("quota");
      },
    },
    { getItem: () => null, setItem: () => {} },
  ]) {
    const result = await saveDisabledChoice(context, record(), store, now);
    expect(result.saved).toBe(false);
    expect(result.error).toContain("has not been changed");
    expect(await readDisabledChoice(context, record(), store, now)).toBe(false);
  }
});
it("missing identity and unsupported targets leave the choice unsettled", async () => {
  for (const changes of [
    { machineId: "Unavailable" },
    { machineId: "bad\nname" },
    { definitionId: "" },
    { definitionId: "../other" },
    { identifier: "arbitrary timer" },
  ]) {
    const c = { ...context, ...changes },
      store = storage(),
      r = record({ identifier: c.identifier });
    expect((await saveDisabledChoice(c, r, store, now)).saved).toBe(false);
    expect(store.data.size).toBe(0);
  }
});
