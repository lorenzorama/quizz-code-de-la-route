"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();

  return (
    <AuthForm
      title="Connexion"
      submitLabel="Se connecter"
      onSubmit={async (email, password) => {
        await login(email, password);
        router.push("/");
      }}
      footer={
        <>
          Pas de compte ?{" "}
          <Link href="/register" className="font-semibold text-indigo-700 hover:underline">
            Créer un compte
          </Link>
        </>
      }
    />
  );
}
