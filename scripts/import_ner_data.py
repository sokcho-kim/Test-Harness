"""
NER Test Data Import Script for Test Harness
"""
import json
import sys
import requests
from pathlib import Path

# Fix encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://localhost:8080"

def create_ner_prompt():
    """Create NER extraction prompt"""
    prompt_data = {
        "name": "Medical NER Extraction",
        "description": "Extract Disease, Drug, Procedure, Biomarker entities from medical text",
        "content": """다음 의료 텍스트에서 엔티티를 추출해주세요.

## 추출할 엔티티 유형:
- Disease: 질병, 증상, 의학적 상태 (예: 당뇨병, 고혈압, 폐렴, 암)
- Drug: 약물, 의약품, 치료제 (예: 인슐린, 아스피린, 항생제)
- Procedure: 의료 시술, 수술, 검사 (예: 내시경, MRI, 수술)
- Biomarker: 바이오마커, 검사 수치, 생체 지표 (예: 혈당, 콜레스테롤, 종양표지자)

## 입력 텍스트:
{{text}}

## 출력 형식:
반드시 아래 JSON 형식으로만 응답하세요. 다른 설명 없이 JSON만 출력하세요.
```json
{
  "Disease": ["질병1", "질병2"],
  "Drug": ["약물1", "약물2"],
  "Procedure": ["시술1", "시술2"],
  "Biomarker": ["바이오마커1"]
}
```
해당 유형의 엔티티가 없으면 빈 배열로 표시하세요.""",
        "tags": ["ner", "medical", "extraction"]
    }

    response = requests.post(f"{API_BASE}/prompts", json=prompt_data)
    if response.status_code == 200:
        prompt = response.json()
        print(f"[OK] Prompt created: {prompt['id']}")
        return prompt['id']
    else:
        print(f"[FAIL] Prompt creation failed: {response.text}")
        return None

def create_dataset():
    """Create NER dataset"""
    dataset_data = {
        "name": "Medical NER Test Dataset",
        "description": "Medical NER test data (77 cases)",
        "dataset_type": "ner",
        "default_assertions": [
            {
                "type": "is-json",
                "description": "JSON format check"
            }
        ]
    }

    response = requests.post(f"{API_BASE}/datasets", json=dataset_data)
    if response.status_code == 200:
        dataset = response.json()
        print(f"[OK] Dataset created: {dataset['id']}")
        return dataset['id']
    else:
        print(f"[FAIL] Dataset creation failed: {response.text}")
        return None

def import_test_cases(dataset_id: str, data_path: str):
    """Import test cases"""
    data_file = Path(data_path)

    if not data_file.exists():
        print(f"[FAIL] Data file not found: {data_path}")
        return False

    imported = 0
    failed = 0

    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line.strip())

                # raw_input: data to be mapped to {{text}} in prompt template
                raw_input = {
                    "text": item["text"],
                    "id": item.get("id", "")
                }

                # expected_output: expected answer (JSON string)
                expected_entities = item.get("entities", {})
                # Ensure all entity types have default values
                full_entities = {
                    "Disease": expected_entities.get("Disease", []),
                    "Drug": expected_entities.get("Drug", []),
                    "Procedure": expected_entities.get("Procedure", []),
                    "Biomarker": expected_entities.get("Biomarker", [])
                }
                expected_output = json.dumps(full_entities, ensure_ascii=False)

                case_data = {
                    "raw_input": raw_input,
                    "expected_output": expected_output,
                    "assertions": [
                        {
                            "type": "is-json",
                            "description": "JSON format check"
                        },
                        {
                            "type": "contains-json",
                            "value": '"Disease"',
                            "description": "Disease key check"
                        }
                    ]
                }

                response = requests.post(
                    f"{API_BASE}/datasets/{dataset_id}/cases",
                    json=case_data
                )

                if response.status_code == 200:
                    imported += 1
                else:
                    failed += 1
                    if failed <= 3:
                        print(f"  Warning: {item.get('id', 'unknown')} import failed - {response.text}")

            except json.JSONDecodeError as e:
                failed += 1
                print(f"  JSON parse error: {e}")
            except Exception as e:
                failed += 1
                print(f"  Error: {e}")

    print(f"[OK] Import complete: {imported} success, {failed} failed")
    return imported > 0

def main():
    print("=" * 50)
    print("NER Test Data Import")
    print("=" * 50)

    # 1. Create prompt
    print("\n[1/3] Creating NER prompt...")
    prompt_id = create_ner_prompt()
    if not prompt_id:
        return

    # 2. Create dataset
    print("\n[2/3] Creating dataset...")
    dataset_id = create_dataset()
    if not dataset_id:
        return

    # 3. Import test cases
    print("\n[3/3] Importing test cases...")
    data_path = r"D:\scrape-hub\project\ner\data\gliner2_train_v2\test.jsonl"
    success = import_test_cases(dataset_id, data_path)

    if success:
        print("\n" + "=" * 50)
        print("Import Complete!")
        print(f"Prompt ID: {prompt_id}")
        print(f"Dataset ID: {dataset_id}")
        print("\nCreate and run tests in Web UI:")
        print("  http://localhost:3000/tests/new")
        print("=" * 50)

if __name__ == "__main__":
    main()
