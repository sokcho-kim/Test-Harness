'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { promptsApi } from '@/lib/api';
import type { PromptVersion } from '@/types';
import { Button } from '@/components/ui/Button';
import { Input, Textarea, Select } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { StatusBadge, Badge } from '@/components/ui/Badge';
import {
  ArrowLeft,
  Plus,
  Check,
  Clock,
  Variable,
  GitBranch,
} from 'lucide-react';
import Link from 'next/link';

function extractVariables(content: string): string[] {
  const regex = /\{\{(\w+)\}\}/g;
  const matches = new Set<string>();
  let match;
  while ((match = regex.exec(content)) !== null) {
    matches.add(match[1]);
  }
  return Array.from(matches);
}

export default function PromptDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const promptId = params.id as string;

  const [showNewVersion, setShowNewVersion] = useState(false);
  const [newContent, setNewContent] = useState('');
  const [changeType, setChangeType] = useState<'major' | 'minor' | 'patch'>('minor');
  const [changeNote, setChangeNote] = useState('');

  const { data: prompt, isLoading } = useQuery({
    queryKey: ['prompt', promptId],
    queryFn: () => promptsApi.get(promptId),
  });

  const { data: versions = [] } = useQuery({
    queryKey: ['prompt-versions', promptId],
    queryFn: () => promptsApi.getVersions(promptId),
  });

  const createVersionMutation = useMutation({
    mutationFn: () =>
      promptsApi.createVersion(promptId, {
        content: newContent,
        change_type: changeType,
        change_note: changeNote || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt', promptId] });
      queryClient.invalidateQueries({ queryKey: ['prompt-versions', promptId] });
      setShowNewVersion(false);
      setNewContent('');
      setChangeNote('');
    },
  });

  const activateMutation = useMutation({
    mutationFn: (versionId: string) =>
      promptsApi.activateVersion(promptId, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt', promptId] });
      queryClient.invalidateQueries({ queryKey: ['prompt-versions', promptId] });
    },
  });

  const openNewVersionModal = () => {
    const latestVersion = versions[0];
    setNewContent(latestVersion?.content || '');
    setShowNewVersion(true);
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!prompt) {
    return (
      <div className="p-6">
        <p className="text-red-500">Prompt not found</p>
      </div>
    );
  }

  const variables = prompt.active_version
    ? extractVariables(prompt.active_version.content)
    : [];

  return (
    <div className="p-6">
      <div className="mb-6">
        <Link
          href="/prompts"
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft size={18} />
          Back to Prompts
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              {prompt.name}
              {prompt.active_version && (
                <span className="text-lg text-gray-500 font-normal">
                  v{prompt.active_version.major}.{prompt.active_version.minor}.
                  {prompt.active_version.patch}
                </span>
              )}
            </h1>
            {prompt.description && (
              <p className="text-gray-500 mt-1">{prompt.description}</p>
            )}
            <div className="flex items-center gap-2 mt-2">
              {prompt.tags?.map((tag) => (
                <Badge key={tag}>{tag}</Badge>
              ))}
            </div>
          </div>
          <Button onClick={openNewVersionModal}>
            <Plus size={18} />
            New Version
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Version */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="font-semibold">Active Version</h2>
              {prompt.active_version && (
                <StatusBadge status={prompt.active_version.status} />
              )}
            </div>
            <div className="p-4">
              {prompt.active_version ? (
                <>
                  <pre className="bg-gray-50 p-4 rounded-lg text-sm font-mono whitespace-pre-wrap overflow-x-auto">
                    {prompt.active_version.content}
                  </pre>
                  {variables.length > 0 && (
                    <div className="mt-4 flex items-center gap-2">
                      <Variable size={16} className="text-gray-400" />
                      <span className="text-sm text-gray-500">Variables:</span>
                      {variables.map((v) => (
                        <span
                          key={v}
                          className="text-sm bg-blue-100 text-blue-800 px-2 py-0.5 rounded"
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-gray-500">No active version</p>
              )}
            </div>
          </div>
        </div>

        {/* Version History */}
        <div>
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b flex items-center gap-2">
              <GitBranch size={18} className="text-gray-400" />
              <h2 className="font-semibold">Version History</h2>
            </div>
            <div className="divide-y max-h-[600px] overflow-y-auto">
              {versions.map((version: PromptVersion) => (
                <div
                  key={version.id}
                  className={`p-4 ${
                    version.is_active ? 'bg-blue-50' : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        v{version.major}.{version.minor}.{version.patch}
                      </span>
                      {version.is_active && (
                        <Check size={16} className="text-green-500" />
                      )}
                    </div>
                    <StatusBadge status={version.status} />
                  </div>
                  {version.change_note && (
                    <p className="text-sm text-gray-600 mb-2">
                      {version.change_note}
                    </p>
                  )}
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <Clock size={12} />
                      {new Date(version.created_at).toLocaleString()}
                    </span>
                    {!version.is_active && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => activateMutation.mutate(version.id)}
                        loading={activateMutation.isPending}
                      >
                        Activate
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* New Version Modal */}
      <Modal
        isOpen={showNewVersion}
        onClose={() => setShowNewVersion(false)}
        title="Create New Version"
        size="lg"
      >
        <div className="space-y-4">
          <Select
            label="Change Type"
            options={[
              { value: 'patch', label: 'Patch (bug fix, typo)' },
              { value: 'minor', label: 'Minor (small changes)' },
              { value: 'major', label: 'Major (breaking changes)' },
            ]}
            value={changeType}
            onChange={(e) =>
              setChangeType(e.target.value as 'major' | 'minor' | 'patch')
            }
          />

          <Textarea
            label="Prompt Content"
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            rows={12}
            className="font-mono text-sm"
          />

          {extractVariables(newContent).length > 0 && (
            <div className="flex items-center gap-2">
              <Variable size={16} className="text-gray-400" />
              <span className="text-sm text-gray-500">Variables:</span>
              {extractVariables(newContent).map((v) => (
                <span
                  key={v}
                  className="text-sm bg-blue-100 text-blue-800 px-2 py-0.5 rounded"
                >
                  {v}
                </span>
              ))}
            </div>
          )}

          <Input
            label="Change Note (optional)"
            placeholder="Describe what changed"
            value={changeNote}
            onChange={(e) => setChangeNote(e.target.value)}
          />

          {createVersionMutation.error && (
            <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">
              {(createVersionMutation.error as Error).message}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button variant="secondary" onClick={() => setShowNewVersion(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => createVersionMutation.mutate()}
              disabled={!newContent.trim()}
              loading={createVersionMutation.isPending}
            >
              Create Version
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
