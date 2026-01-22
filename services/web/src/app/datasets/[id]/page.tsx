'use client';

import { useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { datasetsApi } from '@/lib/api';
import type { TestCase } from '@/types';
import { Button } from '@/components/ui/Button';
import { Input, Textarea } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { StatusBadge, Badge } from '@/components/ui/Badge';
import {
  ArrowLeft,
  Plus,
  Upload,
  Trash2,
  FileJson,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import Link from 'next/link';

export default function DatasetDetailPage() {
  const params = useParams();
  const queryClient = useQueryClient();
  const datasetId = params.id as string;
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [showAddCase, setShowAddCase] = useState(false);
  const [expandedCase, setExpandedCase] = useState<string | null>(null);
  const [rawInput, setRawInput] = useState('{}');
  const [expectedOutput, setExpectedOutput] = useState('');

  const { data: dataset, isLoading } = useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: () => datasetsApi.get(datasetId),
  });

  const { data: cases = [] } = useQuery({
    queryKey: ['dataset-cases', datasetId],
    queryFn: () => datasetsApi.getCases(datasetId),
  });

  const addCaseMutation = useMutation({
    mutationFn: () =>
      datasetsApi.addCase(datasetId, {
        raw_input: JSON.parse(rawInput),
        expected_output: expectedOutput || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset-cases', datasetId] });
      setShowAddCase(false);
      setRawInput('{}');
      setExpectedOutput('');
    },
  });

  const importCsvMutation = useMutation({
    mutationFn: (file: File) => datasetsApi.importCsv(datasetId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset-cases', datasetId] });
    },
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      importCsvMutation.mutate(file);
    }
  };

  const isValidJson = (str: string) => {
    try {
      JSON.parse(str);
      return true;
    } catch {
      return false;
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="p-6">
        <p className="text-red-500">Dataset not found</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <Link
          href="/datasets"
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft size={18} />
          Back to Datasets
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              {dataset.name}
              <StatusBadge status={dataset.dataset_type} />
            </h1>
            {dataset.description && (
              <p className="text-gray-500 mt-1">{dataset.description}</p>
            )}
            <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
              <span>{dataset.case_count} cases</span>
              {dataset.default_assertions.length > 0 && (
                <span>{dataset.default_assertions.length} default assertions</span>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.json"
              onChange={handleFileSelect}
              className="hidden"
            />
            <Button
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
              loading={importCsvMutation.isPending}
            >
              <Upload size={18} />
              Import CSV
            </Button>
            <Button onClick={() => setShowAddCase(true)}>
              <Plus size={18} />
              Add Case
            </Button>
          </div>
        </div>
      </div>

      {/* Default Assertions */}
      {dataset.default_assertions.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Default Assertions</h2>
          </div>
          <div className="p-4 flex flex-wrap gap-2">
            {dataset.default_assertions.map((assertion, i) => (
              <Badge key={i} variant="info">
                {assertion.type}
                {assertion.value ? `: ${assertion.value}` : ''}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Test Cases */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <h2 className="font-semibold">Test Cases ({cases.length})</h2>
        </div>

        {cases.length === 0 ? (
          <div className="p-12 text-center">
            <FileJson className="mx-auto text-gray-300 mb-4" size={48} />
            <p className="text-gray-500">No test cases yet</p>
            <div className="flex justify-center gap-2 mt-4">
              <Button
                variant="secondary"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={18} />
                Import CSV
              </Button>
              <Button onClick={() => setShowAddCase(true)}>
                <Plus size={18} />
                Add Case
              </Button>
            </div>
          </div>
        ) : (
          <div className="divide-y">
            {cases.map((testCase: TestCase, index: number) => (
              <div key={testCase.id} className="hover:bg-gray-50">
                <button
                  className="w-full p-4 text-left flex items-center justify-between"
                  onClick={() =>
                    setExpandedCase(
                      expandedCase === testCase.id ? null : testCase.id
                    )
                  }
                >
                  <div className="flex items-center gap-3">
                    {expandedCase === testCase.id ? (
                      <ChevronDown size={18} className="text-gray-400" />
                    ) : (
                      <ChevronRight size={18} className="text-gray-400" />
                    )}
                    <span className="text-gray-500 text-sm w-8">#{index + 1}</span>
                    <span className="font-mono text-sm truncate max-w-xl">
                      {JSON.stringify(testCase.raw_input).slice(0, 80)}...
                    </span>
                  </div>
                  {testCase.expected_output && (
                    <Badge variant="success">has expected</Badge>
                  )}
                </button>

                {expandedCase === testCase.id && (
                  <div className="px-4 pb-4 pl-16 space-y-3">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Raw Input</p>
                      <pre className="bg-gray-50 p-3 rounded text-sm font-mono overflow-x-auto">
                        {JSON.stringify(testCase.raw_input, null, 2)}
                      </pre>
                    </div>
                    {testCase.expected_output && (
                      <div>
                        <p className="text-xs text-gray-500 mb-1">
                          Expected Output
                        </p>
                        <pre className="bg-green-50 p-3 rounded text-sm">
                          {testCase.expected_output}
                        </pre>
                      </div>
                    )}
                    {testCase.assertions && testCase.assertions.length > 0 && (
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Assertions</p>
                        <div className="flex flex-wrap gap-2">
                          {testCase.assertions.map((a, i) => (
                            <Badge key={i}>
                              {a.type}
                              {a.value ? `: ${a.value}` : ''}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Case Modal */}
      <Modal
        isOpen={showAddCase}
        onClose={() => setShowAddCase(false)}
        title="Add Test Case"
        size="lg"
      >
        <div className="space-y-4">
          <div>
            <Textarea
              label="Raw Input (JSON)"
              value={rawInput}
              onChange={(e) => setRawInput(e.target.value)}
              rows={8}
              className="font-mono text-sm"
              error={!isValidJson(rawInput) ? 'Invalid JSON' : undefined}
            />
            <p className="text-xs text-gray-500 mt-1">
              Example: {`{"question": "What is 2+2?", "context": "..."}`}
            </p>
          </div>

          <Textarea
            label="Expected Output (optional)"
            placeholder="Expected response from the model"
            value={expectedOutput}
            onChange={(e) => setExpectedOutput(e.target.value)}
            rows={4}
          />

          {addCaseMutation.error && (
            <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">
              {(addCaseMutation.error as Error).message}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button variant="secondary" onClick={() => setShowAddCase(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => addCaseMutation.mutate()}
              disabled={!isValidJson(rawInput)}
              loading={addCaseMutation.isPending}
            >
              Add Case
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
