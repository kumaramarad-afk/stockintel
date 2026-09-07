import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-20 text-center">
      <p className="text-sm uppercase tracking-wide text-gsr-accent">404</p>
      <h1 className="mt-2 text-3xl font-semibold">Not found</h1>
      <p className="mt-2 text-gsr-muted">That page is not in coverage.</p>
      <Link href="/" className="mt-6 inline-block text-gsr-accent hover:text-white">
        Back to research
      </Link>
    </div>
  );
}
