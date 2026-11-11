// frontend/src/lib/powerbiExport.ts

export interface PowerBiKPISpec {
  id: string;
  title: string;
  value: string;
  formula_dax: string;
  rationale: string;
}

export interface PowerBiVisualSpec {
  id: string;
  title: string;
  chart_type: string;
  x_axis: string;
  y_axis: string;
}

export interface PowerBiDashboardPlan {
  title: string;
  dataset_name: string;
  kpis: PowerBiKPISpec[];
  visuals: PowerBiVisualSpec[];
  dax_script: string;
  powerquery_m: string;
}

interface ZipInputEntry {
  name: string;
  data: string | Uint8Array;
}

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) {
      c = (c & 1) !== 0 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[i] = c >>> 0;
  }
  return table;
})();

function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) {
    crc = (crc >>> 8) ^ CRC_TABLE[(crc ^ bytes[i]) & 0xff];
  }
  return (crc ^ 0xffffffff) >>> 0;
}

export function buildZipArchive(entries: ZipInputEntry[]): Uint8Array {
  const encoder = new TextEncoder();
  const now = new Date();
  const dosTime =
    ((now.getHours() & 0x1f) << 11) |
    ((now.getMinutes() & 0x3f) << 5) |
    ((now.getSeconds() >> 1) & 0x1f);
  const dosDate =
    (((Math.max(1980, now.getFullYear()) - 1980) & 0x7f) << 9) |
    (((now.getMonth() + 1) & 0x0f) << 5) |
    (now.getDate() & 0x1f);

  const prepared = entries.map((entry) => {
    const nameBytes = encoder.encode(entry.name);
    const dataBytes =
      typeof entry.data === "string" ? encoder.encode(entry.data) : entry.data;
    return {
      nameBytes,
      dataBytes,
      crc: crc32(dataBytes),
      offset: 0,
    };
  });

  let localTotalSize = 0;
  let centralDirSize = 0;
  for (const item of prepared) {
    item.offset = localTotalSize;
    localTotalSize += 30 + item.nameBytes.length + item.dataBytes.length;
    centralDirSize += 46 + item.nameBytes.length;
  }

  const totalSize = localTotalSize + centralDirSize + 22;
  const output = new Uint8Array(totalSize);
  const view = new DataView(output.buffer);

  let cursor = 0;
  for (const item of prepared) {
    // Local file header (30 bytes + filename)
    view.setUint32(cursor, 0x04034b50, true);
    view.setUint16(cursor + 4, 20, true); // version needed: 2.0
    view.setUint16(cursor + 6, 0x0800, true); // UTF-8 filename flag
    view.setUint16(cursor + 8, 0, true); // compression method: STORE
    view.setUint16(cursor + 10, dosTime, true);
    view.setUint16(cursor + 12, dosDate, true);
    view.setUint32(cursor + 14, item.crc, true);
    view.setUint32(cursor + 18, item.dataBytes.length, true);
    view.setUint32(cursor + 22, item.dataBytes.length, true);
    view.setUint16(cursor + 26, item.nameBytes.length, true);
    view.setUint16(cursor + 28, 0, true); // extra length
    output.set(item.nameBytes, cursor + 30);
    cursor += 30 + item.nameBytes.length;

    output.set(item.dataBytes, cursor);
    cursor += item.dataBytes.length;
  }

  const centralDirOffset = cursor;
  for (const item of prepared) {
    // Central directory header (46 bytes + filename)
    view.setUint32(cursor, 0x02014b50, true);
    view.setUint16(cursor + 4, 20, true); // version made by
    view.setUint16(cursor + 6, 20, true); // version needed
    view.setUint16(cursor + 8, 0x0800, true); // UTF-8 filename flag
    view.setUint16(cursor + 10, 0, true); // STORE
    view.setUint16(cursor + 12, dosTime, true);
    view.setUint16(cursor + 14, dosDate, true);
    view.setUint32(cursor + 16, item.crc, true);
    view.setUint32(cursor + 20, item.dataBytes.length, true);
    view.setUint32(cursor + 24, item.dataBytes.length, true);
    view.setUint16(cursor + 28, item.nameBytes.length, true);
    view.setUint16(cursor + 30, 0, true); // extra length
    view.setUint16(cursor + 32, 0, true); // comment length
    view.setUint16(cursor + 34, 0, true); // disk number start
    view.setUint16(cursor + 36, 0, true); // internal attrs
    view.setUint32(cursor + 38, 0, true); // external attrs
    view.setUint32(cursor + 42, item.offset, true); // local header offset
    output.set(item.nameBytes, cursor + 46);
    cursor += 46 + item.nameBytes.length;
  }

  // End of central directory record (22 bytes)
  view.setUint32(cursor, 0x06054b50, true);
  view.setUint16(cursor + 4, 0, true); // disk number
  view.setUint16(cursor + 6, 0, true); // start disk
  view.setUint16(cursor + 8, prepared.length, true);
  view.setUint16(cursor + 10, prepared.length, true);
  view.setUint32(cursor + 12, centralDirSize, true);
  view.setUint32(cursor + 16, centralDirOffset, true);
  view.setUint16(cursor + 20, 0, true); // comment length

  return output;
}

export function stripDatasetExtension(datasetName?: string): string {
  if (!datasetName) return "";
  return datasetName.trim().replace(/\.(csv|tsv|txt)$/i, "");
}

export function sanitizePowerBiFilenameBase(
  datasetName?: string,
  fallback = "Vectronyx_Dashboard"
): string {
  const stem = stripDatasetExtension(datasetName);
  const sanitized = stem.replace(/[^A-Za-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
  return sanitized || fallback;
}

function extractDaxExpression(formula: string): string {
  const text = (formula || "").trim();
  if (!text) return "0";
  const nonCommentLines = text
    .split(/\r?\n/)
    .filter((line) => !/^\s*(--|\/\/)/.test(line));
  const cleaned = nonCommentLines.join("\n").trim() || text;
  const eqIdx = cleaned.indexOf("=");
  if (eqIdx > 0) {
    const lhs = cleaned.slice(0, eqIdx).trim();
    const rhs = cleaned.slice(eqIdx + 1).trim();
    if (lhs && rhs) return rhs;
  }
  return cleaned;
}

function parseCsvRow(line: string, delimiter: string): string[] {
  const cells: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === delimiter && !inQuotes) {
      cells.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  cells.push(current.trim());
  return cells;
}

function inferCsvColumnsAndTypes(
  csvContent: string
): Array<{ name: string; dataType: string; sourceColumn: string }> {
  const cleaned = (csvContent || "").replace(/^\uFEFF/, "");
  const lines = cleaned.split(/\r?\n/).filter((l) => l.trim() !== "");
  if (lines.length === 0) return [];

  const headerLine = lines[0];
  const delimiter = headerLine.includes("\t") && !headerLine.includes(",") ? "\t" : ",";
  const headers = parseCsvRow(headerLine, delimiter);
  const sampleRows = lines.slice(1, 51).map((line) => parseCsvRow(line, delimiter));

  const seen = new Map<string, number>();
  return headers.map((rawName, idx) => {
    const baseName = rawName || `Column_${idx + 1}`;
    const count = seen.get(baseName) || 0;
    seen.set(baseName, count + 1);
    const colName = count > 0 ? `${baseName}_${count + 1}` : baseName;

    const values = sampleRows
      .map((r) => (idx < r.length ? r[idx].trim() : ""))
      .filter((v) => v !== "");

    let dataType = "string";
    if (values.length > 0) {
      const allInt = values.every((v) => /^(0|-?[1-9]\d*)$/.test(v));
      const allFloat = values.every((v) =>
        /^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?$/.test(v)
      );
      if (allInt) dataType = "int64";
      else if (allFloat) dataType = "double";
    }

    return {
      name: colName,
      dataType,
      sourceColumn: colName,
    };
  });
}

function mapVisualType(chartType: string): string {
  switch ((chartType || "").toLowerCase()) {
    case "line":
      return "lineChart";
    case "area":
      return "areaChart";
    case "pie":
      return "donutChart";
    case "scatter":
      return "scatterChart";
    default:
      return "clusteredColumnChart";
  }
}

export function generatePowerBiPbipZipBlob(
  plan: PowerBiDashboardPlan,
  csvContent: string
): Blob {
  const filenameBase = sanitizePowerBiFilenameBase(plan.dataset_name);

  const pbipMeta = {
    version: "1.0",
    artifacts: [{ report: { path: `${filenameBase}.Report` } }],
    settings: { enableAutoRecovery: true },
  };

  const pbirMeta = {
    version: "1.0",
    datasetReference: {
      byPath: { path: `../${filenameBase}.Dataset` },
      byConnection: null,
    },
  };

  const visualContainers: Array<Record<string, unknown>> = [];

  (plan.kpis || []).forEach((kpi, i) => {
    visualContainers.push({
      x: 20 + i * 240,
      y: 20,
      width: 220,
      height: 130,
      config: JSON.stringify({
        name: `kpi_card_${i}`,
        layouts: [
          {
            id: 0,
            position: { x: 20 + i * 240, y: 20, width: 220, height: 130 },
          },
        ],
        singleVisual: {
          visualType: "card",
          projections: { Fields: [{ queryRef: `Dataset.${kpi.title}` }] },
          visualContainerObjects: {
            title: [
              {
                properties: {
                  show: { expr: { Literal: { Value: "true" } } },
                  text: { expr: { Literal: { Value: `'${kpi.title}'` } } },
                },
              },
            ],
          },
        },
      }),
    });
  });

  const chartY = 170;
  (plan.visuals || []).forEach((vis, i) => {
    const colIdx = i % 2;
    const rowIdx = Math.floor(i / 2);
    const vx = 20 + colIdx * 620;
    const vy = chartY + rowIdx * 340;

    visualContainers.push({
      x: vx,
      y: vy,
      width: 600,
      height: 320,
      config: JSON.stringify({
        name: `visual_${vis.id}`,
        singleVisual: {
          visualType: mapVisualType(vis.chart_type),
          projections: {
            Category: [{ queryRef: `Dataset.${vis.x_axis}` }],
            Y: [{ queryRef: `Dataset.${vis.y_axis}` }],
          },
          visualContainerObjects: {
            title: [
              {
                properties: {
                  show: { expr: { Literal: { Value: "true" } } },
                  text: { expr: { Literal: { Value: `'${vis.title}'` } } },
                },
              },
            ],
          },
        },
      }),
    });
  });

  const reportJson = {
    config: JSON.stringify({
      version: "5.50",
      themeCollection: {
        baseTheme: { name: "CY24SU02", version: "5.50", type: 2 },
      },
    }),
    layoutOptimization: 0,
    sections: [
      {
        name: "ReportSection1",
        displayName: plan.title,
        width: 1280,
        height: Math.max(
          720,
          chartY + Math.floor(((plan.visuals?.length || 0) + 1) / 2) * 360 + 50
        ),
        visualContainers,
      },
    ],
  };

  const pbidatasetMeta = {
    version: "1.0",
    settings: {},
  };

  const mCodeContent =
    plan.powerquery_m ||
    `let\n    Source = Csv.Document(File.Contents("dataset.csv"), [Delimiter=",", Encoding=65001]),\n    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])\nin\n    #"Promoted Headers"`;

  const columns = inferCsvColumnsAndTypes(csvContent);
  const measures = (plan.kpis || []).map((kpi) => ({
    name: kpi.title,
    expression: extractDaxExpression(kpi.formula_dax),
    description: kpi.rationale,
  }));

  const modelBim = {
    name: "DatasetModel",
    compatibilityLevel: 1550,
    model: {
      culture: "en-US",
      dataAccessOptions: { legacyRedirectsEnabled: true, fastCombine: true },
      defaultPowerBIDataSourceVersion: "powerBI_V3",
      tables: [
        {
          name: "Dataset",
          description: `Imported table for ${plan.dataset_name}`,
          columns,
          partitions: [
            {
              name: "Dataset",
              mode: "import",
              source: {
                type: "m",
                expression: mCodeContent,
              },
            },
          ],
          measures,
        },
      ],
    },
  };

  let readmeText = `========================================================================
VECTRONYX AI WORKBENCH — POWER BI PROJECT EXPORT (.pbip)
========================================================================
Dashboard: ${plan.title}
Dataset:   ${plan.dataset_name}

HOW TO OPEN:
1. Ensure you have Power BI Desktop (May 2023 or newer) installed.
2. Extract (unzip) this entire package into a folder.
3. Double click on '${filenameBase}.pbip' to open the project in Power BI Desktop.
4. (Optional) To save as a single .pbix file, choose File > Save As > Power BI file (.pbix).

------------------------------------------------------------------------
DAX MEASURES (READY TO COPY & PASTE):
------------------------------------------------------------------------
`;

  for (const kpi of plan.kpis || []) {
    readmeText += `\n-- ${kpi.title} (${kpi.rationale})\n${kpi.formula_dax}\n`;
  }

  if (plan.dax_script) {
    readmeText += `\n-- Consolidated Script:\n${plan.dax_script}\n`;
  }

  readmeText += `
------------------------------------------------------------------------
POWER QUERY (M) ETL TRANSFORMATION:
------------------------------------------------------------------------
${mCodeContent}
`;

  const zipBytes = buildZipArchive([
    { name: `${filenameBase}.pbip`, data: JSON.stringify(pbipMeta, null, 2) },
    {
      name: `${filenameBase}.Report/definition.pbir`,
      data: JSON.stringify(pbirMeta, null, 2),
    },
    {
      name: `${filenameBase}.Report/report.json`,
      data: JSON.stringify(reportJson, null, 2),
    },
    {
      name: `${filenameBase}.Dataset/definition.pbidataset`,
      data: JSON.stringify(pbidatasetMeta, null, 2),
    },
    {
      name: `${filenameBase}.Dataset/model.bim`,
      data: JSON.stringify(modelBim, null, 2),
    },
    {
      name: `${filenameBase}.Dataset/dataset.csv`,
      data: csvContent,
    },
    {
      name: "PowerBI_Setup_Guide.txt",
      data: readmeText,
    },
  ]);

  const bufferCopy = new Uint8Array(zipBytes.byteLength);
  bufferCopy.set(zipBytes);
  return new Blob([bufferCopy.buffer], { type: "application/zip" });
}
