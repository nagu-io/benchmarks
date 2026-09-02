import { SuitePage } from "@/components/SuitePage";
import { pageMeta } from "@/lib/site";

export const metadata = pageMeta({
  title: "Honest Containment",
  description: "Whether a contact was resolved or only ended. Every agent is scored under four common industry containment definitions and under ours, and the spread is published as a column.",
  path: "/honest-containment",
});

export default function Page() {
  return <SuitePage slug="honest-containment" />;
}
