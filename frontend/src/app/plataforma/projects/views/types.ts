import type { ProjectRecord } from '@/types/projects';

export interface BaseProjectViewProps {
    projects: ProjectRecord[];
    onUpdate: (id: string, patch: Partial<ProjectRecord>) => void;
    onDelete?: (id: string) => void;
}
