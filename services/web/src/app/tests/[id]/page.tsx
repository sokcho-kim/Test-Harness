'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { testsApi, promptsApi } from '@/lib/api';
import type { TestResult } from '@/types';
import { Button } from '@/components/ui/Button';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Filter,
} from 'lucide-react';
import Link from 'next/link';

export default function TestDetailPage() {
  const params = useParams();
  const testId = params.id as string;
  const [expandedResult, setExpandedResult] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'passed' | 'failed'>('all');

  const { data: test, isLoading } = useQuery({
    queryKey: ['test', testId],
    queryFn: () => testsApi.get(testId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' || status === 'pending' ? 2000 : false;
    },
  });

  const { data: resultsData } = useQuery({
    queryKey: ['test-results', testId],
    queryFn: () => testsApi.getResults(testId, 1, 100),
    enabled: !!test && test.status === 'completed',
  });

  const { data: prompts = [] } = useQuery({
    queryKey: ['prompts'],
    queryFn: () => promptsApi.list(),
  });

  const results = resultsData?.items || [];

  const filteredResults = results.filter((r) => {
    if (filter === 'passed') return r.passed;
    if (filter === 'failed') return !r.passed;
    return true;
  });

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!test) {
    return (
      <div className="p-6">
        <p className="text-red-500">Test not found</p>
      </div>
    );
  }

  const passRate = test.total_cases > 0
    ? Math.round((test.passed_cases / test.total_cases) * 100)
    : 0;

  return (
    <div className="p-6">
      <div className="mb-6">
        <Link
          href="/tests"
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft size={18} />
          Back to Tests
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              {test.name || `Test ${test.id.slice(0, 8)}`}
              <StatusBadge status={test.status} />
            </h1>
            <p className="text-gray-500 mt-1">
              Created {new Date(test.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Total Cases</p>
          <p className="text-2xl font-bold">{test.total_cases}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Passed</p>
          <p className="text-2xl font-bold text-green-600">{test.passed_cases}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Failed</p>
          <p className="text-2xl font-bold text-red-600">{test.failed_cases}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Pass Rate</p>
          <p className={`text-2xl font-bold ${passRate >= 80 ? 'text-green-600' : passRate >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
            {passRate}%
          </p>
        </div>
      </div>

      {/* Progress for running tests */}
      {(test.status === 'running' || test.status === 'pending') && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">Progress</span>
            <span className="text-sm font-medium">{Math.round(test.progress)}%</span>
          </div>
          <div className="w-full h-3 bg-gray-200 rounded-full">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${test.progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-2">
            {test.status === 'pending' ? 'Waiting to start...' : 'Running evaluations...'}
          </p>
        </div>
      )}

      {/* Configuration */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-4 border-b">
          <h2 className="font-semibold">Configuration</h2>
        </div>
        <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-500 mb-2">Prompts</p>
            <div className="flex flex-wrap gap-2">
              {test.prompt_ids.map((id) => {
                const p = prompts.find((p) => p.id === id);
                return (
                  <Badge key={id} variant="info">
                    {p?.name || id.slice(0, 8)}
                  </Badge>
                );
              })}
            </div>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-2">Models</p>
            <div className="flex flex-wrap gap-2">
              {test.model_ids.map((id) => (
                <Badge key={id}>{id.split('/').pop()}</Badge>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-2">Mapping</p>
            <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
              {JSON.stringify(test.resolved_mapping, null, 2)}
            </pre>
          </div>
        </div>
      </div>

      {/* Results */}
      {test.status === 'completed' && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b flex items-center justify-between">
            <h2 className="font-semibold">Results ({filteredResults.length})</h2>
            <div className="flex items-center gap-2">
              <Filter size={16} className="text-gray-400" />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                className="text-sm border rounded px-2 py-1"
              >
                <option value="all">All</option>
                <option value="passed">Passed</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>

          <div className="divide-y max-h-[600px] overflow-y-auto">
            {filteredResults.map((result: TestResult, index: number) => (
              <div key={result.id} className="hover:bg-gray-50">
                <button
                  className="w-full p-4 text-left flex items-center justify-between"
                  onClick={() =>
                    setExpandedResult(
                      expandedResult === result.id ? null : result.id
                    )
                  }
                >
                  <div className="flex items-center gap-3">
                    {expandedResult === result.id ? (
                      <ChevronDown size={18} className="text-gray-400" />
                    ) : (
                      <ChevronRight size={18} className="text-gray-400" />
                    )}
                    {result.passed ? (
                      <CheckCircle className="text-green-500" size={18} />
                    ) : (
                      <XCircle className="text-red-500" size={18} />
                    )}
                    <span className="text-gray-500 text-sm w-8">#{index + 1}</span>
                    <div>
                      <span className="font-medium">
                        {prompts.find((p) => p.id === result.prompt_id)?.name ||
                          result.prompt_id.slice(0, 8)}
                      </span>
                      <span className="text-gray-400 mx-2">×</span>
                      <span className="text-sm text-gray-500">
                        {result.model_id.split('/').pop()}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex gap-1">
                      {result.assertion_results.map((ar, i) => (
                        <span
                          key={i}
                          className={`w-2 h-2 rounded-full ${
                            ar.passed ? 'bg-green-500' : 'bg-red-500'
                          }`}
                          title={`${ar.type}: ${ar.passed ? 'passed' : 'failed'}`}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-gray-400">
                      {result.latency_ms}ms
                    </span>
                  </div>
                </button>

                {expandedResult === result.id && (
                  <div className="px-4 pb-4 pl-16 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Input</p>
                        <pre className="bg-gray-50 p-3 rounded text-sm font-mono overflow-x-auto max-h-40">
                          {result.input_rendered}
                        </pre>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Output</p>
                        <pre className="bg-gray-50 p-3 rounded text-sm overflow-x-auto max-h-40">
                          {result.output}
                        </pre>
                      </div>
                    </div>

                    <div>
                      <p className="text-xs text-gray-500 mb-2">Assertions</p>
                      <div className="space-y-2">
                        {result.assertion_results.map((ar, i) => (
                          <div
                            key={i}
                            className={`flex items-center gap-2 p-2 rounded ${
                              ar.passed ? 'bg-green-50' : 'bg-red-50'
                            }`}
                          >
                            {ar.passed ? (
                              <CheckCircle
                                className="text-green-500"
                                size={16}
                              />
                            ) : (
                              <XCircle className="text-red-500" size={16} />
                            )}
                            <span className="font-medium text-sm">
                              {ar.type}
                            </span>
                            {ar.value && (
                              <span className="text-sm text-gray-500">
                                : {ar.value}
                              </span>
                            )}
                            {ar.message && (
                              <span className="text-xs text-gray-400 ml-auto">
                                {ar.message}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    {result.error && (
                      <div className="p-3 bg-red-50 text-red-600 rounded text-sm">
                        {result.error}
                      </div>
                    )}

                    <div className="flex gap-4 text-xs text-gray-400">
                      <span>Latency: {result.latency_ms}ms</span>
                      {result.token_usage && (
                        <span>
                          Tokens: {result.token_usage.total_tokens} (
                          {result.token_usage.prompt_tokens} +{' '}
                          {result.token_usage.completion_tokens})
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
