'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { datasetsApi } from '@/lib/api';
import Link from 'next/link';
import { Plus, Search, Database, Trash2, Edit } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { StatusBadge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';

export default function DatasetsPage() {
  const [search, setSearch] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: datasets = [], isLoading } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => datasetsApi.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => datasetsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      setDeleteId(null);
    },
  });

  const filtered = datasets.filter(
    (d) =>
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.description?.toLowerCase().includes(search.toLowerCase())
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
          <h1 className="text-2xl font-bold">Datasets</h1>
          <p className="text-gray-500">Manage your test datasets</p>
        </div>
        <Link href="/datasets/new">
          <Button>
            <Plus size={18} />
            New Dataset
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
              placeholder="Search datasets..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <Database className="mx-auto text-gray-300 mb-4" size={48} />
            <p className="text-gray-500">No datasets found</p>
            <Link href="/datasets/new">
              <Button variant="secondary" className="mt-4">
                Create your first dataset
              </Button>
            </Link>
          </div>
        ) : (
          <div className="divide-y">
            {filtered.map((dataset) => (
              <div
                key={dataset.id}
                className="p-4 hover:bg-gray-50 flex items-center justify-between"
              >
                <Link href={`/datasets/${dataset.id}`} className="flex-1">
                  <div className="flex items-center gap-3">
                    <Database className="text-green-500" size={20} />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{dataset.name}</span>
                        <StatusBadge status={dataset.dataset_type} />
                      </div>
                      {dataset.description && (
                        <p className="text-sm text-gray-500 mt-0.5">
                          {dataset.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                        <span>{dataset.case_count} cases</span>
                        {dataset.default_assertions.length > 0 && (
                          <span>
                            {dataset.default_assertions.length} default assertions
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>

                <div className="flex items-center gap-2">
                  <Link href={`/datasets/${dataset.id}`}>
                    <Button variant="ghost" size="sm">
                      <Edit size={16} />
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDeleteId(dataset.id)}
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
        title="Delete Dataset"
        size="sm"
      >
        <p className="text-gray-600 mb-4">
          Are you sure you want to delete this dataset? All test cases will be
          deleted. This action cannot be undone.
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
