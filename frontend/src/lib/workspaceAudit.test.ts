import { describe, expect, it } from "vitest";

import { getWorkspaceAuditEventKey } from "./workspaceAudit";

describe("getWorkspaceAuditEventKey", () => {
  it("builds a stable key from the event payload", () => {
    const event = {
      timestamp: "2026-07-14T20:00:00Z",
      action: "update_flags",
      feature_id: "automation_builder",
      updated_by: "persona-123",
      changes: { automation_builder: true },
      before: { automation_builder: false },
      after: { automation_builder: true },
    };

    expect(getWorkspaceAuditEventKey(event)).toBe(
      "2026-07-14T20:00:00Z|update_flags|automation_builder|persona-123|{\"automation_builder\":true}|{\"automation_builder\":false}|{\"automation_builder\":true}",
    );
  });
});
