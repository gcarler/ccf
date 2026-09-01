import { redirect } from "next/navigation";

/** Legacy alias; the canonical public testimonials page is CMS-backed. */
export default function TestimonialsLegacyPage() {
  redirect("/testimonios");
}
