const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const componentPath = path.join(
  __dirname,
  "../components/patients/ReviewerAssignmentControl.tsx",
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

test("reviewer assignment control gates rendering to latest pending review snapshot", () => {
  const { canRenderReviewerAssignmentControl } = component;

  assert.equal(
    canRenderReviewerAssignmentControl({
      latestSnapshotId: "snapshot-1",
      reviewStatus: "pending_review",
      snapshotId: "snapshot-1",
    }),
    true,
  );

  [
    { latestSnapshotId: "snapshot-1", reviewStatus: "approved", snapshotId: "snapshot-1" },
    { latestSnapshotId: "snapshot-1", reviewStatus: "rejected", snapshotId: "snapshot-1" },
    { latestSnapshotId: "snapshot-2", reviewStatus: "pending_review", snapshotId: "snapshot-1" },
    { latestSnapshotId: null, reviewStatus: "pending_review", snapshotId: "snapshot-1" },
  ].forEach((entry) => {
    assert.equal(canRenderReviewerAssignmentControl(entry), false);
  });
});

test("patient detail wires assignment only into the review packet backlog", () => {
  const pagePath = path.join(__dirname, "../app/patients/[id]/page.tsx");
  const pageSource = fs.readFileSync(pagePath, "utf8");
  const start = pageSource.indexOf("const renderPatientBacklogPanel");
  const end = pageSource.indexOf("export default async function PatientDetailPage");
  assert.notEqual(start, -1);
  assert.notEqual(end, -1);
  const backlogRenderer = pageSource.slice(start, end);

  assert.match(pageSource, /import ReviewerAssignmentControl/);
  assert.match(backlogRenderer, /<ReviewerAssignmentControl/);
  assert.match(backlogRenderer, /latestSnapshotId=\{latestSnapshotId\}/);
  assert.match(backlogRenderer, /reviewStatus=\{snapshot\.review_status\}/);
  assert.match(backlogRenderer, /snapshotId=\{snapshot\.id\}/);
  assert.match(backlogRenderer, /<ReviewerRejectionControl/);
  assert.match(backlogRenderer, /Read-only for this snapshot\./);

  const auditReadinessPath = path.join(__dirname, "../app/audit-readiness/page.tsx");
  const auditReadinessSource = fs.readFileSync(auditReadinessPath, "utf8");
  assert.doesNotMatch(auditReadinessSource, /ReviewerAssignmentControl/);
  assert.doesNotMatch(auditReadinessSource, /Assign reviewer/);
  assert.doesNotMatch(auditReadinessSource, /\/assignment/);
});

test("reviewer assignment control posts the backend assignment field name and success copy", () => {
  const source = fs.readFileSync(componentPath, "utf8");

  assert.match(source, /assigned_reviewer_user_id: trimmedReviewerUserId/);
  assert.match(source, /Reviewer assigned\./);
  assert.match(source, /Review packet snapshot assignment failed\./);
});
