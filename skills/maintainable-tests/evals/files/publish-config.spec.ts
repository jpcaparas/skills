import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

declare function publishConfig(options: {
  backup: boolean;
  destination: string;
  force: boolean;
}): void;

// Regression fixture: old bytes must survive only in an explicitly requested backup.
const previousContents = 'export default { mode: "legacy" };';
const generatedContents = 'export default { mode: "strict" };';
let configPath: string;
let testDirectory: string;

beforeEach(() => {
  testDirectory = mkdtempSync(join(tmpdir(), "publish-config-"));
  configPath = join(testDirectory, "formatter.ts");
  writeFileSync(configPath, previousContents, "utf8");
});

afterEach(() => {
  rmSync(testDirectory, { force: true, recursive: true });
});

it("overwrites the existing formatter configuration after confirmation", () => {
  publishConfig({ backup: false, destination: configPath, force: true });

  expect(existsSync(configPath)).not.toBe(previousContents);
});

it("does not create a backup unless requested", () => {
  publishConfig({ backup: false, destination: configPath, force: true });

  expect(() => readFileSync(join(testDirectory, "formatter.json.backup"), "utf8")).toThrow();
});

it("keeps the previous bytes in the requested backup", () => {
  publishConfig({ backup: true, destination: configPath, force: true });

  expect(readFileSync(`${configPath}.backup`, "utf8")).toBe(previousContents);
});
