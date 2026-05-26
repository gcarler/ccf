"use client";

/**
 * Simple formula engine for AirTable cells.
 * Supports: SUM, AVG, COUNT, MIN, MAX, CONCAT, IF, TODAY, NOW, LEN, UPPER, LOWER, ROUND
 * Cell references: {columnName}
 */

export function evaluateFormula(
  formula: string,
  row: Record<string, any>,
  allRows: Record<string, any>[] = []
): any {
  if (!formula || !formula.startsWith("=")) return formula;

  const expr = formula.substring(1).trim();

  try {
    // Replace cell references with values
    let processed = expr;

    // Replace {columnName} with actual values
    processed = processed.replace(/\{([^}]+)\}/g, (_match, colName) => {
      const val = row[colName];
      if (val === undefined || val === null) return "0";
      return typeof val === "string" ? `"${val}"` : String(val);
    });

    // Handle functions
    processed = processed.replace(/SUM\(([^)]+)\)/g, (_, args) => {
      const nums = args.split(",").map((a: string) => parseFloat(a.trim()) || 0);
      return String(nums.reduce((a: number, b: number) => a + b, 0));
    });

    processed = processed.replace(/AVG\(([^)]+)\)/g, (_, args) => {
      const nums = args.split(",").map((a: string) => parseFloat(a.trim()) || 0);
      return String(nums.length ? nums.reduce((a: number, b: number) => a + b, 0) / nums.length : 0);
    });

    processed = processed.replace(/COUNT\(([^)]+)\)/g, (_, args) => {
      return String(args.split(",").filter((a: string) => a.trim() !== "0" && a.trim() !== '""').length);
    });

    processed = processed.replace(/MIN\(([^)]+)\)/g, (_, args) => {
      const nums = args.split(",").map((a: string) => parseFloat(a.trim()) || 0);
      return String(Math.min(...nums));
    });

    processed = processed.replace(/MAX\(([^)]+)\)/g, (_, args) => {
      const nums = args.split(",").map((a: string) => parseFloat(a.trim()) || 0);
      return String(Math.max(...nums));
    });

    processed = processed.replace(/CONCAT\(([^)]+)\)/g, (_, args) => {
      return `"${args.split(",").map((a: string) => a.trim().replace(/"/g, "")).join("")}"`;
    });

    processed = processed.replace(/LEN\(([^)]+)\)/g, (_, arg) => {
      return String(arg.trim().replace(/"/g, "").length);
    });

    processed = processed.replace(/UPPER\(([^)]+)\)/g, (_, arg) => {
      return `"${arg.trim().replace(/"/g, "").toUpperCase()}"`;
    });

    processed = processed.replace(/LOWER\(([^)]+)\)/g, (_, arg) => {
      return `"${arg.trim().replace(/"/g, "").toLowerCase()}"`;
    });

    processed = processed.replace(/ROUND\(([^,]+),\s*([^)]+)\)/g, (_, num, decimals) => {
      return String(parseFloat(num).toFixed(parseInt(decimals)));
    });

    processed = processed.replace(/IF\(([^,]+),\s*([^,]+),\s*([^)]+)\)/g, (_, cond, trueVal, falseVal) => {
      const c = cond.trim();
      const t = trueVal.trim().replace(/"/g, "");
      const f = falseVal.trim().replace(/"/g, "");
      // Simple eval for conditions
      try {
        return eval(c) ? `"${t}"` : `"${f}"`;
      } catch {
        return `"${f}"`;
      }
    });

    processed = processed.replace(/TODAY\(\)/g, () => `"${new Date().toISOString().split("T")[0]}"`);
    processed = processed.replace(/NOW\(\)/g, () => `"${new Date().toISOString()}"`);

    // Clean up and evaluate simple math
    processed = processed.replace(/"/g, "");

    // Try to evaluate as number
    if (/^[\d\s+\-*/().]+$/.test(processed)) {
      try {
        return eval(processed);
      } catch {
        return processed;
      }
    }

    return processed;
  } catch {
    return expr;
  }
}
