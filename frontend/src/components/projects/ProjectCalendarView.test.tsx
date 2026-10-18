import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ProjectCalendarView from "./ProjectCalendarView";
import type { ProjectTaskRecord } from "@/types/projects";

vi.mock("@/hooks/useProjectTasks", () => ({
    useProjectTasks: () => ({
        updateTask: vi.fn().mockResolvedValue(true),
    }),
}));

vi.mock("@/components/projects/TaskCreationDrawer", () => ({
    default: () => null,
}));

vi.mock("@/components/ui/UniversalCalendarView", () => ({
    default: ({
        events,
        title,
    }: {
        events: Array<{ id: string | number; title: string; date: string }>;
        title: string;
    }) => (
        <div data-testid="mock-universal-calendar">
            <h2>{title}</h2>
            <ul>
                {events.map((event) => (
                    <li key={String(event.id)} data-testid={`calendar-event-${event.id}`}>
                        {event.title} ({event.date})
                    </li>
                ))}
            </ul>
        </div>
    ),
}));

function toDateKey(date: Date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function offsetDateKey(days: number) {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return toDateKey(d);
}

describe("ProjectCalendarView — PMI §6.5 Schedule Governance", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    const sampleTasks: ProjectTaskRecord[] = [
        {
            id: "t-overdue",
            project_id: "p1",
            title: "Paquete Vencido Crítico",
            status: "in_progress",
            priority: "urgent",
            progress: 40,
            due_date: offsetDateKey(-3),
        },
        {
            id: "t-window",
            project_id: "p1",
            title: "Entrega Ventana 7 Días",
            status: "todo",
            priority: "medium",
            progress: 10,
            due_date: offsetDateKey(4),
        },
        {
            id: "t-completed-past",
            project_id: "p1",
            title: "Hito Pasado Completado",
            status: "completed",
            priority: "high",
            progress: 100,
            due_date: offsetDateKey(-5),
        },
        {
            id: "t-future",
            project_id: "p1",
            title: "Paquete Futuro Normal",
            status: "todo",
            priority: "low",
            progress: 0,
            due_date: offsetDateKey(15),
        },
    ];

    it("renders the PMI §6.5 schedule governance HUD with overdue, 7d critical window, critical priority, and on-time rate", () => {
        render(
            <ProjectCalendarView
                projectId="p1"
                projectTitle="Proyecto Faro"
                tasks={sampleTasks}
                onOpenTask={vi.fn()}
                onCreateTask={vi.fn()}
            />
        );

        expect(screen.getByTestId("calendar-pmi-schedule-hud")).toBeInTheDocument();
        expect(screen.getByTestId("calendar-pmi-overdue-count")).toHaveTextContent("1");
        expect(screen.getByTestId("calendar-pmi-due-soon-count")).toHaveTextContent("1");
        // urgent + high = 2 tasks
        expect(screen.getByTestId("calendar-pmi-critical-count")).toHaveTextContent("2");
        // 3 out of 4 tasks are not overdue => 75%
        expect(screen.getByTestId("calendar-pmi-ontime-rate")).toHaveTextContent("75%");

        const alert = screen.getByTestId("calendar-pmi-overdue-alert");
        expect(alert).toHaveTextContent(
            /Alerta PMI §6.5: 1 paquete\(s\) con fecha límite vencida requieren reprogramación o acción correctiva/i
        );
    });

    it("filters events passed to UniversalCalendarView by OVERDUE, CRITICAL_WINDOW, CRITICAL_PRIORITY, and ALL", () => {
        render(
            <ProjectCalendarView
                projectId="p1"
                projectTitle="Proyecto Faro"
                tasks={sampleTasks}
                onOpenTask={vi.fn()}
                onCreateTask={vi.fn()}
            />
        );

        // Initially ALL (4 events)
        expect(screen.getByTestId("calendar-event-t-overdue")).toBeInTheDocument();
        expect(screen.getByTestId("calendar-event-t-window")).toBeInTheDocument();
        expect(screen.getByTestId("calendar-event-t-completed-past")).toBeInTheDocument();
        expect(screen.getByTestId("calendar-event-t-future")).toBeInTheDocument();

        // Filter OVERDUE
        fireEvent.click(screen.getByTestId("calendar-pmi-filter-overdue"));
        expect(screen.getByTestId("calendar-event-t-overdue")).toBeInTheDocument();
        expect(screen.queryByTestId("calendar-event-t-window")).not.toBeInTheDocument();
        expect(screen.queryByTestId("calendar-event-t-completed-past")).not.toBeInTheDocument();

        // Filter CRITICAL_WINDOW (7d)
        fireEvent.click(screen.getByTestId("calendar-pmi-filter-critical_window"));
        expect(screen.getByTestId("calendar-event-t-window")).toBeInTheDocument();
        expect(screen.queryByTestId("calendar-event-t-overdue")).not.toBeInTheDocument();
        expect(screen.queryByTestId("calendar-event-t-future")).not.toBeInTheDocument();

        // Filter CRITICAL_PRIORITY (urgent + high)
        fireEvent.click(screen.getByTestId("calendar-pmi-filter-critical_priority"));
        expect(screen.getByTestId("calendar-event-t-overdue")).toBeInTheDocument();
        expect(screen.getByTestId("calendar-event-t-completed-past")).toBeInTheDocument();
        expect(screen.queryByTestId("calendar-event-t-window")).not.toBeInTheDocument();

        // Back to ALL
        fireEvent.click(screen.getByTestId("calendar-pmi-filter-all"));
        expect(screen.getByTestId("calendar-event-t-future")).toBeInTheDocument();
    });

    it("hides the overdue alert when there are no overdue tasks", () => {
        const cleanTasks: ProjectTaskRecord[] = [
            {
                id: "t-ok",
                project_id: "p1",
                title: "Tarea al Día",
                status: "in_progress",
                priority: "medium",
                progress: 50,
                due_date: offsetDateKey(3),
            },
        ];

        render(
            <ProjectCalendarView
                projectId="p1"
                tasks={cleanTasks}
                onOpenTask={vi.fn()}
                onCreateTask={vi.fn()}
            />
        );

        expect(screen.getByTestId("calendar-pmi-overdue-count")).toHaveTextContent("0");
        expect(screen.getByTestId("calendar-pmi-ontime-rate")).toHaveTextContent("100%");
        expect(screen.queryByTestId("calendar-pmi-overdue-alert")).not.toBeInTheDocument();
    });
});
