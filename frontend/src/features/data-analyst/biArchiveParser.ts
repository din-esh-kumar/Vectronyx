// frontend/src/features/data-analyst/biArchiveParser.ts
/**
 * Zero-dependency browser parser for Power BI (.pbip ZIP) and Tableau (.twbx / .twb) files.
 * Uses native DataView + DecompressionStream("deflate-raw") + DOMParser.
 */

export interface ZipEntryInfo {
  name: string;
  size: number;
  textContent?: string;
}

export interface ParsedTableauField {
  caption: string;
  formula: string;
  datatype: string;
}

export interface ParsedTableauWorksheet {
  name: string;
  rows: string;
  cols: string;
  markType: string;
}

export interface ParsedBIFile {
  kind: "powerbi" | "tableau";
  fileName: string;
  files: ZipEntryInfo[];
  title: string;
  pages: Array<{ name: string; visualsCount: number; visualTypes: string[] }>;
  worksheets: ParsedTableauWorksheet[];
  calculatedFields: ParsedTableauField[];
  daxMeasures: Array<{ name: string; expression: string }>;
  csvPreview: { headers: string[]; rows: string[][] } | null;
}

async function inflateRaw(compressed: Uint8Array): Promise<Uint8Array> {
  const ds = new DecompressionStream("deflate-raw");
  const writer = ds.writable.getWriter();
  const safeCopy = new Uint8Array(compressed.byteLength);
  safeCopy.set(compressed);
  await writer.write(safeCopy);
  await writer.close();
  const out = await new Response(ds.readable).arrayBuffer();
  return new Uint8Array(out);
}

const TEXT_EXTS = new Set([
  ".twb",
  ".pbip",
  ".json",
  ".bim",
  ".tmdl",
  ".txt",
  ".md",
  ".csv",
  ".xml",
  ".platform",
]);

function isTextFile(name: string): boolean {
  const lower = name.toLowerCase();
  for (const ext of TEXT_EXTS) {
    if (lower.endsWith(ext)) return true;
  }
  return false;
}

async function unzipBuffer(buffer: ArrayBuffer): Promise<ZipEntryInfo[]> {
  const view = new DataView(buffer);
  const bytes = new Uint8Array(buffer);
  const decoder = new TextDecoder("utf-8", { fatal: false });
  const entries: ZipEntryInfo[] = [];

  // Locate End of Central Directory (EOCD) signature 0x06054b50
  let eocdOffset = -1;
  const minOffset = Math.max(0, bytes.length - 65557);
  for (let i = bytes.length - 22; i >= minOffset; i--) {
    if (view.getUint32(i, true) === 0x06054b50) {
      eocdOffset = i;
      break;
    }
  }
  if (eocdOffset === -1) {
    throw new Error("Invalid ZIP archive (missing End of Central Directory).");
  }

  const totalEntries = view.getUint16(eocdOffset + 10, true);
  let cdOffset = view.getUint32(eocdOffset + 16, true);

  for (let i = 0; i < totalEntries && cdOffset + 46 <= bytes.length; i++) {
    if (view.getUint32(cdOffset, true) !== 0x02014b50) break;

    const method = view.getUint16(cdOffset + 10, true);
    const compSize = view.getUint32(cdOffset + 20, true);
    const uncompSize = view.getUint32(cdOffset + 24, true);
    const nameLen = view.getUint16(cdOffset + 28, true);
    const extraLen = view.getUint16(cdOffset + 30, true);
    const commentLen = view.getUint16(cdOffset + 32, true);
    const localHeaderOffset = view.getUint32(cdOffset + 42, true);

    const name = decoder.decode(bytes.subarray(cdOffset + 46, cdOffset + 46 + nameLen));
    cdOffset += 46 + nameLen + extraLen + commentLen;

    if (name.endsWith("/")) continue;

    let textContent: string | undefined;
    if (isTextFile(name) && localHeaderOffset + 30 <= bytes.length) {
      const lNameLen = view.getUint16(localHeaderOffset + 26, true);
      const lExtraLen = view.getUint16(localHeaderOffset + 28, true);
      const dataStart = localHeaderOffset + 30 + lNameLen + lExtraLen;
      const slice = bytes.subarray(dataStart, dataStart + compSize);

      if (method === 0) {
        textContent = decoder.decode(slice);
      } else if (method === 8) {
        try {
          const inflated = await inflateRaw(slice);
          textContent = decoder.decode(inflated);
        } catch {
          // Leave textContent undefined if decompression fails
        }
      }
    }

    entries.push({ name, size: uncompSize, textContent });
  }

  return entries;
}

function parseCsvPreview(csvText: string, maxRows = 12): { headers: string[]; rows: string[][] } | null {
  const lines = csvText
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length === 0) return null;

  const splitLine = (line: string): string[] => {
    const out: string[] = [];
    let cur = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        inQuotes = !inQuotes;
      } else if (ch === "," && !inQuotes) {
        out.push(cur.trim());
        cur = "";
      } else {
        cur += ch;
      }
    }
    out.push(cur.trim());
    return out;
  };

  const headers = splitLine(lines[0]);
  const rows = lines.slice(1, 1 + maxRows).map(splitLine);
  return { headers, rows };
}

function parseTableauXml(xmlText: string): {
  worksheets: ParsedTableauWorksheet[];
  calculatedFields: ParsedTableauField[];
  dashboards: string[];
} {
  const doc = new DOMParser().parseFromString(xmlText, "text/xml");
  const worksheets: ParsedTableauWorksheet[] = [];
  const calculatedFields: ParsedTableauField[] = [];
  const dashboards: string[] = [];

  doc.querySelectorAll("worksheets > worksheet").forEach((ws) => {
    const name = ws.getAttribute("name") || "Sheet";
    const rows = ws.querySelector("table > rows")?.textContent?.trim() || "";
    const cols = ws.querySelector("table > cols")?.textContent?.trim() || "";
    const markEl = ws.querySelector("pane mark");
    const markType = markEl?.getAttribute("class") || "Automatic";
    worksheets.push({ name, rows, cols, markType });
  });

  doc.querySelectorAll("dashboards > dashboard").forEach((db) => {
    const name = db.getAttribute("name");
    if (name) dashboards.push(name);
  });

  const seenCaptions = new Set<string>();
  doc.querySelectorAll("column").forEach((col) => {
    const calc = col.querySelector("calculation");
    if (!calc) return;
    const formula = calc.getAttribute("formula") || "";
    const caption = col.getAttribute("caption") || col.getAttribute("name") || "Calculated Field";
    const datatype = col.getAttribute("datatype") || "real";
    if (formula && !seenCaptions.has(caption)) {
      seenCaptions.add(caption);
      calculatedFields.push({ caption, formula, datatype });
    }
  });

  return { worksheets, calculatedFields, dashboards };
}

function parsePowerBiArchive(files: ZipEntryInfo[], fileName: string): ParsedBIFile {
  const pages: ParsedBIFile["pages"] = [];
  const daxMeasures: ParsedBIFile["daxMeasures"] = [];
  let title = fileName.replace(/\.(zip|pbip)$/i, "");
  let csvPreview: ParsedBIFile["csvPreview"] = null;

  for (const f of files) {
    const lower = f.name.toLowerCase();
    if (lower.endsWith("report.json") && f.textContent) {
      try {
        const rep = JSON.parse(f.textContent);
        const sections = Array.isArray(rep?.sections) ? rep.sections : [];
        for (const sec of sections) {
          const containers = Array.isArray(sec?.visualContainers) ? sec.visualContainers : [];
          const visualTypes: string[] = [];
          for (const vc of containers) {
            try {
              const cfg = typeof vc.config === "string" ? JSON.parse(vc.config) : vc.config;
              const vType = cfg?.singleVisual?.visualType;
              if (vType) visualTypes.push(vType);
            } catch {
              // ignore malformed visual config
            }
          }
          pages.push({
            name: sec?.displayName || sec?.name || `Page ${pages.length + 1}`,
            visualsCount: containers.length,
            visualTypes,
          });
        }
      } catch {
        // ignore invalid JSON
      }
    }

    if (lower.endsWith("model.bim") && f.textContent) {
      try {
        const bim = JSON.parse(f.textContent);
        const tables = Array.isArray(bim?.model?.tables) ? bim.model.tables : [];
        for (const tbl of tables) {
          const measures = Array.isArray(tbl?.measures) ? tbl.measures : [];
          for (const m of measures) {
            const expr = Array.isArray(m.expression) ? m.expression.join("\n") : String(m.expression || "");
            if (m.name) {
              daxMeasures.push({ name: m.name, expression: expr });
            }
          }
        }
      } catch {
        // ignore invalid BIM
      }
    }

    if (lower.endsWith(".csv") && f.textContent && !csvPreview) {
      csvPreview = parseCsvPreview(f.textContent);
    }
  }

  return {
    kind: "powerbi",
    fileName,
    files,
    title,
    pages,
    worksheets: [],
    calculatedFields: [],
    daxMeasures,
    csvPreview,
  };
}

export async function parseBIUploadFile(file: File): Promise<ParsedBIFile> {
  const lower = file.name.toLowerCase();

  // Plain .twb XML file
  if (lower.endsWith(".twb")) {
    const xmlText = await file.text();
    const { worksheets, calculatedFields, dashboards } = parseTableauXml(xmlText);
    return {
      kind: "tableau",
      fileName: file.name,
      files: [{ name: file.name, size: file.size, textContent: xmlText }],
      title: dashboards[0] || file.name.replace(/\.twb$/i, ""),
      pages: dashboards.map((d) => ({ name: d, visualsCount: worksheets.length, visualTypes: [] })),
      worksheets,
      calculatedFields,
      daxMeasures: [],
      csvPreview: null,
    };
  }

  // Plain .pbip JSON descriptor
  if (lower.endsWith(".pbip")) {
    const text = await file.text();
    return {
      kind: "powerbi",
      fileName: file.name,
      files: [{ name: file.name, size: file.size, textContent: text }],
      title: file.name.replace(/\.pbip$/i, ""),
      pages: [],
      worksheets: [],
      calculatedFields: [],
      daxMeasures: [],
      csvPreview: null,
    };
  }

  // ZIP-based .twbx or .pbip.zip
  const buffer = await file.arrayBuffer();
  const files = await unzipBuffer(buffer);

  const twbEntry = files.find((f) => f.name.toLowerCase().endsWith(".twb") && f.textContent);
  if (lower.endsWith(".twbx") || twbEntry) {
    const { worksheets, calculatedFields, dashboards } = twbEntry?.textContent
      ? parseTableauXml(twbEntry.textContent)
      : { worksheets: [], calculatedFields: [], dashboards: [] };
    const csvEntry = files.find((f) => f.name.toLowerCase().endsWith(".csv") && f.textContent);
    return {
      kind: "tableau",
      fileName: file.name,
      files,
      title: dashboards[0] || file.name.replace(/\.twbx$/i, ""),
      pages: dashboards.map((d) => ({ name: d, visualsCount: worksheets.length, visualTypes: [] })),
      worksheets,
      calculatedFields,
      daxMeasures: [],
      csvPreview: csvEntry?.textContent ? parseCsvPreview(csvEntry.textContent) : null,
    };
  }

  return parsePowerBiArchive(files, file.name);
}
