'use client';

import { useQuery } from '@tanstack/react-query';
import { promptsApi, datasetsApi, testsApi } from '@/lib/api';
import Link from 'next/link';
import { FileText, Database, Play, CheckCircle, XCircle, Clock } from 'lucide-react';

function StatCard({
  title,
  value,
  icon: Icon,
  href,
  color,
}: {
  title: string;
  value: number | string;
  icon: any;
  href: string;
  color: string;
}) {
  return (
    <Link
      href={href}
      className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-3xl font-bold mt-1">{value}</p>
        </div>
        <div className={`p-3 rounded-full ${color}`}>
          <Icon className="text-white" size={24} />
        </div>
      </div>
    </Link>
  );
}

function RecentTestRuns({ runs }: { runs: any[] }) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="text-green-500" size={18} />;
      case 'failed':
        return <XCircle className="text-red-500" size={18} />;
      default:
        return <Clock className="text-yellow-500" size={18} />;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b">
        <h2 className="font-semibold">Recent Test Runs</h2>
      </div>
      <div className="divide-y">
        {runs.length === 0 ? (
          <div className="p-4 text-gray-500 text-center">No test runs yet</div>
        ) : (
          runs.slice(0, 5).map((run) => (
            <Link
              key={run.id}
              href={`/tests/${run.id}`}
              className="flex items-center justify-between p-4 hover:bg-gray-50"
            >
              <div className="flex items-center gap-3">
                {getStatusIcon(run.status)}
                <div>
                  <p className="font-medium">
                    {run.name || `Run ${run.id.slice(0, 8)}`}
                  </p>
                  <p className="text-sm text-gray-500">
                    {new Date(run.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm">
                  <span className="text-green-600">{run.passed_cases}</span>
                  {' / '}
                  <span className="text-red-600">{run.failed_cases}</span>
                  {' / '}
                  <span>{run.total_cases}</span>
                </p>
                <p className="text-xs text-gray-500">
                  {run.status === 'completed'
                    ? `${Math.round((run.passed_cases / run.total_cases) * 100)}% passed`
                    : run.status}
                </p>
              </div>
            </Link>
          ))
        )}
      </div>
      {runs.length > 0 && (
        <div className="p-4 border-t">
          <Link href="/tests" className="text-blue-600 text-sm hover:underline">
            View all tests &rarr;
          </Link>
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { data: prompts = [] } = useQuery({
    queryKey: ['prompts'],
    queryFn: () => promptsApi.list(),
  });

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => datasetsApi.list(),
  });

  const { data: tests = [] } = useQuery({
    queryKey: ['tests'],
    queryFn: () => testsApi.list(),
  });

  const activePrompts = prompts.filter((p) => p.active_version).length;
  const totalCases = datasets.reduce((sum, d) => sum + d.case_count, 0);
  const completedTests = tests.filter((t) => t.status === 'completed').length;

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-gray-500">Overview of your test harness</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <StatCard
          title="Prompts"
          value={`${activePrompts} / ${prompts.length}`}
          icon={FileText}
          href="/prompts"
          color="bg-blue-500"
        />
        <StatCard
          title="Test Cases"
          value={totalCases}
          icon={Database}
          href="/datasets"
          color="bg-green-500"
        />
        <StatCard
          title="Test Runs"
          value={completedTests}
          icon={Play}
          href="/tests"
          color="bg-purple-500"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentTestRuns runs={tests} />

        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Quick Actions</h2>
          </div>
          <div className="p-4 space-y-3">
            <Link
              href="/prompts/new"
              className="flex items-center gap-3 p-3 border rounded-lg hover:bg-gray-50"
            >
              <FileText className="text-blue-500" />
              <span>Create new prompt</span>
            </Link>
            <Link
              href="/datasets/new"
              className="flex items-center gap-3 p-3 border rounded-lg hover:bg-gray-50"
            >
              <Database className="text-green-500" />
              <span>Create new dataset</span>
            </Link>
            <Link
              href="/tests/new"
              className="flex items-center gap-3 p-3 border rounded-lg hover:bg-gray-50"
            >
              <Play className="text-purple-500" />
              <span>Run new test</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
