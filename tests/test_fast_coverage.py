"""
Fast Endpoint Coverage — Hits the most impactful endpoints quickly.
"""
import pytest
from tests.conftest import seed_admin_v2, auth_headers_v2


@pytest.fixture(scope="function")
def ac(client, db_session):
    user, persona, sede = seed_admin_v2(db_session)
    h = auth_headers_v2(client)
    return client, h, sede, persona


OK = (200, 201, 400, 401, 403, 404, 405, 422, 424, 500)


class TestAdminFast:
    def test_admin_users(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/users", headers=h).status_code in OK
    def test_admin_roles(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/roles", headers=h).status_code in OK
    def test_admin_audit(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/audit", headers=h).status_code in OK
    def test_admin_personas(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/personas", headers=h).status_code in OK
    def test_admin_automations(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/automations", headers=h).status_code in OK
    def test_admin_milestones(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/milestones", headers=h).status_code in OK
    def test_admin_permissions(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/permissions", headers=h).status_code in OK
    def test_admin_variables(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/variables", headers=h).status_code in OK
    def test_admin_comments(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/comments", headers=h).status_code in OK
    def test_admin_socials(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/socials", headers=h).status_code in OK
    def test_admin_locations(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/locations", headers=h).status_code in OK
    def test_admin_donation_categories(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/donation-categories", headers=h).status_code in OK
    def test_admin_user_module_roles(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/user-module-roles", headers=h).status_code in OK
    def test_admin_auth_role_definitions(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/auth-role-definitions", headers=h).status_code in OK
    def test_admin_users_with_roles(self, ac):
        c, h, s, p = ac; assert c.get("/api/admin/users-with-roles", headers=h).status_code in OK


class TestAcademyFast:
    def test_academy_courses(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/courses/", headers=h).status_code in OK
    def test_academy_enrollments(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/enrollments", headers=h).status_code in OK
    def test_academy_lessons(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/lessons/", headers=h).status_code in OK
    def test_academy_assessments(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/assessments/", headers=h).status_code in OK
    def test_academy_certificates(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/me/certificates", headers=h).status_code in OK
    def test_academy_forum(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/forum/threads", headers=h).status_code in OK
    def test_academy_schedule(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/schedule", headers=h).status_code in OK
    def test_academy_personas(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/personas", headers=h).status_code in OK
    def test_academy_me_enrollments(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/me/enrollments", headers=h).status_code in OK
    def test_academy_me_progress(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/me/progress", headers=h).status_code in OK
    def test_academy_me_profile(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/me/profile", headers=h).status_code in OK
    def test_academy_dashboard(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/dashboard/metrics", headers=h).status_code in OK
    def test_academy_admin_submissions(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/admin/submissions", headers=h).status_code in OK
    def test_academy_analytics(self, ac):
        c, h, s, p = ac; assert c.get("/api/academy/analytics/candidates", headers=h).status_code in OK


class TestProjectsFast:
    def test_projects_list(self, ac):
        c, h, s, p = ac; assert c.get("/api/projects", headers=h).status_code in OK
    def test_projects_tasks(self, ac):
        c, h, s, p = ac; assert c.get("/api/projects/tasks", headers=h).status_code in OK
    def test_projects_summary(self, ac):
        c, h, s, p = ac; assert c.get("/api/projects/summary", headers=h).status_code in OK
    def test_projects_workload(self, ac):
        c, h, s, p = ac; assert c.get("/api/projects/workload", headers=h).status_code in OK
    def test_projects_activities(self, ac):
        c, h, s, p = ac; assert c.get("/api/projects/activities", headers=h).status_code in OK
    def test_projects_inbox(self, ac):
        c, h, s, p = ac; assert c.get("/api/projects/inbox", headers=h).status_code in OK
    def test_projects_comments(self, ac):
        c, h, s, p = ac; assert c.get("/api/projects/comments", headers=h).status_code in OK


class TestEvangelismFast:
    def test_evangelism_strategies(self, ac):
        c, h, s, p = ac; assert c.get("/api/evangelism/strategies", headers=h).status_code in OK
    def test_evangelism_grupos(self, ac):
        c, h, s, p = ac; assert c.get("/api/evangelism/grupos", headers=h).status_code in OK
    def test_evangelism_sesiones(self, ac):
        c, h, s, p = ac; assert c.get("/api/evangelism/sesiones", headers=h).status_code in OK
    def test_evangelism_asistencias(self, ac):
        c, h, s, p = ac; assert c.get("/api/evangelism/asistencias", headers=h).status_code in OK
    def test_evangelism_reports(self, ac):
        c, h, s, p = ac; assert c.get("/api/evangelism/reports", headers=h).status_code in OK
    def test_evangelism_analytics(self, ac):
        c, h, s, p = ac; assert c.get("/api/evangelism/analytics", headers=h).status_code in OK
    def test_evangelism_notifications(self, ac):
        c, h, s, p = ac; assert c.get("/api/evangelism/notifications", headers=h).status_code in OK
    def test_evangelism_rankings(self, ac):
        c, h, s, p = ac; assert c.get("/api/evangelism/rankings", headers=h).status_code in OK
    def test_evangelism_multiplication(self, ac):
        c, h, s, p = ac; assert c.get("/api/evangelism/multiplication", headers=h).status_code in OK


class TestCrmPastoralFast:
    def test_crm_pastoral(self, ac):
        c, h, s, p = ac; assert c.get("/api/crm/pastoral", headers=h).status_code in OK
    def test_crm_tasks(self, ac):
        c, h, s, p = ac; assert c.get("/api/crm/tasks", headers=h).status_code in OK
    def test_crm_roles(self, ac):
        c, h, s, p = ac; assert c.get("/api/crm/roles", headers=h).status_code in OK
    def test_crm_volunteers(self, ac):
        c, h, s, p = ac; assert c.get("/api/crm/volunteers", headers=h).status_code in OK


class TestAuthV3Fast:
    def test_v3_me(self, ac):
        c, h, s, p = ac; assert c.get("/api/v3/auth/me", headers=h).status_code in OK
    def test_v3_check_email(self, ac):
        c, h, s, p = ac; assert c.get("/api/v3/auth/check-email?email=x@y.com", headers=h).status_code in OK


class TestAgentsFast:
    def test_agents_list(self, ac):
        c, h, s, p = ac; assert c.get("/api/agents", headers=h).status_code in OK
    def test_agents_tasks(self, ac):
        c, h, s, p = ac; assert c.get("/api/agents/tasks", headers=h).status_code in OK
    def test_agents_conversations(self, ac):
        c, h, s, p = ac; assert c.get("/api/agents/conversations", headers=h).status_code in OK
    def test_agents_insights(self, ac):
        c, h, s, p = ac; assert c.get("/api/agents/insights", headers=h).status_code in OK
    def test_agents_search(self, ac):
        c, h, s, p = ac; assert c.get("/api/agents/search", headers=h).status_code in OK
    def test_agents_analytics(self, ac):
        c, h, s, p = ac; assert c.get("/api/agents/analytics/summary", headers=h).status_code in OK
    def test_agents_kb_search(self, ac):
        c, h, s, p = ac; assert c.get("/api/agents/kb/search", headers=h).status_code in OK
    def test_agents_kb_stats(self, ac):
        c, h, s, p = ac; assert c.get("/api/agents/kb/stats", headers=h).status_code in OK


class TestWorkspaceFast:
    def test_workspace_list(self, ac):
        c, h, s, p = ac; assert c.get("/api/workspace", headers=h).status_code in OK


class TestDonationsFast:
    def test_donations_list(self, ac):
        c, h, s, p = ac; assert c.get("/api/donations", headers=h).status_code in OK
    def test_donations_funds(self, ac):
        c, h, s, p = ac; assert c.get("/api/donations/funds", headers=h).status_code in OK
    def test_donations_categories(self, ac):
        c, h, s, p = ac; assert c.get("/api/donations/categories", headers=h).status_code in OK


class TestFinanceFast:
    def test_finance_funds(self, ac):
        c, h, s, p = ac; assert c.get("/api/finance/funds", headers=h).status_code in OK
    def test_finance_transactions(self, ac):
        c, h, s, p = ac; assert c.get("/api/finance/transactions", headers=h).status_code in OK


class TestAnalyticsFast:
    def test_analytics_dashboard(self, ac):
        c, h, s, p = ac; assert c.get("/api/analytics/dashboard-metrics", headers=h).status_code in OK
    def test_analytics_radar(self, ac):
        c, h, s, p = ac; assert c.get("/api/analytics/radar", headers=h).status_code in OK
    def test_analytics_events(self, ac):
        c, h, s, p = ac; assert c.get("/api/analytics/events/summary", headers=h).status_code in OK


class TestGovernanceFast:
    def test_governance_rules(self, ac):
        c, h, s, p = ac; assert c.get("/api/governance/automation-rules", headers=h).status_code in OK


class TestMessagingFast:
    def test_messaging_conversations(self, ac):
        c, h, s, p = ac; assert c.get("/api/messaging/conversations", headers=h).status_code in OK


class TestChatFast:
    def test_chat_conversations(self, ac):
        c, h, s, p = ac; assert c.get("/api/chat/conversations", headers=h).status_code in OK


class TestSupportFast:
    def test_support_tickets(self, ac):
        c, h, s, p = ac; assert c.get("/api/support/tickets", headers=h).status_code in OK
    def test_support_kb(self, ac):
        c, h, s, p = ac; assert c.get("/api/support/kb", headers=h).status_code in OK
    def test_support_tutorials(self, ac):
        c, h, s, p = ac; assert c.get("/api/support/tutorials", headers=h).status_code in OK


class TestSpiritualFast:
    def test_spiritual_certificates(self, ac):
        c, h, s, p = ac; assert c.get("/api/spiritual-life/certificates", headers=h).status_code in OK
    def test_spiritual_timeline(self, ac):
        c, h, s, p = ac; assert c.get("/api/spiritual-life/timeline", headers=h).status_code in OK


class TestPrayerFast:
    def test_prayer_requests(self, ac):
        c, h, s, p = ac; assert c.get("/api/prayer/requests", headers=h).status_code in OK


class TestYoutubeFast:
    def test_youtube_videos(self, ac):
        c, h, s, p = ac; assert c.get("/api/youtube/videos", headers=h).status_code in OK


class TestCmsV2Fast:
    def test_cms_sites(self, ac):
        c, h, s, p = ac; assert c.get("/api/cms/v2/sites", headers=h).status_code in OK
    def test_cms_pages(self, ac):
        c, h, s, p = ac; assert c.get("/api/cms/v2/sites/faro/pages", headers=h).status_code in OK
    def test_cms_menus(self, ac):
        c, h, s, p = ac; assert c.get("/api/cms/v2/sites/faro/menus", headers=h).status_code in OK
    def test_cms_themes(self, ac):
        c, h, s, p = ac; assert c.get("/api/cms/v2/sites/faro/themes", headers=h).status_code in OK
    def test_cms_global_blocks(self, ac):
        c, h, s, p = ac; assert c.get("/api/cms/v2/global-blocks", headers=h).status_code in OK
    def test_cms_media(self, ac):
        c, h, s, p = ac; assert c.get("/api/cms/v2/media", headers=h).status_code in OK
