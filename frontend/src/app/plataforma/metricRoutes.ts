export function getPlatformMetricHref(title: string): string | null {
    const normalized = title.toLowerCase();
    if (normalized.includes('proyecto') || normalized.includes('project')) {
        return '/plataforma/projects/list';
    }
    return null;
}
