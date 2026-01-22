'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { testsApi, promptsApi } from '@/lib/api';
import type { TestRun, TestResult } from '@/types';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Input';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  BarChart3,
} from 'lucide-react';
import Link from 'next/link';

export default function ComparePage() {
  const [selectedTestId, setSelectedTestId] = useState<string>('');

  const { data: tests = [] } = useQuery({
    queryKey: ['tests'],
    queryFn: () => testsApi.list('completed'),
  });

  const { data: prompts = [] } = useQuery({
    queryKey: ['prompts'],
    queryFn: () => promptsApi.list(),
  });

  const { data: resultsData } = useQuery({
    queryKey: ['test-results', selectedTestId],
    queryFn: () => testsApi.getResults(selectedTestId, 1, 500),
    enabled: !!selectedTestId,
  });

  const selectedTest = tests.find((t) => t.id === selectedTestId);
  const results = resultsData?.items || [];

  // Group results by test case
  const groupedByCase = results.reduce((acc, result) => {
    const caseId = result.test_case_id;
    if (!acc[caseId]) {
      acc[caseId] = [];
    }
    acc[caseId].push(result);
    return acc;
  }, {} as Record<string, TestResult[]>);

  // Calculate stats per model
  const modelStats = selectedTest?.model_ids.reduce((acc, modelId) => {
    const modelResults = results.filter((r) => r.model_id === modelId);
    const passed = modelResults.filter((r) => r.passed).length;
    const avgLatency =
      modelResults.length > 0
        ? Math.round(
            modelResults.reduce((sum, r) => sum + r.latency_ms, 0) /
              modelResults.length
          )
        : 0;
    acc[modelId] = {
      total: modelResults.length,
      passed,
      failed: modelResults.length - passed,
      passRate: modelResults.length > 0 ? Math.round((passed / modelResults.length) * 100) : 0,
      avgLatency,
    };
    return acc;
  }, {} as Record<string, { total: number; passed: number; failed: number; passRate: number; avgLatency: number }>) || {};

  // Calculate stats per prompt
  const promptStats = selectedTest?.prompt_ids.reduce((acc, promptId) => {
    const promptResults = results.filter((r) => r.prompt_id === promptId);
    const passed = promptResults.filter((r) => r.passed).length;
    acc[promptId] = {
      total: promptResults.length,
      passed,
      failed: promptResults.length - passed,
      passRate: promptResults.length > 0 ? Math.round((passed / promptResults.length) * 100) : 0,
    };
    return acc;
  }, {} as Record<string, { total: number; passed: number; failed: number; passRate: number }>) || {};

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-3">
          <BarChart3 className="text-purple-500" />
          Compare Results
        </h1>
        <p className="text-gray-500">
          Compare performance across prompts and models
        </p>
      </div>

      {/* Test Selection */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <Select
          label="Select a completed test to compare"
          options={[
            { value: '', label: 'Select a test...' },
            ...tests.map((t) => ({
              value: t.id,
              label: `${t.name || `Test ${t.id.slice(0, 8)}`} (${t.total_cases} cases)`,
            })),
          ]}
          value={selectedTestId}
          onChange={(e) => setSelectedTestId(e.target.value)}
        />
      </div>

      {selectedTest && (
        <>
          {/* Model Comparison */}
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="p-4 border-b">
              <h2 className="font-semibold">Model Comparison</h2>
            </div>
            <div className="p-4">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-3 text-sm font-medium text-gray-500">
                        Model
                      </th>
                      <th className="text-center p-3 text-sm font-medium text-gray-500">
                        Total
                      </th>
                      <th className="text-center p-3 text-sm font-medium text-gray-500">
                        Passed
                      </th>
                      <th className="text-center p-3 text-sm font-medium text-gray-500">
                        Failed
                      </th>
                      <th className="text-center p-3 text-sm font-medium text-gray-500">
                        Pass Rate
                      </th>
                      <th className="text-center p-3 text-sm font-medium text-gray-500">
                        Avg Latency
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedTest.model_ids.map((modelId) => {
                      const stats = modelStats[modelId];
                      return (
                        <tr key={modelId} className="border-b hover:bg-gray-50">
                          <td className="p-3">
                            <span className="font-medium">
                              {modelId.split('/').pop()}
                            </span>
                          </td>
                          <td className="p-3 text-center">{stats?.total || 0}</td>
                          <td className="p-3 text-center text-green-600 font-medium">
                            {stats?.passed || 0}
                          </td>
                          <td className="p-3 text-center text-red-600 font-medium">
                            {stats?.failed || 0}
                          </td>
                          <td className="p-3 text-center">
                            <div className="flex items-center justify-center gap-2">
                              <div className="w-20 h-2 bg-gray-200 rounded-full">
                                <div
                                  className={`h-full rounded-full ${
                                    (stats?.passRate || 0) >= 80
                                      ? 'bg-green-500'
                                      : (stats?.passRate || 0) >= 50
                                      ? 'bg-yellow-500'
                                      : 'bg-red-500'
                                  }`}
                                  style={{ width: `${stats?.passRate || 0}%` }}
                                />
                              </div>
                              <span className="text-sm font-medium">
                                {stats?.passRate || 0}%
                              </span>
                            </div>
                          </td>
                          <td className="p-3 text-center text-gray-500">
                            {stats?.avgLatency || 0}ms
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Prompt Comparison */}
          {selectedTest.prompt_ids.length > 1 && (
            <div className="bg-white rounded-lg shadow mb-6">
              <div className="p-4 border-b">
                <h2 className="font-semibold">Prompt Comparison</h2>
              </div>
              <div className="p-4">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-3 text-sm font-medium text-gray-500">
                          Prompt
                        </th>
                        <th className="text-center p-3 text-sm font-medium text-gray-500">
                          Total
                        </th>
                        <th className="text-center p-3 text-sm font-medium text-gray-500">
                          Passed
                        </th>
                        <th className="text-center p-3 text-sm font-medium text-gray-500">
                          Failed
                        </th>
                        <th className="text-center p-3 text-sm font-medium text-gray-500">
                          Pass Rate
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedTest.prompt_ids.map((promptId) => {
                        const prompt = prompts.find((p) => p.id === promptId);
                        const stats = promptStats[promptId];
                        return (
                          <tr
                            key={promptId}
                            className="border-b hover:bg-gray-50"
                          >
                            <td className="p-3">
                              <span className="font-medium">
                                {prompt?.name || promptId.slice(0, 8)}
                              </span>
                            </td>
                            <td className="p-3 text-center">
                              {stats?.total || 0}
                            </td>
                            <td className="p-3 text-center text-green-600 font-medium">
                              {stats?.passed || 0}
                            </td>
                            <td className="p-3 text-center text-red-600 font-medium">
                              {stats?.failed || 0}
                            </td>
                            <td className="p-3 text-center">
                              <div className="flex items-center justify-center gap-2">
                                <div className="w-20 h-2 bg-gray-200 rounded-full">
                                  <div
                                    className={`h-full rounded-full ${
                                      (stats?.passRate || 0) >= 80
                                        ? 'bg-green-500'
                                        : (stats?.passRate || 0) >= 50
                                        ? 'bg-yellow-500'
                                        : 'bg-red-500'
                                    }`}
                                    style={{ width: `${stats?.passRate || 0}%` }}
                                  />
                                </div>
                                <span className="text-sm font-medium">
                                  {stats?.passRate || 0}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Side-by-Side Results */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h2 className="font-semibold">
                Side-by-Side Results ({Object.keys(groupedByCase).length} cases)
              </h2>
            </div>
            <div className="divide-y max-h-[600px] overflow-y-auto">
              {Object.entries(groupedByCase).map(([caseId, caseResults], idx) => (
                <div key={caseId} className="p-4">
                  <div className="text-sm text-gray-500 mb-3">
                    Case #{idx + 1}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {caseResults.map((result) => {
                      const prompt = prompts.find(
                        (p) => p.id === result.prompt_id
                      );
                      return (
                        <div
                          key={result.id}
                          className={`p-3 rounded-lg border ${
                            result.passed
                              ? 'border-green-200 bg-green-50'
                              : 'border-red-200 bg-red-50'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              {result.passed ? (
                                <CheckCircle
                                  className="text-green-500"
                                  size={16}
                                />
                              ) : (
                                <XCircle className="text-red-500" size={16} />
                              )}
                              <span className="text-xs font-medium">
                                {prompt?.name || result.prompt_id.slice(0, 8)}
                              </span>
                            </div>
                            <Badge variant="default">
                              {result.model_id.split('/').pop()}
                            </Badge>
                          </div>
                          <pre className="text-xs bg-white p-2 rounded border overflow-x-auto max-h-24">
                            {result.output.slice(0, 200)}
                            {result.output.length > 200 ? '...' : ''}
                          </pre>
                          <div className="flex items-center justify-between mt-2 text-xs text-gray-400">
                            <span>{result.latency_ms}ms</span>
                            <div className="flex gap-1">
                              {result.assertion_results.map((ar, i) => (
                                <span
                                  key={i}
                                  className={`w-2 h-2 rounded-full ${
                                    ar.passed ? 'bg-green-500' : 'bg-red-500'
                                  }`}
                                  title={ar.type}
                                />
                              ))}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {!selectedTestId && tests.length === 0 && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <BarChart3 className="mx-auto text-gray-300 mb-4" size={48} />
          <p className="text-gray-500">No completed tests to compare</p>
          <Link href="/tests/new">
            <Button variant="secondary" className="mt-4">
              Run a test first
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
