import { benchmarks, type Suite } from "@/lib/data";
import { TableWrap } from "@/components/TableWrap";

/** Charter 5.5 and 7.3: what a table must carry before a figure on it can be checked. */
export function Provenance({ suite }: { suite: Suite }) {
  const { results, dataset } = suite;
  const rows: [string, string][] = [
    ["Dataset", dataset.present ? `${suite.builtFrom} v${dataset.version ?? "not set"}` : `${suite.builtFrom} — not a dataset`],
    ["Dataset seed", dataset.seed === undefined || dataset.seed === null ? "not applicable" : String(dataset.seed)],
    ["Dataset version in the results", results.datasetVersion ?? "not run"],
    ["Harness version", results.harnessVersion ?? benchmarks.harness.version ?? "not set"],
    ["Harness commit", results.harnessCommit ?? "not run"],
    ["Scorer version", results.scorerVersion ?? "not run"],
    ["Charter version", benchmarks.charter.version ?? "not set"],
    ["Ground-truth hash", results.groundTruthSha ?? dataset.groundTruthSha ?? "not published for this suite"],
    ["Dataset manifest hash", results.datasetManifestSha ?? "not published for this suite"],
    ["Results folder", results.dir ?? "does not exist — the suite has not been run"],
    ["Run date", results.runDate ?? "not run"],
    ["Price list date", "not run — no provider charge has been incurred"],
  ];
  return (
    <TableWrap label={`Versions and hashes for ${suite.name}`}>
      <table className="table table-dense">
        <caption>
          Charter 5.5: a figure that cannot be reproduced from the items below is withdrawn rather than defended.
        </caption>
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <th scope="row" style={{ fontWeight: 400, width: "40%" }}>
                {k}
              </th>
              <td className={v.startsWith("not ") || v.startsWith("does not") ? "not-run" : undefined}>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

export function PromptHashes({ hashes }: { hashes: Record<string, string> | null | undefined }) {
  if (!hashes) return null;
  const entries = Object.entries(hashes);
  if (entries.length === 0) return null;
  return (
    <TableWrap label="Prompt hashes">
      <table className="table table-dense">
        <caption>
          Charter 5.1: every prompt is published in full and hashed into every report that used it. There is no private
          prompt.
        </caption>
        <thead>
          <tr>
            <th scope="col">Prompt</th>
            <th scope="col">Hash</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([k, v]) => (
            <tr key={k}>
              <th scope="row" style={{ fontWeight: 400 }}>
                {k}
              </th>
              <td>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}
