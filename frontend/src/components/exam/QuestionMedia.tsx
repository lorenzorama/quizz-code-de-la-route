import { mediaUrl } from "@/lib/api";

export function QuestionMedia({
  mediaType,
  mediaPath,
}: {
  mediaType: string;
  mediaPath: string | null;
}) {
  if (!mediaPath || mediaType === "none") return null;
  const src = mediaUrl(mediaPath);

  if (mediaType === "video") {
    return (
      <video
        controls
        src={src}
        className="mx-auto max-h-[50vh] w-auto max-w-full rounded-xl border border-slate-200 bg-black object-contain"
      />
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt="Illustration de la question"
      className="mx-auto max-h-[50vh] w-auto max-w-full rounded-xl border border-slate-200 object-contain"
    />
  );
}
