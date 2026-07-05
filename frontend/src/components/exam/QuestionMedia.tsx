import { mediaUrl } from "@/lib/api";

export function QuestionMedia({
  mediaType,
  mediaPath,
  fill = false,
}: {
  mediaType: string;
  mediaPath: string | null;
  /**
   * When true, the media fills its (bounded-height) flex parent — used by the
   * viewport-fit quiz runners. When false (default), it keeps a natural size
   * capped at 50vh, for scrollable contexts like the exam review list.
   */
  fill?: boolean;
}) {
  if (!mediaPath || mediaType === "none") return null;
  const src = mediaUrl(mediaPath);
  const sizing = fill
    ? "max-h-full max-w-full"
    : "max-h-[50vh] w-auto max-w-full";
  const className = `mx-auto ${sizing} rounded-xl border border-slate-200 object-contain`;

  if (mediaType === "video") {
    return <video controls src={src} className={`${className} bg-black`} />;
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt="Illustration de la question" className={className} />
  );
}
