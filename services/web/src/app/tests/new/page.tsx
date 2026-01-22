'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { promptsApi, datasetsApi, testsApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { ArrowLeft, Check, FileText, Database, Cpu, Play } from 'lucide-react';
import Link from 'next/link';

const AVAILABLE_MODELS = [
  { id: 'meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo', name: 'Llama 3.1 8B' },
  { id: 'meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo', name: 'Llama 3.1 70B' },
  { id: 'meta-llama/Llama-3.3-70B-Instruct-Turbo', name: 'Llama 3.3 70B' },
  { id: 'mistralai/Mixtral-8x7B-Instruct-v0.1', name: 'Mixtral 8x7B' },
  { id: 'Qwen/Qwen2.5-72B-Instruct-Turbo', name: 'Qwen 2.5 72B' },
  { id: 'deepseek-ai/DeepSeek-V3', name: 'DeepSeek V3' },
];

export default function NewTestPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [selectedPrompts, setSelectedPrompts] = useState<string[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [step, setStep] = useState(1);

  const { data: prompts = [] } = useQuery({
    queryKey: ['prompts'],
    queryFn: () => promptsApi.list(),
  });

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => datasetsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      testsApi.create({
        name: name || undefined,
        prompt_ids: selectedPrompts,
        dataset_id: selectedDataset!,
        model_ids: selectedModels,
      }),
    onSuccess: async (data) => {
      // Execute immediately
      await testsApi.execute(data.id, true);
      router.push(`/tests/${data.id}`);
    },
  });

  const togglePrompt = (id: string) => {
    setSelectedPrompts((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const toggleModel = (id: string) => {
    setSelectedModels((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const canProceed = () => {
    if (step === 1) return selectedPrompts.length > 0;
    if (step === 2) return selectedDataset !== null;
    if (step === 3) return selectedModels.length > 0;
    return false;
  };

  const selectedDatasetInfo = datasets.find((d) => d.id === selectedDataset);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <Link
          href="/tests"
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft size={18} />
          Back to Tests
        </Link>
        <h1 className="text-2xl font-bold">Create New Test</h1>
        <p className="text-gray-500">Configure and run a new test</p>
      </div>

      {/* Steps */}
      <div className="flex items-center gap-4 mb-8">
        {[
          { num: 1, label: 'Prompts', icon: FileText },
          { num: 2, label: 'Dataset', icon: Database },
          { num: 3, label: 'Models', icon: Cpu },
          { num: 4, label: 'Run', icon: Play },
        ].map((s, i) => (
          <div key={s.num} className="flex items-center">
            <button
              onClick={() => s.num < step && setStep(s.num)}
              disabled={s.num > step}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                step === s.num
                  ? 'bg-blue-600 text-white'
                  : step > s.num
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-400'
              }`}
            >
              {step > s.num ? (
                <Check size={18} />
              ) : (
                <s.icon size={18} />
              )}
              <span>{s.label}</span>
            </button>
            {i < 3 && <div className="w-8 h-0.5 bg-gray-200 mx-2" />}
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        {/* Step 1: Select Prompts */}
        {step === 1 && (
          <div>
            <h2 className="font-semibold mb-4">Select Prompts</h2>
            <p className="text-sm text-gray-500 mb-4">
              Choose one or more prompts to test. Active versions will be used.
            </p>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {prompts.filter(p => p.active_version).map((prompt) => (
                <label
                  key={prompt.id}
                  className={`flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                    selectedPrompts.includes(prompt.id)
                      ? 'border-blue-500 bg-blue-50'
                      : ''
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedPrompts.includes(prompt.id)}
                    onChange={() => togglePrompt(prompt.id)}
                    className="w-5 h-5 text-blue-600 rounded"
                  />
                  <FileText className="text-blue-500" size={20} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{prompt.name}</span>
                      {prompt.active_version && (
                        <span className="text-xs text-gray-500">
                          v{prompt.active_version.major}.
                          {prompt.active_version.minor}.
                          {prompt.active_version.patch}
                        </span>
                      )}
                    </div>
                    {prompt.active_version && (
                      <div className="text-xs text-gray-500 mt-1">
                        Variables: {prompt.active_version.variables.join(', ') || 'none'}
                      </div>
                    )}
                  </div>
                </label>
              ))}
              {prompts.filter(p => p.active_version).length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  No prompts with active versions. Create a prompt first.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 2: Select Dataset */}
        {step === 2 && (
          <div>
            <h2 className="font-semibold mb-4">Select Dataset</h2>
            <p className="text-sm text-gray-500 mb-4">
              Choose a dataset containing test cases.
            </p>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {datasets.map((dataset) => (
                <label
                  key={dataset.id}
                  className={`flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                    selectedDataset === dataset.id
                      ? 'border-blue-500 bg-blue-50'
                      : ''
                  }`}
                >
                  <input
                    type="radio"
                    name="dataset"
                    checked={selectedDataset === dataset.id}
                    onChange={() => setSelectedDataset(dataset.id)}
                    className="w-5 h-5 text-blue-600"
                  />
                  <Database className="text-green-500" size={20} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{dataset.name}</span>
                      <StatusBadge status={dataset.dataset_type} />
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                      {dataset.case_count} test cases
                    </div>
                  </div>
                </label>
              ))}
              {datasets.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  No datasets available. Create a dataset first.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Select Models */}
        {step === 3 && (
          <div>
            <h2 className="font-semibold mb-4">Select Models</h2>
            <p className="text-sm text-gray-500 mb-4">
              Choose one or more models to evaluate prompts with.
            </p>
            <div className="space-y-2">
              {AVAILABLE_MODELS.map((model) => (
                <label
                  key={model.id}
                  className={`flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                    selectedModels.includes(model.id)
                      ? 'border-blue-500 bg-blue-50'
                      : ''
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedModels.includes(model.id)}
                    onChange={() => toggleModel(model.id)}
                    className="w-5 h-5 text-blue-600 rounded"
                  />
                  <Cpu className="text-purple-500" size={20} />
                  <div className="flex-1">
                    <span className="font-medium">{model.name}</span>
                    <p className="text-xs text-gray-400 font-mono">{model.id}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Review & Run */}
        {step === 4 && (
          <div>
            <h2 className="font-semibold mb-4">Review & Run</h2>

            <Input
              label="Test Name (optional)"
              placeholder="Enter a name for this test run"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mb-6"
            />

            <div className="space-y-4 mb-6">
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="text-sm font-medium text-gray-500 mb-2">
                  Prompts ({selectedPrompts.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {selectedPrompts.map((id) => {
                    const p = prompts.find((p) => p.id === id);
                    return (
                      <Badge key={id} variant="info">
                        {p?.name}
                      </Badge>
                    );
                  })}
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="text-sm font-medium text-gray-500 mb-2">
                  Dataset
                </h3>
                {selectedDatasetInfo && (
                  <div className="flex items-center gap-2">
                    <Badge variant="success">{selectedDatasetInfo.name}</Badge>
                    <span className="text-sm text-gray-500">
                      {selectedDatasetInfo.case_count} cases
                    </span>
                  </div>
                )}
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="text-sm font-medium text-gray-500 mb-2">
                  Models ({selectedModels.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {selectedModels.map((id) => {
                    const m = AVAILABLE_MODELS.find((m) => m.id === id);
                    return (
                      <Badge key={id} variant="default">
                        {m?.name}
                      </Badge>
                    );
                  })}
                </div>
              </div>

              <div className="p-4 bg-blue-50 rounded-lg">
                <h3 className="text-sm font-medium text-blue-700 mb-1">
                  Total Evaluations
                </h3>
                <p className="text-2xl font-bold text-blue-600">
                  {selectedPrompts.length *
                    selectedModels.length *
                    (selectedDatasetInfo?.case_count || 0)}
                </p>
                <p className="text-xs text-blue-500 mt-1">
                  {selectedPrompts.length} prompts × {selectedModels.length}{' '}
                  models × {selectedDatasetInfo?.case_count || 0} cases
                </p>
              </div>
            </div>

            {createMutation.error && (
              <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm mb-4">
                {(createMutation.error as Error).message}
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between pt-6 border-t mt-6">
          <Button
            variant="secondary"
            onClick={() => setStep(step - 1)}
            disabled={step === 1}
          >
            Back
          </Button>

          {step < 4 ? (
            <Button onClick={() => setStep(step + 1)} disabled={!canProceed()}>
              Continue
            </Button>
          ) : (
            <Button
              onClick={() => createMutation.mutate()}
              loading={createMutation.isPending}
            >
              <Play size={18} />
              Run Test
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
