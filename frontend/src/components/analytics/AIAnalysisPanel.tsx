"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Brain, RefreshCw } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface AnalysisResult {
  summary: string;
  insights: string[];
  recommendations: string[];
  generated_at: string;
}

interface AIAnalysisPanelProps {
  analysis: AnalysisResult | null;
  loading: boolean;
  onRefresh: () => void;
}

export default function AIAnalysisPanel({ analysis, loading, onRefresh }: AIAnalysisPanelProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Brain size={16} className="text-blue-500" />
            AI Analysis
          </CardTitle>
          <Button size="sm" variant="outline" onClick={onRefresh} disabled={loading}>
            <RefreshCw size={14} className={`mr-1 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Analyzing..." : "Refresh"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading && !analysis && (
          <div className="space-y-3 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4" />
            <div className="h-3 bg-gray-100 rounded w-full" />
            <div className="h-3 bg-gray-100 rounded w-5/6" />
            <div className="h-3 bg-gray-100 rounded w-2/3" />
          </div>
        )}

        {!analysis && !loading && (
          <p className="text-sm text-gray-400 text-center py-4">
            Click "Refresh" to generate AI analysis based on current business data.
          </p>
        )}

        {analysis && (
          <div className="space-y-4">
            <div className="prose prose-sm max-w-none text-gray-700">
              <ReactMarkdown>{analysis.summary}</ReactMarkdown>
            </div>

            {analysis.insights.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-800 mb-1.5">Key Insights</h4>
                <ul className="space-y-1">
                  {analysis.insights.map((insight, i) => (
                    <li key={i} className="text-xs text-gray-600 flex gap-2">
                      <span className="text-blue-400 mt-0.5">●</span>
                      {insight}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.recommendations.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-800 mb-1.5">Recommendations</h4>
                <ul className="space-y-1">
                  {analysis.recommendations.map((rec, i) => (
                    <li key={i} className="text-xs text-gray-600 flex gap-2">
                      <span className="text-green-400 mt-0.5">→</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.generated_at && (
              <p className="text-[10px] text-gray-400">
                Generated: {new Date(analysis.generated_at).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
