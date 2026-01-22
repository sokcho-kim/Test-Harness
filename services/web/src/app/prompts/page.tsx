'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { promptsApi } from '@/lib/api';
import Link from 'next/link';
import { Plus, Search, FileText, MoreVertical, Trash2, Edit } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { StatusBadge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';

export default function PromptsPage() {
  const [search, setSearch] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: prompts = [], isLoading } = useQuery({
    queryKey: ['prompts'],
    queryFn: () => promptsApi.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => promptsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      setDeleteId(null);
    },
  });

  const filtered = prompts.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.description?.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Prompts</h1>
          <p className="text-gray-500">Manage your prompt templates</p>
        </div>
        <Link href="/prompts/new">
          <Button>
            <Plus size={18} />
            New Prompt
          </Button>
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              size={18}
            />
            <Input
              placeholder="Search prompts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="mx-auto text-gray-300 mb-4" size={48} />
            <p className="text-gray-500">No prompts found</p>
            <Link href="/prompts/new">
              <Button variant="secondary" className="mt-4">
                Create your first prompt
              </Button>
            </Link>
          </div>
        ) : (
          <div className="divide-y">
            {filtered.map((prompt) => (
              <div
                key={prompt.id}
                className="p-4 hover:bg-gray-50 flex items-center justify-between"
              >
                <Link href={`/prompts/${prompt.id}`} className="flex-1">
                  <div className="flex items-center gap-3">
                    <FileText className="text-blue-500" size={20} />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{prompt.name}</span>
                        {prompt.active_version && (
                          <span className="text-xs text-gray-500">
                            v{prompt.active_version.major}.
                            {prompt.active_version.minor}.
                            {prompt.active_version.patch}
                          </span>
                        )}
                        {prompt.active_version && (
                          <StatusBadge status={prompt.active_version.status} />
                        )}
                      </div>
                      {prompt.description && (
                        <p className="text-sm text-gray-500 mt-0.5">
                          {prompt.description}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        {prompt.tags?.map((tag) => (
                          <span
                            key={tag}
                            className="text-xs bg-gray-100 px-2 py-0.5 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                        <span className="text-xs text-gray-400">
                          {prompt.version_count} version(s)
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>

                <div className="flex items-center gap-2">
                  <Link href={`/prompts/${prompt.id}`}>
                    <Button variant="ghost" size="sm">
                      <Edit size={16} />
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDeleteId(prompt.id)}
                  >
                    <Trash2 size={16} className="text-red-500" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="Delete Prompt"
        size="sm"
      >
        <p className="text-gray-600 mb-4">
          Are you sure you want to delete this prompt? This will also delete all
          versions. This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            loading={deleteMutation.isPending}
            onClick={() => deleteId && deleteMutation.mutate(deleteId)}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}
