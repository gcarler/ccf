export interface CourseSummary {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  modality: string;
  duration_hours: number;
  is_self_paced: boolean;
  cohort_name?: string | null;
  certificate_type?: string | null;
}

export interface EnrollmentRecord {
  id: string;
  status: string;
  progress_percent: number;
  final_grade?: number | null;
  attendance_percent: number;
  approved: boolean;
  certificate_issued: boolean;
  acta_closed: boolean;
  course: CourseSummary;
}

export interface LessonRecord {
  id: string;
  course_id: string;
  title: string;
  content: string;
  order_index: number;
  duration_minutes: number;
}

export interface CertificateRecord {
  id: string;
  enrollment_id: string;
  certificate_code: string;
  certificate_type?: string | null;
  course_title?: string | null;
  issued_at: string;
}

export interface AssignmentSubmissionReview {
  id: string;
  enrollment_id: string;
  lesson_id: string;
  student_name: string;
  lesson_title: string;
  file_url: string;
  comment?: string | null;
  grade?: number | null;
  teacher_feedback?: string | null;
  submitted_at: string;
}

export interface MetricCard {
  title: string;
  value: string;
  trend: string;
  tone: string;
}

export interface DashboardMetrics {
  active_students?: number;
  completion_rate?: number;
  certificates_issued?: number;
  total_courses: number;
  formal_courses: number;
  non_formal_courses: number;
  total_enrollments: number;
  completed_enrollments: number;
  approved_formal_enrollments: number;
  approved_non_formal_enrollments: number;
  cards?: MetricCard[];
  enrollment_trends?: { label: string; value: number }[];
  top_courses?: { title: string; count: number }[];
}

export interface PilotChecklistItem {
  key: string;
  label: string;
  completed: boolean;
}

export interface PilotReadiness {
  environment_ready: boolean;
  kpi_dashboard_ready: boolean;
  support_ready: boolean;
  security_ready: boolean;
  readiness_score: number;
  checklist: PilotChecklistItem[];
}

export interface AcademyStudentProfile {
  persona_id: string;
  username: string;
  total_progress: number;
  enrollments_count: number;
  certificates_count: number;
  active_courses: EnrollmentRecord[];
  recent_certificates: CertificateRecord[];
}
