import type { Suite } from "@/lib/data";
import { repoPath, REPO_PUBLISHED } from "@/lib/site";

/** The commands, read from the suite's own reproduce file where one exists. */
export function Reproduce({ suite }: { suite: Suite }) {
  const { reproduce } = suite;
  return (
    <div className="stack-3">
      <p className="body">
        {reproduce.present ? (
          <>
            These commands are read at build time from <code>{reproduce.source}</code>. They are the commands that
            produced the files behind this page, and the commands that replace the &quot;not run&quot; rows with a
            measurement.
          </>
        ) : reproduce.commands.length > 0 ? (
          <>
            No <code>reproduce.md</code> exists for this suite, because no run has been made. The commands below are
            read at build time from <code>{reproduce.source}</code>: they rebuild the dataset from its seed and run the
            harness against it.
          </>
        ) : (
          <>
            This suite is not run from a command line. It is a set of scripted exercises run against a live deployment,
            scored against a published rubric by a person. The documents below hold the procedure.
          </>
        )}
      </p>

      {reproduce.commands.map((c, i) => (
        <div key={i}>
          {c.heading ? <p className="code-heading">{c.heading}</p> : null}
          <pre className="code">
            <code>{c.code}</code>
          </pre>
        </div>
      ))}

      {reproduce.documents.length > 0 ? (
        <div>
          <p className="ui" style={{ fontWeight: 500, marginBottom: 12 }}>
            The documents this suite is run from
          </p>
          <ul className="prose-list">
            {reproduce.documents.map((d) => (
              <li key={d.path}>
                <a href={repoPath(d.path)}>{d.title}</a> — <code>{d.path}</code>
                {d.headings.length > 0 ? <span className="note"> · {d.headings.slice(0, 6).join(" · ")}</span> : null}
              </li>
            ))}
          </ul>
          {REPO_PUBLISHED ? null : (
            <p className="note" style={{ marginTop: 12 }}>
              The public repository is not created yet, so those links do not resolve. The paths are the paths inside
              it.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
