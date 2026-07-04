"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth";

export function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <span className="text-sm font-bold text-indigo-700">Code de la Route</span>
        <div className="flex items-center gap-3">
          {user ? <span className="text-sm text-slate-600">{user.email}</span> : null}
          <Button
            variant="secondary"
            onClick={async () => {
              await logout();
              router.replace("/login");
            }}
          >
            Déconnexion
          </Button>
        </div>
      </div>
    </header>
  );
}
