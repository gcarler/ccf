import { redirect } from 'next/navigation';

/**
 * Compatibility entry point for the assessment area.
 *
 * Assessments belong to a course/enrollment and therefore do not have an
 * independent catalog endpoint. Keep the canonical route available for
 * bookmarks and older navigation, while sending users to the Academy
 * dashboard where their enrolled assessments are presented.
 */
export default function AssessmentsIndexPage() {
  redirect('/plataforma/academy');
}
