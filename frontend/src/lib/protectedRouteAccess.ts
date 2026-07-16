type GuardUser = {
    role?: string | null;
};

type ProtectedRouteAccessArgs = {
    user: GuardUser | null | undefined;
    allowedRoles?: string[];
    allowedPermissions?: string[];
    hasPermission: (permission: string) => boolean;
};

export type ProtectedRouteAccessResult = {
    isAllowed: boolean;
    deniedBy: "role" | "permission" | null;
};

function normalizeRole(role: string | null | undefined): string {
    return (role || "").trim().toLowerCase();
}

function matchesAllowedRole(user: GuardUser | null | undefined, allowedRoles?: string[]): boolean {
    if (!allowedRoles?.length) return true;
    const userRole = normalizeRole(user?.role);
    if (!userRole) return false;
    return allowedRoles.some((role) => normalizeRole(role) === userRole);
}

export function evaluateProtectedRouteAccess({
    user,
    allowedRoles,
    allowedPermissions,
    hasPermission,
}: ProtectedRouteAccessArgs): ProtectedRouteAccessResult {
    const permissionRules = allowedPermissions?.filter(Boolean) ?? [];
    if (permissionRules.length > 0) {
        const hasAnyPermission = permissionRules.some((permission) => hasPermission(permission));
        return {
            isAllowed: hasAnyPermission,
            deniedBy: hasAnyPermission ? null : "permission",
        };
    }

    const roleAllowed = matchesAllowedRole(user, allowedRoles);
    return {
        isAllowed: roleAllowed,
        deniedBy: roleAllowed ? null : "role",
    };
}
