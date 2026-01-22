'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { datasetsApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input, Textarea, Select } from '@/components/ui/Input';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function NewDatasetPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [datasetType, setDatasetType] = useState('evaluation');

  const createMutation = useMutation({
    mutationFn: () =>
      datasetsApi.create({
        name,
        description: description || undefined,
        dataset_type: datasetType,
      }),
    onSuccess: (data) => {
      router.push(`/datasets/${data.id}`);
    },
  });

  const isValid = name.trim();

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <Link
          href="/datasets"
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft size={18} />
          Back to Datasets
        </Link>
        <h1 className="text-2xl font-bold">Create New Dataset</h1>
        <p className="text-gray-500">Create a new test dataset</p>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <Input
          label="Name"
          placeholder="Enter dataset name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <Input
          label="Description (optional)"
          placeholder="Brief description of the dataset"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <Select
          label="Dataset Type"
          options={[
            { value: 'evaluation', label: 'Evaluation - General testing' },
            { value: 'golden', label: 'Golden - Verified/curated data' },
            { value: 'synthetic', label: 'Synthetic - Auto-generated data' },
          ]}
          value={datasetType}
          onChange={(e) => setDatasetType(e.target.value)}
        />

        {createMutation.error && (
          <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">
            {(createMutation.error as Error).message}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-4 border-t">
          <Link href="/datasets">
            <Button variant="secondary">Cancel</Button>
          </Link>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={!isValid}
            loading={createMutation.isPending}
          >
            Create Dataset
          </Button>
        </div>
      </div>
    </div>
  );
}
