"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

export function QuitToHome({ message }: { message: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button type="button" variant="ghost" onClick={() => setOpen(true)}>
        Quitter
      </Button>
      <ConfirmDialog
        open={open}
        title="Quitter ?"
        message={message}
        confirmLabel="Oui, quitter"
        cancelLabel="Annuler"
        onCancel={() => setOpen(false)}
        onConfirm={() => router.push("/")}
      />
    </>
  );
}
