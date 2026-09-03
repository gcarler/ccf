import { redirect } from "next/navigation";

/**
 * /plataforma/academy/assessments — redirige al dashboard de academia.
 * Las páginas individuales de evaluación están en /plataforma/academy/assessments/[id].
 */
export default function AssessmentsIndexPage() {
  redirect("/plataforma/academy");
}
