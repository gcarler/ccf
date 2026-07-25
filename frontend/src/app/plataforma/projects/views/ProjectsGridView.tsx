'use client';

import ProjectCard from '@/components/projects/ProjectCard';
import type { ProjectRecord } from '@/types/projects';
import type { BaseProjectViewProps } from './types';

interface ProjectsGridViewProps extends BaseProjectViewProps {}

export default function ProjectsGridView({ projects, onUpdate, onDelete }: ProjectsGridViewProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 pb-4">
            {projects.map((project, idx) => (
                <ProjectCard
                    key={project.id}
                    project={project}
                    index={idx}
                    onUpdate={onUpdate}
                    onDelete={onDelete}
                />
            ))}
        </div>
    );
}
