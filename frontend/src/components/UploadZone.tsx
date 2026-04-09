import { useCallback, useState } from "react";
import { Upload } from "lucide-react";
import { cn } from "../lib/utils";

interface Props {
  onFile: (file: File) => void;
  disabled?: boolean;
}

const ACCEPTED = ".pdf,.png,.jpg,.jpeg,.tiff,.tif,.bmp";

export default function UploadZone({ onFile, disabled }: Props) {
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) onFile(file);
    },
    [onFile]
  );

  return (
    <label
      className={cn(
        "flex flex-col items-center justify-center gap-3 w-full h-52 rounded-xl border-2 border-dashed cursor-pointer transition-colors",
        dragOver
          ? "border-blue-500 bg-blue-50 dark:bg-blue-950"
          : "border-gray-300 dark:border-gray-700 hover:border-blue-400 hover:bg-gray-50 dark:hover:bg-gray-900",
        disabled && "opacity-50 pointer-events-none"
      )}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept={ACCEPTED}
        className="sr-only"
        disabled={disabled}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }}
      />
      <Upload size={32} className="text-gray-400" />
      <div className="text-center">
        <p className="text-sm font-medium">
          Drop your lab report here or{" "}
          <span className="text-blue-500">click to browse</span>
        </p>
        <p className="text-xs text-gray-500 mt-1">PDF, PNG, JPG, TIFF up to 50 MB</p>
      </div>
    </label>
  );
}
