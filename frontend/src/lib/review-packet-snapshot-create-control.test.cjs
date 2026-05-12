const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const componentPath = path.join(
  __dirname,
  "../components/patients/ReviewPacketSnapshotCreateControl.tsx",
);

function loadComponentModule() {
  const source = fs.readFileSync(componentPath, "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      esModuleInterop: true,
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
    fileName: componentPath,
  });

  const componentModule = new Module(componentPath, module);
  componentModule.filename = componentPath;
  componentModule.paths = Module._nodeModulePaths(path.dirname(componentPath));
  componentModule.require = (request) => {
    if (request === "next/navigation") {
      return {
        useRouter: () => ({ refresh: () => undefined }),
      };
    }
    return Module.prototype.require.call(componentModule, request);
  };
  componentModule._compile(outputText, componentPath);
  return componentModule.exports;
}

const component = loadComponentModule();

test("review packet snapshot create control appears only for rejected or no-snapshot create-next-step posture", () => {
  const { canRenderReviewPacketSnapshotCreateControl } = component;

  assert.equal(
    canRenderReviewPacketSnapshotCreateControl({
      latestSnapshotId: "snapshot-1",
      nextStepAction: "create_snapshot",
      patientId: "patient-1",
      reviewStatus: "rejected",
    }),
    true,
  );
  assert.equal(
    canRenderReviewPacketSnapshotCreateControl({
      latestSnapshotId: null,
      nextStepAction: "create_snapshot",
      patientId: "patient-1",
      reviewStatus: null,
    }),
    true,
  );

  [
    {
      latestSnapshotId: "snapshot-1",
      nextStepAction: "review_snapshot",
      patientId: "patient-1",
      reviewStatus: "rejected",
    },
    {
      latestSnapshotId: "snapshot-1",
      nextStepAction: "create_snapshot",
      patientId: "patient-1",
      reviewStatus: "pending_review",
    },
    {
      latestSnapshotId: "snapshot-1",
      nextStepAction: "create_snapshot",
      patientId: "patient-1",
      reviewStatus: "approved",
    },
    {
      latestSnapshotId: "snapshot-1",
      nextStepAction: "create_snapshot",
      patientId: "",
      reviewStatus: "rejected",
    },
  ].forEach((entry) => {
    assert.equal(canRenderReviewPacketSnapshotCreateControl(entry), false);
  });
});

test("patient detail wires create-snapshot control only into the review packet backlog", () => {
  const pagePath = path.join(__dirname, "../app/patients/[id]/page.tsx");
  const pageSource = fs.readFileSync(pagePath, "utf8");
  const start = pageSource.indexOf("const renderPatientBacklogPanel");
  const end = pageSource.indexOf("export default async function PatientDetailPage");
  assert.notEqual(start, -1);
  assert.notEqual(end, -1);
  const backlogRenderer = pageSource.slice(start, end);

  assert.match(pageSource, /import ReviewPacketSnapshotCreateControl/);
  assert.match(backlogRenderer, /<ReviewPacketSnapshotCreateControl/);
  assert.match(backlogRenderer, /latestSnapshotId=\{latestSnapshotId\}/);
  assert.match(backlogRenderer, /nextStepAction=\{backlog\.audit_status\.next_step\.action\}/);
  assert.match(backlogRenderer, /patientId=\{backlog\.patient_id\}/);
  assert.match(backlogRenderer, /reviewStatus=\{backlog\.audit_status\.review_status\}/);

  const auditReadinessPath = path.join(__dirname, "../app/audit-readiness/page.tsx");
  const auditReadinessSource = fs.readFileSync(auditReadinessPath, "utf8");
  assert.doesNotMatch(auditReadinessSource, /ReviewPacketSnapshotCreateControl/);
  assert.doesNotMatch(auditReadinessSource, /Create new review packet snapshot/);
});
