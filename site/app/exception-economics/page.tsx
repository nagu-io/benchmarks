import { SuitePage } from "@/components/SuitePage";
import { pageMeta } from "@/lib/site";

export const metadata = pageMeta({
  title: "Exception Economics",
  description: "What automation costs when it is wrong, in reviewer minutes and money, at three confidence thresholds.",
  path: "/exception-economics",
});

export default function Page() {
  return <SuitePage slug="exception-economics" />;
}
