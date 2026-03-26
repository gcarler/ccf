export const getInitials = (name: string) => {
    if (!name) return '';
    const parts = name.split(' ').filter(Boolean);
    const sliced = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? '');
    return sliced.join('');
};

export const parseCommentCount = (text?: string | null) => {
    if (!text) return 0;
    const match = text.match(/\d+/);
    return match ? Number(match[0]) : 0;
};

export const formatDueLabel = (isoDate?: string | null) => {
    if (!isoDate) return '—';
    const parsed = new Date(isoDate);
    if (Number.isNaN(parsed.getTime())) {
        return isoDate;
    }
    return parsed.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' });
};
