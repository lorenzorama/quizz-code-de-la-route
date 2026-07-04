"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();

  return (
    <AuthForm
      title="Créer un compte"
      submitLabel="S'inscrire"
      onSubmit={async (email, password) => {
        await register(email, password);
        router.push("/");
      }}
      footer={
        <>
          Déjà inscrit ?{" "}
          <Link href="/login" className="font-semibold text-indigo-700 hover:underline">
            Se connecter
          </Link>
        </>
      }
    />
  );
}
