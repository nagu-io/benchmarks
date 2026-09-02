import type { Reference } from "@/lib/data";
import { TableWrap } from "@/components/TableWrap";
import { BarChart } from "@/components/BarChart";

const pct = (n: number | null | undefined) => (n === null || n === undefined ? "not run" : (n * 100).toFixed(1));
const num = (n: number | null | undefined, dp = 1) =>
  n === null || n === undefined ? "not run" : n.toLocaleString("en-GB", { minimumFractionDigits: dp, maximumFractionDigits: dp });

/**
 * Exception Economics scores a decision policy over labelled items, so the dataset ships
 * with one of its own. These figures describe that policy and that threshold. They
 * describe no vendor's system, and no row here is a measurement of a model.
 */
export function ReferencePolicy({ reference, dir }: { reference: Reference; dir: string | null }) {
  const thresholds = reference.thresholds;
  const chartThreshold = thresholds[0];

  return (
    <div className="stack-4">
      <div className="banner" style={{ borderLeftColor: "var(--color-red)" }}>
        <p className="banner-title condensed">Not a system result</p>
        <p className="body" style={{ fontSize: 15 }}>
          The figures below come from the dataset&apos;s own {reference.note ?? "reference decision policy"}: a
          synthetic confidence and proposed outcome generated with each item. It is a property of the dataset. It is not
          a measurement of any model, service or vendor, and no figure below should be read as one. The leaderboard
          above is the measurement, and it is empty.
        </p>
        <p className="note">
          Population: {reference.population ?? "not stated"}. Read from <code>{dir}/scores-baseline.json</code>.
        </p>
      </div>

      <div>
        <TableWrap label="Reference decision policy at three confidence thresholds">
          <table className="table">
            <caption>
              Charter 3.14.6: automation rate is never published alone. The wrong-automation figure sits on the same
              row.
            </caption>
            <thead>
              <tr>
                <th scope="col">Confidence threshold</th>
                <th scope="col" className="numeric">
                  Automation rate %
                </th>
                <th scope="col" className="numeric">
                  Wrong automations
                </th>
                <th scope="col" className="numeric">
                  Wrong as % of automated
                </th>
                <th scope="col" className="numeric">
                  Rework min per 1,000 automated
                </th>
                <th scope="col" className="numeric">
                  Open exposure items
                </th>
                <th scope="col" className="numeric">
                  Reviewer min per 1,000 items
                </th>
                <th scope="col" className="numeric">
                  Net cost per item, INR
                </th>
                <th scope="col" className="numeric">
                  Net cost per item, USD
                </th>
              </tr>
            </thead>
            <tbody>
              {thresholds.map((t) => (
                <tr key={String(t.threshold)}>
                  <th scope="row" style={{ fontWeight: 400 }}>
                    {t.threshold === null ? "not run" : t.threshold.toFixed(2)}
                  </th>
                  <td className="numeric">{pct(t.rates?.automation_rate)}</td>
                  <td className="numeric">{t.counts?.automated_wrong?.toLocaleString("en-GB") ?? "not run"}</td>
                  <td className="numeric">{pct(t.rates?.wrong_automation_rate_of_automated)}</td>
                  <td className="numeric">{num(t.rework?.minutesPer1000Automated)}</td>
                  <td className="numeric">{t.rework?.openExposureItems?.toLocaleString("en-GB") ?? "not run"}</td>
                  <td className="numeric">{num(t.reviewer?.per1000ItemsAdmitted)}</td>
                  <td className="numeric">{num(t.cost?.net_cost_per_item_inr, 4)}</td>
                  <td className="numeric">{num(t.cost?.net_cost_per_item_usd, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
        <p className="filter-note">
          Sample size {thresholds[0]?.counts?.items_admitted?.toLocaleString("en-GB") ?? "not stated"} items admitted, at
          every threshold, out of {thresholds[0]?.counts?.items_received?.toLocaleString("en-GB") ?? "not stated"}{" "}
          received. Money is at the placeholder reviewer rates the labour model states:{" "}
          {thresholds[0]?.cost?.rate_status ?? "status not stated"}. They are not market rates and they are not a
          measurement. Machine cost per item is zero because no system has been run, so every net cost figure here is
          labour only.
        </p>
      </div>

      {chartThreshold ? (
        <div>
          <BarChart
            title={`Reference decision policy at threshold ${chartThreshold.threshold?.toFixed(2) ?? ""}: the share of each tier carried without a person`}
            bars={chartThreshold.byTier.map((t) => ({
              label: t.tier,
              automated: t.automationRate,
              note: `${t.admitted?.toLocaleString("en-GB") ?? "?"} admitted · ${t.automatedWrong ?? 0} wrong`,
            }))}
            emptyMessage="Nothing to plot."
          />
          <p className="filter-note">
            A property of the dataset, not a measurement of a system. The yellow fill is the share the policy carried
            with no person; the red mark under the remainder is the share that reached a reviewer. Charter 4.1.4: a
            headline figure moves when the mix moves, so the per-tier table travels with it.
          </p>
        </div>
      ) : null}

      <div>
        <TableWrap label="Reference decision policy per tier">
          <table className="table table-dense">
            <caption>
              Per tier, at threshold {chartThreshold?.threshold?.toFixed(2) ?? "not stated"}. The cost of being wrong
              rises with the tier, which is what the tier scheme is for.
            </caption>
            <thead>
              <tr>
                <th scope="col">Tier</th>
                <th scope="col" className="numeric">
                  Items admitted
                </th>
                <th scope="col" className="numeric">
                  Automation rate %
                </th>
                <th scope="col" className="numeric">
                  Wrong automations
                </th>
                <th scope="col" className="numeric">
                  Wrong as % of automated
                </th>
                <th scope="col" className="numeric">
                  Open exposure items
                </th>
                <th scope="col" className="numeric">
                  Reviewer minutes
                </th>
                <th scope="col" className="numeric">
                  Rework minutes
                </th>
              </tr>
            </thead>
            <tbody>
              {(chartThreshold?.byTier ?? []).map((t) => (
                <tr key={t.tier}>
                  <th scope="row" style={{ fontWeight: 400 }}>
                    {t.tier}
                  </th>
                  <td className="numeric">{t.admitted?.toLocaleString("en-GB") ?? "not run"}</td>
                  <td className="numeric">{pct(t.automationRate)}</td>
                  <td className="numeric">{t.automatedWrong?.toLocaleString("en-GB") ?? "not run"}</td>
                  <td className="numeric">{pct(t.wrongShare)}</td>
                  <td className="numeric">{t.openExposure?.toLocaleString("en-GB") ?? "0"}</td>
                  <td className="numeric">{num(t.reviewerMinutes)}</td>
                  <td className="numeric">{num(t.reworkMinutes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </div>

      {reference.sweepBest ? (
        <div>
          <TableWrap label="The threshold that minimises net cost">
            <table className="table table-dense">
              <caption>
                Swept from 0.50 to 0.99 in steps of 0.01. Every fifth point of the sweep, and the minimising point.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Threshold</th>
                  <th scope="col" className="numeric">
                    Automation rate %
                  </th>
                  <th scope="col" className="numeric">
                    Reviewer min per 1,000 items
                  </th>
                  <th scope="col" className="numeric">
                    Rework min per 1,000 automated
                  </th>
                  <th scope="col" className="numeric">
                    Open exposure items
                  </th>
                  <th scope="col" className="numeric">
                    Net cost per item, INR
                  </th>
                </tr>
              </thead>
              <tbody>
                {reference.sweepPoints.map((p) => (
                  <tr key={String(p.threshold)}>
                    <th scope="row" style={{ fontWeight: 400 }}>
                      {Number(p.threshold).toFixed(2)}
                    </th>
                    <td className="numeric">{pct(p.automation_rate)}</td>
                    <td className="numeric">{num(p.reviewer_minutes_per_1000_items)}</td>
                    <td className="numeric">{num(p.rework_minutes_per_1000_automated)}</td>
                    <td className="numeric">{p.open_exposure_items?.toLocaleString("en-GB") ?? "0"}</td>
                    <td className="numeric">{num(p.net_cost_per_item_inr, 4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
          <p className="filter-note">
            Minimising threshold {reference.sweepMinimising?.toFixed(2) ?? "not stated"}, at which the policy automates{" "}
            {pct(reference.sweepBest.automation_rate)} percent of admitted items at a net cost of{" "}
            {num(reference.sweepBest.net_cost_per_item_inr, 4)} INR per item, with{" "}
            {reference.sweepBest.open_exposure_items ?? 0} items in open exposure. Again: a property of this dataset and
            this synthetic policy, at placeholder labour rates.
          </p>
        </div>
      ) : null}

      {reference.labourStatus ? (
        <div>
          <TableWrap label="Status of the labour model behind the money">
            <table className="table table-dense">
              <caption>Charter 3.15.6: money figures stay marked placeholder until a partner supplies the rate.</caption>
              <tbody>
                {Object.entries(reference.labourStatus).map(([k, v]) => (
                  <tr key={k}>
                    <th scope="row" style={{ fontWeight: 400, width: "40%" }}>
                      {k.replace(/_/g, " ")}
                    </th>
                    <td className="not-run">{String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </div>
      ) : null}
    </div>
  );
}
