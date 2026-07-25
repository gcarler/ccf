'use client';

import UniversalWikiView from '@/components/ui/UniversalWikiView';

export default function ProjectsWikiView() {
    return (
        <div className="pb-4">
            <UniversalWikiView moduleName="Proyectos" storageKey="wiki_projects_portfolio" />
        </div>
    );
}
