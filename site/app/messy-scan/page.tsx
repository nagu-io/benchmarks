import { SuitePage } from "@/components/SuitePage";
import { pageMeta } from "@/lib/site";

export const metadata = pageMeta({
  title: "Messy Scan",
  description: "What degradation does to document extraction, and how much of the volume survives without a person. Five tiers, four document types, four language mixes.",
  path: "/messy-scan",
});

export default function Page() {
  return <SuitePage slug="messy-scan" />;
}
