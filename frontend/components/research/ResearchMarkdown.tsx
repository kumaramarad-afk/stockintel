"use client";

import type { ReactNode } from "react";

function inlineMarkdown(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const token = match[0];
    if (token.startsWith("**")) {
      nodes.push(<strong key={key++}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("*")) {
      nodes.push(<em key={key++}>{token.slice(1, -1)}</em>);
    } else if (token.startsWith("`")) {
      nodes.push(
        <code key={key++} className="rounded bg-slate-100 px-1 text-[0.9em] text-slate-800">
          {token.slice(1, -1)}
        </code>,
      );
    } else {
      const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (link) {
        nodes.push(
          <a key={key++} href={link[2]} className="text-emerald-700 underline underline-offset-2" target="_blank" rel="noreferrer">
            {link[1]}
          </a>,
        );
      }
    }
    last = match.index + token.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function isTableRow(line: string) {
  return line.trim().startsWith("|") && line.trim().endsWith("|");
}

function isTableDivider(line: string) {
  return /^\|[\s:-]+\|/.test(line.trim());
}

function parseRow(line: string) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

export function ResearchMarkdown({ markdown }: { markdown: string }) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i += 1;
      continue;
    }
    if (line.trim() === "---") {
      blocks.push(<hr key={key++} className="my-8 border-slate-200" />);
      i += 1;
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push(
        <h1 key={key++} className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
          {inlineMarkdown(line.slice(2))}
        </h1>,
      );
      i += 1;
      continue;
    }
    if (line.startsWith("### ")) {
      blocks.push(
        <h3 key={key++} className="mt-2 text-lg font-medium text-slate-600">
          {inlineMarkdown(line.slice(4))}
        </h3>,
      );
      i += 1;
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push(
        <h2 key={key++} className="mt-10 text-xl font-semibold text-emerald-900">
          {inlineMarkdown(line.slice(3))}
        </h2>,
      );
      i += 1;
      continue;
    }
    if (isTableRow(line) && i + 1 < lines.length && isTableDivider(lines[i + 1])) {
      const header = parseRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && isTableRow(lines[i]) && !isTableDivider(lines[i])) {
        rows.push(parseRow(lines[i]));
        i += 1;
      }
      blocks.push(
        <div key={key++} className="my-5 overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                {header.map((cell, idx) => (
                  <th key={idx} className="px-3 py-2 font-semibold">
                    {inlineMarkdown(cell)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rIdx) => (
                <tr key={rIdx} className="border-t border-slate-100">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-3 py-2 text-slate-800">
                      {inlineMarkdown(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }
    if (/^\d+\.\s+/.test(line.trim())) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i += 1;
      }
      blocks.push(
        <ol key={key++} className="my-4 list-decimal space-y-3 pl-5 text-[15px] leading-7 text-slate-800">
          {items.map((item, idx) => (
            <li key={idx}>{inlineMarkdown(item)}</li>
          ))}
        </ol>,
      );
      continue;
    }
    if (/^[-*]\s+/.test(line.trim())) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
        i += 1;
      }
      blocks.push(
        <ul key={key++} className="my-4 list-disc space-y-3 pl-5 text-[15px] leading-7 text-slate-800">
          {items.map((item, idx) => (
            <li key={idx}>{inlineMarkdown(item)}</li>
          ))}
        </ul>,
      );
      continue;
    }
    if (line.trim().startsWith("*") && line.trim().endsWith("*") && !line.trim().startsWith("**")) {
      blocks.push(
        <p key={key++} className="my-3 text-sm italic leading-6 text-slate-500">
          {inlineMarkdown(line.trim().replace(/^\*/, "").replace(/\*$/, ""))}
        </p>,
      );
      i += 1;
      continue;
    }
    const para: string[] = [line];
    i += 1;
    while (i < lines.length && lines[i].trim() && !lines[i].startsWith("#") && lines[i].trim() !== "---" && !/^[-*]\s+/.test(lines[i].trim()) && !/^\d+\.\s+/.test(lines[i].trim()) && !isTableRow(lines[i])) {
      para.push(lines[i]);
      i += 1;
    }
    const text = para.join(" ").trim();
    const isFooter = text.toLowerCase().includes("educational and informational purposes only");
    blocks.push(
      <p key={key++} className={isFooter ? "mt-8 text-xs leading-5 text-slate-400" : "my-3 text-[15px] leading-7 text-slate-800"}>
        {inlineMarkdown(text)}
      </p>,
    );
  }

  return <article className="mx-auto max-w-[42rem]">{blocks}</article>;
}
