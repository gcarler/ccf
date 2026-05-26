"use client";

/**
 * Simple formula engine for AirTable cells.
 * Supports: SUM, AVG, COUNT, MIN, MAX, CONCAT, IF, TODAY, NOW, LEN, UPPER, LOWER, ROUND
 * Cell references: {columnName}
 *
 * Safe math: uses a tiny recursive-descent parser instead of eval().
 * Only supports +, -, *, /, parentheses, and numbers.
 */

/* ── safe expression evaluator (no eval) ───────────────────── */

type Token = { type: "num"; value: number } | { type: "op"; value: string } | { type: "lparen" } | { type: "rparen" };

function tokenize(expr: string): Token[] {
  const tokens: Token[] = [];
  const re = /\s*(\d+\.?\d*|[+\-*/()])\s*/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(expr)) !== null) {
    const raw = match[1];
    if (/^\d/.test(raw)) {
      tokens.push({ type: "num", value: parseFloat(raw) });
    } else if (raw === "(") {
      tokens.push({ type: "lparen" });
    } else if (raw === ")") {
      tokens.push({ type: "rparen" });
    } else {
      tokens.push({ type: "op", value: raw });
    }
  }
  return tokens;
}

class ParseError extends Error {}

function parseAddSub(tokens: Token[], pos: { i: number }): number {
  let left = parseMulDiv(tokens, pos);
  while (pos.i < tokens.length) {
    const t = tokens[pos.i];
    if (t.type === "op" && (t.value === "+" || t.value === "-")) {
      pos.i++;
      const right = parseMulDiv(tokens, pos);
      left = t.value === "+" ? left + right : left - right;
    } else break;
  }
  return left;
}

function parseMulDiv(tokens: Token[], pos: { i: number }): number {
  let left = parseAtom(tokens, pos);
  while (pos.i < tokens.length) {
    const t = tokens[pos.i];
    if (t.type === "op" && (t.value === "*" || t.value === "/")) {
      pos.i++;
      const right = parseAtom(tokens, pos);
      left = t.value === "*" ? left * right : left / right;
    } else break;
  }
  return left;
}

function parseAtom(tokens: Token[], pos: { i: number }): number {
  if (pos.i >= tokens.length) throw new ParseError("Unexpected end of expression");
  const t = tokens[pos.i];
  if (t.type === "num") {
    pos.i++;
    return t.value;
  }
  if (t.type === "lparen") {
    pos.i++;
    const val = parseAddSub(tokens, pos);
    if (pos.i >= tokens.length || tokens[pos.i].type !== "rparen") throw new ParseError("Missing closing parenthesis");
    pos.i++;
    return val;
  }
  if (t.type === "op" && t.value === "-") {
    // Unary minus
    pos.i++;
    return -parseAtom(tokens, pos);
  }
  throw new ParseError(`Unexpected token`);
}

function safeEval(mathExpr: string): number {
  const tokens = tokenize(mathExpr);
  if (tokens.length === 0) return NaN;
  const pos = { i: 0 };
  const result = parseAddSub(tokens, pos);
  if (pos.i < tokens.length) throw new ParseError("Unexpected tokens after expression");
  return result;
}

/* ── safe conditional evaluator (no eval) ─────────────────── */

function evaluateCondition(cond: string): boolean {
  // Supported operators: ==, !=, <, >, <=, >=
  const match = cond.match(/^([\d.]+)\s*(==|!=|<=|>=|<|>)\s*([\d.]+)$/);
  if (match) {
    const a = parseFloat(match[1]);
    const op = match[2];
    const b = parseFloat(match[3]);
    switch (op) {
      case "==": return a === b;
      case "!=": return a !== b;
      case "<":  return a < b;
      case ">":  return a > b;
      case "<=": return a <= b;
      case ">=": return a >= b;
    }
  }
  // String equality
  const strMatch = cond.match(/^"([^"]*)"\s*(==|!=)\s*"([^"]*)"$/);
  if (strMatch) {
    return strMatch[2] === "==" ? strMatch[1] === strMatch[3] : strMatch[1] !== strMatch[3];
  }
  // Truthiness: "true", non-zero number
  const trimmed = cond.trim();
  if (/^\d+$/.test(trimmed)) return parseFloat(trimmed) !== 0;
  return trimmed === "true";
}

/* ── main formula engine ──────────────────────────────────── */

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
      try {
        return evaluateCondition(c) ? `"${t}"` : `"${f}"`;
      } catch {
        return `"${f}"`;
      }
    });

    processed = processed.replace(/TODAY\(\)/g, () => `"${new Date().toISOString().split("T")[0]}"`);
    processed = processed.replace(/NOW\(\)/g, () => `"${new Date().toISOString()}"`);

    // Clean up quotes for math evaluation
    const clean = processed.replace(/"/g, "");

    // Evaluate as math expression (safe, no eval)
    if (/^[\d\s+\-*/().]+$/.test(clean)) {
      try {
        return safeEval(clean);
      } catch {
        return clean;
      }
    }

    return clean;
  } catch {
    return expr;
  }
}
