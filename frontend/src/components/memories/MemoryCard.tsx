"use client";
import { Card, CardContent } from "@/components/ui/card";
import { Trash2 } from "lucide-react";

export interface MemoryData {
  id: string;
  memory_type: string;
  title: string;
  content: string;
  importance: number;
  access_count: number;
  entity_type?: string;
  created_at: string;
}

interface Props {
  memory: MemoryData;
  onDelete: (id: string) => void;
}

const typeColors: Record<string, string> = {
  long_term: "bg-blue-50 text-blue-600",
  episodic: "bg-amber-50 text-amber-600",
  semantic: "bg-purple-50 text-purple-600",
};

export default function MemoryCard({ memory, onDelete }: Props) {
  return (
    <Card className="hover:shadow-sm transition-shadow group">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${typeColors[memory.memory_type] || "bg-gray-50 text-gray-500"}`}>
                {memory.memory_type}
              </span>
              {memory.entity_type && (
                <span className="text-[10px] text-gray-400">{memory.entity_type}</span>
              )}
              <span className="text-[10px] text-gray-400">★ {memory.importance}/10</span>
              <span className="text-[10px] text-gray-400">Used {memory.access_count}×</span>
            </div>
            <h3 className="text-sm font-medium text-gray-800">{memory.title}</h3>
            <p className="text-xs text-gray-500 mt-1 line-clamp-3">{memory.content}</p>
            <p className="text-[10px] text-gray-400 mt-2">
              {new Date(memory.created_at).toLocaleDateString("zh-CN", { year: "numeric", month: "short", day: "numeric" })}
            </p>
          </div>
          <button
            onClick={() => onDelete(memory.id)}
            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 rounded transition-all flex-shrink-0"
          >
            <Trash2 size={14} className="text-red-400" />
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
