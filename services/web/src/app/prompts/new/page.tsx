'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { promptsApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input, Textarea } from '@/components/ui/Input';
import { ArrowLeft, Variable } from 'lucide-react';
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

export default function NewPromptPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');

  const variables = extractVariables(content);

  const createMutation = useMutation({
    mutationFn: () =>
      promptsApi.create({
        name,
        description: description || undefined,
        content,
        tags: tags ? tags.split(',').map((t) => t.trim()) : undefined,
      }),
    onSuccess: (data) => {
      router.push(`/prompts/${data.id}`);
    },
  });

  const isValid = name.trim() && content.trim();

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <Link
          href="/prompts"
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft size={18} />
          Back to Prompts
        </Link>
        <h1 className="text-2xl font-bold">Create New Prompt</h1>
        <p className="text-gray-500">Create a new prompt template</p>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <Input
          label="Name"
          placeholder="Enter prompt name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <Input
          label="Description (optional)"
          placeholder="Brief description of the prompt"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <div>
          <Textarea
            label="Prompt Content"
            placeholder="Enter your prompt template. Use {{variable}} for variables."
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={12}
            className="font-mono text-sm"
          />
          {variables.length > 0 && (
            <div className="mt-2 flex items-center gap-2">
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
        </div>

        <Input
          label="Tags (optional)"
          placeholder="Comma-separated tags (e.g., qa, rag, translation)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />

        {createMutation.error && (
          <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">
            {(createMutation.error as Error).message}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-4 border-t">
          <Link href="/prompts">
            <Button variant="secondary">Cancel</Button>
          </Link>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={!isValid}
            loading={createMutation.isPending}
          >
            Create Prompt
          </Button>
        </div>
      </div>
    </div>
  );
}
