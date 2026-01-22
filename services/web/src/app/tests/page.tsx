'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { testsApi } from '@/lib/api';
import Link from 'next/link';
import { Plus, Search, Play, Trash2, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input, Select } from '@/components/ui/Input';
import { StatusBadge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';

export default function TestsPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: tests = [], isLoading } = useQuery({
    queryKey: ['tests', statusFilter],
    queryFn: () =>
      testsApi.list(statusFilter === 'all' ? undefined : statusFilter),
    refetchInterval: 5000, // Poll for updates
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => testsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tests'] });
      setDeleteId(null);
    },
  });

  const filtered = tests.filter(
    (t) =>
      (t.name?.toLowerCase().includes(search.toLowerCase()) ||
        t.id.toLowerCase().includes(search.toLowerCase()))
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="text-green-500" size={18} />;
      case 'failed':
        return <XCircle className="text-red-500" size={18} />;
      case 'running':
        return <Loader2 className="text-blue-500 animate-spin" size={18} />;
      default:
        return <Clock className="text-yellow-500" size={18} />;
    }
  };

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
          <h1 className="text-2xl font-bold">Tests</h1>
          <p className="text-gray-500">Run and manage test executions</p>
        </div>
        <Link href="/tests/new">
          <Button>
            <Plus size={18} />
            New Test
          </Button>
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b flex gap-4">
          <div className="flex-1 relative">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              size={18}
            />
            <Input
              placeholder="Search tests..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select
            options={[
              { value: 'all', label: 'All Status' },
              { value: 'pending', label: 'Pending' },
              { value: 'running', label: 'Running' },
              { value: 'completed', label: 'Completed' },
              { value: 'failed', label: 'Failed' },
            ]}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-40"
          />
        </div>

        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <Play className="mx-auto text-gray-300 mb-4" size={48} />
            <p className="text-gray-500">No tests found</p>
            <Link href="/tests/new">
              <Button variant="secondary" className="mt-4">
                Run your first test
              </Button>
            </Link>
          </div>
        ) : (
          <div className="divide-y">
            {filtered.map((test) => (
              <div
                key={test.id}
                className="p-4 hover:bg-gray-50 flex items-center justify-between"
              >
                <Link href={`/tests/${test.id}`} className="flex-1">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(test.status)}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {test.name || `Run ${test.id.slice(0, 8)}`}
                        </span>
                        <StatusBadge status={test.status} />
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                        <span>{test.prompt_ids.length} prompt(s)</span>
                        <span>{test.model_ids.length} model(s)</span>
                        <span>{test.total_cases} cases</span>
                      </div>
                    </div>
                  </div>
                </Link>

                <div className="flex items-center gap-4">
                  {test.status === 'completed' && (
                    <div className="text-right">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-green-600 font-medium">
                          {test.passed_cases} passed
                        </span>
                        <span className="text-gray-400">/</span>
                        <span className="text-red-600 font-medium">
                          {test.failed_cases} failed
                        </span>
                      </div>
                      <div className="text-xs text-gray-400">
                        {Math.round(
                          (test.passed_cases / test.total_cases) * 100
                        )}
                        % success
                      </div>
                    </div>
                  )}

                  {test.status === 'running' && (
                    <div className="text-right">
                      <div className="text-sm text-gray-500">
                        {Math.round(test.progress)}%
                      </div>
                      <div className="w-20 h-1.5 bg-gray-200 rounded-full mt-1">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{ width: `${test.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <div className="text-xs text-gray-400">
                    {new Date(test.created_at).toLocaleString()}
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.preventDefault();
                      setDeleteId(test.id);
                    }}
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
        title="Delete Test"
        size="sm"
      >
        <p className="text-gray-600 mb-4">
          Are you sure you want to delete this test run? All results will be
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
