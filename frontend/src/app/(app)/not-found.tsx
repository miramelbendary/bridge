import { ButtonLink, EmptyState } from "@/components/ui";

export default function NotFound() {
  return (
    <EmptyState title="Not found">
      <p>This page does not exist, or you do not have access to it.</p>
      <ButtonLink href="/dashboard" variant="secondary" className="mt-4">
        Back to dashboard
      </ButtonLink>
    </EmptyState>
  );
}
