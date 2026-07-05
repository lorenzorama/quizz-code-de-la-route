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
        className="w-full rounded-xl border border-slate-200 bg-black"
      />
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt="Illustration de la question"
      className="w-full rounded-xl border border-slate-200 object-cover"
    />
  );
}
