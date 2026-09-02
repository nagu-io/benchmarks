import { SuitePage } from "@/components/SuitePage";
import { pageMeta } from "@/lib/site";

export const metadata = pageMeta({
  title: "Day-60",
  description: "Whether a deployment is still trustworthy two months after go-live: drift detection, incident restoration, rollback and the monthly report, scored out of 100.",
  path: "/day-60",
});

export default function Page() {
  return <SuitePage slug="day-60" />;
}
