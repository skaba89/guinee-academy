import { useEffect, useState } from "react";
import { useParams, Navigate } from "react-router-dom";
import { useTenant } from "@/contexts/TenantContext";
import { usePublicTenant } from "@/hooks/usePublicTenant";
import { Skeleton } from "@/components/ui/skeleton";

export function TenantRoute({ children }: { children: React.ReactNode }) {
    const { tenantSlug } = useParams<{ tenantSlug: string }>();
    const { tenant, isLoading: tenantCtxLoading, setCurrentTenant } = useTenant();
    const { data: publicTenant, isLoading: publicLoading, isError: publicError } = usePublicTenant(tenantSlug);
    const [synced, setSynced] = useState(false);

    // Use the public tenant data to populate the tenant context
    // This avoids needing authentication to resolve the slug
    useEffect(() => {
        if (publicTenant && (!tenant || tenant.slug !== publicTenant.slug)) {
            setCurrentTenant(publicTenant as any);
            setSynced(true);
        } else if (tenant && tenant.slug === tenantSlug) {
            setSynced(true);
        } else if (publicError) {
            // Public tenant lookup failed (404 or error) — don't keep waiting
            setSynced(true);
        }
    }, [publicTenant, tenant, tenantSlug, setCurrentTenant, publicError]);

    const isLoading = tenantCtxLoading || publicLoading;

    // Show loading while resolving tenant
    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-background">
                <div className="space-y-4 w-full max-w-md p-8">
                    <Skeleton className="h-8 w-3/4 mx-auto" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-5/6" />
                    <Skeleton className="h-32 w-full" />
                </div>
            </div>
        );
    }

    // Only redirect after loading is done AND we confirmed no tenant exists.
    // Previously, this could redirect prematurely during loading or before
    // the public tenant lookup completed.
    if (!synced) {
        // Still syncing — show loading instead of redirecting
        return (
            <div className="flex items-center justify-center min-h-screen bg-background">
                <div className="space-y-4 w-full max-w-md p-8">
                    <Skeleton className="h-8 w-3/4 mx-auto" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-5/6" />
                    <Skeleton className="h-32 w-full" />
                </div>
            </div>
        );
    }

    // Confirmed: no tenant found after loading completed
    if (!tenant && !publicTenant) {
        return <Navigate to={tenantSlug ? `/${tenantSlug}/auth` : "/"} replace />;
    }

    return <>{children}</>;
}
