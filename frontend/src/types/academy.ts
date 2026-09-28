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
  image_url?: string | null;
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

// H-11 (cierre 2026-07-24): tipos mirror de las schemas Pydantic en
// ``backend/schemas/academy.py`` — sustituyen los ``any`` en hooks y
// submódulos del front (forum thread/comments, course detail).
// Mantener sincronizado con el contract del backend.

export interface ForumThreadRecord {
  id: string;
  title: string;
  category: string;
  author_persona_id: string;
  is_resolved: boolean;
  created_at: string;
  // Backend ``ForumThread`` no expone ``content`` en la lista, pero el
  // detalle del thread lo incluye vía el row ORM completo — opcional aquí
  // para que page.tsx del detalle pueda leerlo sin romper TS.
  content?: string;
  course_id?: string | null;
  // Campos opcionales derivados/presentes en el detalle del thread.
  author?: string | null;
  author_role?: string | null;
  upvotes?: number;
}

export interface ForumCommentRecord {
  id: string;
  thread_id: string;
  parent_id?: string | null;
  author_persona_id: string;
  content: string;
  created_at: string;
}

export interface CourseDetail {
  id: string;
  code: string;
  slug?: string | null;
  title: string;
  description?: string | null;
  excerpt?: string | null;
  tag?: string | null;
  cta_text?: string | null;
  syllabus?: Record<string, unknown> | unknown[] | null;
  modality: string;
  sede_id?: string | null;
  is_published: boolean;
  is_self_paced: boolean;
  duration_hours: number;
  xp_per_lesson?: number;
  cohort_name?: string | null;
  certificate_type?: string | null;
  access_level: string;
  image_url?: string | null;
  instructor_name?: string | null;
  created_at?: string | null;
  lesson_count?: number;
  total_minutes?: number;
  lessons?: LessonRecord[];
  // H-11 (cierre 2026-07-24) + F-02bis (cierre 2026-08-02):
  // ``students_count`` SÍ es emitido por ``_serialize_course`` en list/detail
  // (count bulk Axioma-3, sin N+1; 0 para cursos globales en un Manager con
  // sede — scope admin estricto F-02). ``lesson_count`` (singular) es el
  // campo real de lecciones. ``lessons_count`` es histórico muerto (el backend
  // nunca lo emite) y se conserva por tolerancia, sin renderizarse.
  students_count?: number;
  lessons_count?: number;
}

export interface CertificateDetail {
  id: string;
  enrollment_id: string;
  certificate_code: string;
  issued_at: string;
  certificate_type?: string | null;
  course_title?: string | null;
}

export interface AcademyCalendarEvent {
  id: string;
  offering_id?: string | null;
  title: string;
  description?: string | null;
  event_type: string;
  start_date: string;
  end_date: string;
  sede_id?: string | null;
  created_by: string;
  created_at: string;
}

export interface WorkloadWeekPrediction {
  week_number: number;
  year: number;
  start_date: string;
  end_date: string;
  total_events: number;
  evaluations_count: number;
  assignments_count: number;
  socratic_defenses_count: number;
  other_events_count: number;
  workload_score: number;
  workload_level: string;
  is_overloaded: boolean;
  events: AcademyCalendarEvent[];
}

export interface WorkloadPredictionResponse {
  student_id?: string | null;
  offering_id?: string | null;
  weeks_analyzed: number;
  total_events: number;
  overloaded_weeks_count: number;
  weeks: WorkloadWeekPrediction[];
  recommendations: string[];
}

// ── Super-PRO Academic ERP Types ──────────────────────────────────────────────

export type ProgramType =
  | 'curso_libre'
  | 'diplomado'
  | 'carrera'
  | 'especializacion'
  | 'maestria'
  | 'doctorado'
  | 'taller'
  | 'certificacion'
  | 'otro';

export interface AcademicProgram {
  id: string;
  sede_id?: string | null;
  code: string;
  name: string;
  description?: string | null;
  program_type: ProgramType | string;
  level_name?: string | null;
  total_duration_type: string;
  total_duration_units: number;
  total_credits: number;
  modality: string;
  has_teachers: boolean;
  teachers_can_grade: boolean;
  min_passing_grade: number;
  grading_scale_max: number;
  min_attendance_percent: number;
  is_active: boolean;
  study_plans_count?: number;
  created_at?: string | null;
}

export interface AcademicPeriod {
  id: string;
  sede_id?: string | null;
  code: string;
  name: string;
  period_type: string;
  start_date: string;
  end_date: string;
  enrollment_start_date?: string | null;
  enrollment_end_date?: string | null;
  grading_deadline?: string | null;
  status: 'draft' | 'open' | 'in_progress' | 'grading' | 'closed' | string;
  is_active: boolean;
  offerings_count?: number;
  created_at?: string | null;
}

export interface GradingSchemeCut {
  id?: string;
  scheme_id?: string;
  name: string;
  order_index: number;
  weight_percent: number;
  description?: string | null;
}

export interface GradingScheme {
  id: string;
  sede_id?: string | null;
  name: string;
  description?: string | null;
  scale_max: number;
  passing_grade: number;
  is_default: boolean;
  is_active: boolean;
  cuts: GradingSchemeCut[];
  created_at?: string | null;
}

export interface StudyPlanSubject {
  id: string;
  study_plan_id: string;
  course_id?: string | null;
  code: string;
  name: string;
  level_number: number;
  credits: number;
  weekly_hours_theory: number;
  weekly_hours_practice: number;
  weekly_hours_independent: number;
  is_mandatory: boolean;
  default_grading_scheme_id?: string | null;
  order_index: number;
  prerequisite_codes?: string[] | null;
  created_at?: string | null;
}

export interface StudyPlan {
  id: string;
  program_id: string;
  sede_id?: string | null;
  code: string;
  name: string;
  total_credits: number;
  total_levels: number;
  level_type: string;
  is_active: boolean;
  program_name?: string | null;
  subjects: StudyPlanSubject[];
  created_at?: string | null;
}

export interface PeriodOffering {
  id: string;
  sede_id?: string | null;
  academic_period_id: string;
  subject_id: string;
  course_id?: string | null;
  docente_persona_id?: string | null;
  grading_scheme_id: string;
  group_name: string;
  quota_max: number;
  status: string;
  classroom?: string | null;
  schedule_summary?: string | null;
  subject_name?: string | null;
  subject_code?: string | null;
  credits: number;
  docente_name?: string | null;
  period_code?: string | null;
  grading_scheme_name?: string | null;
  enrolled_count: number;
  created_at?: string | null;
}

export interface StudentSubjectRecord {
  id: string;
  offering_id: string;
  persona_id: string;
  student_name: string;
  credits_attempted: number;
  credits_earned: number;
  calculated_final_grade?: number | null;
  final_grade_override?: number | null;
  passed: boolean;
  status: string;
  grades_by_cut?: Record<string, number | null>;
}

export interface OfferingGradesDetail {
  offering_id: string;
  subject_name: string;
  subject_code: string;
  credits: number;
  period_code: string;
  cuts: GradingSchemeCut[];
  records: StudentSubjectRecord[];
}

export interface AcademicTranscriptSubject {
  offering_id?: string | null;
  subject_code: string;
  subject_name: string;
  credits: number;
  period_code: string;
  final_grade: number;
  passed: boolean;
  status: string;
}

export interface AcademicTranscriptSummary {
  persona_id: string;
  student_name: string;
  total_credits_attempted: number;
  total_credits_earned: number;
  total_credits_required?: number | null;
  weighted_gpa: number;
  subjects: AcademicTranscriptSubject[];
}

export interface StudentAcademicCommission {
  offering_id: string;
  subject_name: string;
  subject_code?: string | null;
  period_code?: string | null;
  group_name?: string | null;
  credits?: number;
  status?: string | null;
}

export interface SocraticSession {
  id: string;
  offering_id: string;
  student_id: string;
  question: string;
  response: string;
  session_type: string;
  created_at: string;
}

export interface SocraticQueryResponse {
  session_id: string;
  offering_id: string;
  student_id: string;
  question: string;
  socratic_response: string;
  session_type: string;
  created_at: string;
}

export interface DefenseSession {
  id: string;
  offering_id?: string | null;
  submission_id?: string | null;
  student_id: string;
  status: string;
  score?: number | null;
  duration_seconds: number;
  current_question_index: number;
  total_questions: number;
  current_question?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  time_remaining_seconds?: number | null;
}

export interface DefenseAnswer {
  session_id: string;
  status: string;
  current_question_index: number;
  total_questions: number;
  next_question?: string | null;
  is_completed: boolean;
  score?: number | null;
  feedback?: string | null;
}

export interface DefenseScore {
  session_id: string;
  status: string;
  score: number;
  feedback: string;
  ended_at: string;
}

export interface StudentEnrollment {
  id: string;
  offering_id: string;
  persona_id: string;
  student_name?: string | null;
  enrolled_by_persona_id?: string | null;
  enrolled_at: string;
  status: string;
  deleted_at?: string | null;
}

export interface KnowledgeNode {
  id: string;
  offering_id: string;
  title: string;
  description?: string | null;
  node_type: 'concept' | 'skill' | 'competency' | string;
  weight: number;
  created_at: string;
  deleted_at?: string | null;
  sede_id?: string | null;
}

export interface KnowledgeEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: 'requires' | 'leads_to' | 'related' | string;
  weight: number;
  created_at: string;
  deleted_at?: string | null;
  sede_id?: string | null;
}

export interface KnowledgeGraph {
  offering_id: string;
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export interface StudentNodeProgress {
  id: string;
  student_id: string;
  node_id: string;
  mastery_score: number;
  attempts: number;
  last_evaluated_at?: string | null;
  created_at: string;
}

export interface LearningPathNode {
  node_id: string;
  title: string;
  node_type: string;
  mastery_score: number;
  status: 'ready_to_learn' | 'needs_prerequisites' | 'mastered' | string;
  order_index: number;
}

export interface LearningPath {
  offering_id: string;
  student_id: string;
  current_average_mastery: number;
  path: LearningPathNode[];
  suggested_next_node?: LearningPathNode | null;
}

export interface PortfolioEntry {
  id: string;
  student_id: string;
  offering_id?: string | null;
  entry_type: 'project' | 'defense' | 'certification' | 'grade' | string;
  title: string;
  description?: string | null;
  evidence_url?: string | null;
  score?: number | null;
  issued_at: string;
  credential_hash?: string | null;
  is_public: boolean;
  created_at: string;
}

export interface CredentialVerification {
  entry_id: string;
  is_valid: boolean;
  credential_hash?: string | null;
  calculated_hash: string;
  issued_at: string;
  student_id: string;
}

export type PortfolioVerifyResult = CredentialVerification;

export type WellnessSignalType = 'engagement_drop' | 'grade_risk' | 'absence_pattern' | 'stress_indicator' | string;
export type WellnessSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface WellnessSignal {
  id: string;
  student_id: string;
  offering_id?: string | null;
  signal_type: WellnessSignalType;
  severity: WellnessSeverity;
  detected_at: string;
  details?: Record<string, unknown> | null;
  is_resolved: boolean;
  resolved_at?: string | null;
  resolved_by_id?: string | null;
  created_at: string;
  student_name?: string | null;
}

export interface WellnessAlert {
  id: string;
  signal_id: string;
  recipient_id: string;
  message: string;
  sent_at: string;
  read_at?: string | null;
  created_at: string;
  signal_type?: string | null;
  severity?: string | null;
  detected_at?: string | null;
  is_resolved?: boolean;
}

export interface StudentRiskProfile {
  student_id: string;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical' | string;
  active_signals_count: number;
  signals: WellnessSignal[];
  recommendations: string[];
}

export interface CopilotSuggestion {
  activity_type: 'socratic_dialogue' | 'practical_exercise' | 'recommended_resource' | 'group_challenge' | string;
  title: string;
  description: string;
  estimated_duration_minutes: number;
  aligned_nodes: string[];
}

export interface CopilotRubricCriterion {
  criterion: string;
  weight: number;
  levels: {
    level_1_insufficient: string;
    level_2_basic: string;
    level_3_competent: string;
    level_4_exemplary: string;
    [key: string]: string;
  };
}

export interface CopilotRubric {
  title: string;
  competencies: string[];
  criteria: CopilotRubricCriterion[];
}

export interface ClassPerformanceReport {
  offering_id: string;
  total_students: number;
  average_grade: number;
  grade_distribution: {
    '90-100': number;
    '80-89': number;
    '70-79': number;
    'under_70': number;
    [key: string]: number;
  };
  weak_knowledge_nodes: Array<{
    node_id: string;
    title: string;
    average_mastery: number;
    students_count: number;
  }>;
  at_risk_students: Array<{
    student_id: string;
    signal_type: string;
    severity: string;
    reason: string;
  }>;
  pedagogical_recommendations: string[];
}

export interface WeeklyReport {
  offering_id: string;
  week_period: string;
  total_enrolled: number;
  average_attendance_percent: number;
  grades_summary: {
    average: number;
    highest: number;
    lowest: number;
    evaluations_count: number;
  };
  wellness_alerts_count: number;
  active_wellness_signals: WellnessSignal[];
  knowledge_graph_progress_percent: number;
  key_highlights: string[];
}

export interface Achievement {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  achievement_type: 'completion' | 'excellence' | 'defense' | 'streak' | 'milestone';
  points: number;
  badge_icon?: string | null;
  is_active: boolean;
  sede_id?: string | null;
  created_at: string;
}

export interface StudentAchievement {
  id: string;
  student_id: string;
  achievement_id: string;
  offering_id?: string | null;
  earned_at: string;
  evidence?: Record<string, unknown> | null;
  credential_hash?: string | null;
  sede_id?: string | null;
  achievement?: Achievement | null;
}

export interface LeaderboardEntry {
  id: string;
  student_id: string;
  student_name: string;
  total_points: number;
  rank?: number | null;
  period: string;
  offering_id?: string | null;
  updated_at: string;
}

export interface AchievementCredentialVerification {
  verified: boolean;
  student_id: string;
  student_name: string;
  achievement_id: string;
  achievement_title: string;
  badge_icon?: string | null;
  points: number;
  credential_hash: string;
  earned_at: string;
  is_valid: boolean;
}

export interface StudyGroupMember {
  id: string;
  group_id: string;
  student_id: string;
  student_name: string;
  role: string;
  joined_at: string;
  sede_id?: string | null;
}

export interface StudyGroup {
  id: string;
  offering_id: string;
  name: string;
  description?: string | null;
  max_members: number;
  is_active: boolean;
  created_by: string;
  creator_name?: string | null;
  created_at: string;
  members_count: number;
  members: StudyGroupMember[];
}

export interface MentorProfile {
  id: string;
  mentor_persona_id?: string | null;
  persona_id?: string | null;
  mentor_name?: string | null;
  name?: string | null;
  full_name?: string | null;
  expertise?: string[] | string | null;
  availability?: string[] | string | null;
  availability_summary?: string | null;
  bio?: string | null;
  description?: string | null;
}

export interface MentorshipRequest {
  id: string;
  mentor_persona_id?: string | null;
  mentee_persona_id?: string | null;
  mentor_name?: string | null;
  mentee_name?: string | null;
  status: string;
  message?: string | null;
  requested_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface MentorshipMentee {
  id: string;
  mentee_persona_id?: string | null;
  mentee_name: string;
  status?: string | null;
  started_at?: string | null;
  created_at?: string | null;
  goals?: string[] | null;
}

export interface AcademyRecommendation {
  id: string;
  recommendation_type: string;
  title: string;
  reason: string;
  score: number;
  description?: string | null;
  target_url?: string | null;
  viewed?: boolean;
  created_at: string;
}
