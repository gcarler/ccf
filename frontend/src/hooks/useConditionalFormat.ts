"use client";

export type ConditionalFormatRule = {
  columnId: string;
  operator: "eq" | "neq" | "gt" | "lt" | "gte" | "lte" | "contains" | "isEmpty" | "isNotEmpty";
  value: any;
  backgroundColor?: string;
  textColor?: string;
  icon?: string;
};

export function applyConditionalFormat(
  row: Record<string, any>,
  columnId: string,
  rules: ConditionalFormatRule[]
): { backgroundColor?: string; textColor?: string; icon?: string } | null {
  const cellValue = row[columnId];

  for (const rule of rules) {
    if (rule.columnId !== columnId) continue;

    let matches = false;
    switch (rule.operator) {
      case "eq": matches = cellValue === rule.value; break;
      case "neq": matches = cellValue !== rule.value; break;
      case "gt": matches = Number(cellValue) > Number(rule.value); break;
      case "lt": matches = Number(cellValue) < Number(rule.value); break;
      case "gte": matches = Number(cellValue) >= Number(rule.value); break;
      case "lte": matches = Number(cellValue) <= Number(rule.value); break;
      case "contains": matches = String(cellValue || "").toLowerCase().includes(String(rule.value).toLowerCase()); break;
      case "isEmpty": matches = cellValue === null || cellValue === undefined || cellValue === ""; break;
      case "isNotEmpty": matches = cellValue !== null && cellValue !== undefined && cellValue !== ""; break;
    }

    if (matches) {
      return { backgroundColor: rule.backgroundColor, textColor: rule.textColor, icon: rule.icon };
    }
  }
  return null;
}
