// Prompt Types
export interface Prompt {
  id: string;
  name: string;
  description: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
  active_version: PromptVersion | null;
  version_count: number;
}

export interface PromptVersion {
  id: string;
  prompt_id: string;
  major: number;
  minor: number;
  patch: number;
  content: string;
  variables: string[];
  is_active: boolean;
  status: 'draft' | 'in_review' | 'active' | 'deprecated';
  change_note: string | null;
  created_at: string;
  created_by: string | null;
}

// Dataset Types
export type DatasetType = 'golden' | 'evaluation' | 'synthetic';

export interface Assertion {
  type: string;
  value?: string;
  threshold?: number;
}

export interface TestDataset {
  id: string;
  name: string;
  description: string | null;
  dataset_type: DatasetType;
  column_mapping: Record<string, string> | null;
  default_assertions: Assertion[];
  case_count: number;
  created_at: string;
  updated_at: string;
}

export interface TestCase {
  id: string;
  dataset_id: string;
  raw_input: Record<string, any>;
  expected_output: string | null;
  assertions: Assertion[] | null;
  metadata: Record<string, any> | null;
  created_at: string;
}

// Test Run Types
export type TestRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface TestRun {
  id: string;
  name: string | null;
  prompt_ids: string[];
  dataset_id: string;
  model_ids: string[];
  resolved_mapping: Record<string, string>;
  status: TestRunStatus;
  progress: number;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface TestResult {
  id: string;
  test_run_id: string;
  prompt_id: string;
  prompt_version_id: string;
  model_id: string;
  test_case_id: string;
  input_mapped: Record<string, any>;
  input_rendered: string;
  output: string;
  latency_ms: number;
  token_usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  } | null;
  assertion_results: AssertionResult[];
  passed: boolean;
  error: string | null;
  created_at: string;
}

export interface AssertionResult {
  type: string;
  value?: string;
  passed: boolean;
  message?: string;
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface MappingPreview {
  resolved_mapping: Record<string, string>;
  mapping_source: 'run_override' | 'dataset_default' | 'auto_1to1';
  validation: {
    is_valid: boolean;
    missing_variables: string[];
    unused_columns: string[];
  };
  samples: {
    raw_input: Record<string, any>;
    mapped_input: Record<string, any>;
    rendered_prompt: string;
    error: string | null;
  }[];
}

// Execute Response
export interface ExecuteResponse {
  test_run_id: string;
  status: TestRunStatus;
  total_results: number;
  passed: number;
  failed: number;
}
