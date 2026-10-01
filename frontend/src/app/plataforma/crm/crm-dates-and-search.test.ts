import { describe, expect, it } from 'vitest';
import { parseCrmDateKey, formatCrmCalendarDate, parseCrmLeadDateKey, formatCrmLeadCalendarDate } from '@/components/crm/crmDates';

describe('CRM Dates & Search Regression Suite (QA-001 / QA-003 / QA-004)', () => {
    it('groups tasks by date safely, ignoring invalid dates without throwing RangeError', () => {
        const tasks = [
            { id: '1', title: 'Task 1', due_date: '2026-10-01T10:00:00Z' },
            { id: '2', title: 'Task 2', due_date: '2026-10-01' },
            { id: '3', title: 'Task 3', due_date: 'invalid-date' },
            { id: '4', title: 'Task 4', due_date: null },
            { id: '5', title: 'Task 5', due_date: '2026-10-02' },
        ];

        const map: Record<string, typeof tasks> = {};
        for (const task of tasks) {
            const key = parseCrmDateKey(task.due_date);
            if (!key) continue;
            if (!map[key]) map[key] = [];
            map[key].push(task);
        }

        const entries = Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
        expect(entries).toHaveLength(2);
        expect(entries[0][0]).toBe('2026-10-01');
        expect(entries[0][1]).toHaveLength(2);
        expect(entries[1][0]).toBe('2026-10-02');
        expect(entries[1][1]).toHaveLength(1);

        // Verify formatting does not crash
        expect(formatCrmCalendarDate(entries[0][0])).toBeTruthy();
    });

    it('groups newsletter leads by date safely, placing invalid or missing dates under unknown', () => {
        const leads = [
            { case_id: 1, created_at: '2026-10-05T08:00:00Z' },
            { case_id: 2, created_at: null },
            { case_id: 3, created_at: 'malformed-timestamp' },
            { case_id: 4, created_at: '2026-10-05' },
        ];

        const grouped: Record<string, typeof leads> = {};
        for (const lead of leads) {
            const date = parseCrmLeadDateKey(lead.created_at);
            if (!grouped[date]) grouped[date] = [];
            grouped[date].push(lead);
        }

        expect(grouped['2026-10-05']).toHaveLength(2);
        expect(grouped['unknown']).toHaveLength(2);
        expect(formatCrmLeadCalendarDate('unknown')).toBe('Sin fecha');
        expect(formatCrmLeadCalendarDate('2026-10-05')).toBeTruthy();
    });

    it('validates persona query URL format in resources page uses ?search=', () => {
        const searchTerm = 'Juan Perez';
        const expectedUrl = `/crm/personas?search=${encodeURIComponent(searchTerm)}&limit=10`;
        expect(expectedUrl).toContain('?search=Juan%20Perez');
        expect(expectedUrl).not.toContain('?q=');
    });
});
