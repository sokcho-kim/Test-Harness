# 

> **원문**: https://techblog.woowahan.com/22839/
> **작성일**: 2025. 09. 29.
> **작성자**: 이준수
> **스크래핑**: 2026-01-09

---

## 목차


---

## 본문

AI 기술은 빠르게 진화하고 있습니다.
우아한형제들 AI플랫폼팀은 그동안 AI플랫폼 1.0을 통해 머신러닝(ML) 모델을 개발·배포·운영을 지원하는 MLOps 플랫폼을 구축해 왔습니다. AI플랫폼 1.0의 상세 내용은 아래 글에서 다뤘습니다.

배민 앱에도 AI 서비스가? AI 서비스와 MLOps 도입기
제목은 안정적인 AI 서빙 시스템으로 하겠습니다. 근데 이제 자동화를 곁들인…

대규모 언어 모델(LLM)의 등장은 AI 개발 환경을 근본적으로 변화시켰습니다. 이제는 모델을 직접 학습하지 않아도, 파운데이션 모델 API를 호출만으로 AI 프로덕트를 구현할 수 있습니다.
다만 기존 머신러닝과는 결이 다른 새로운 과제도 생겼습니다.

ML 시대의 과제: 데이터 준비, 모델 학습, 재학습 운영
LLM 시대의 과제: 비용, 지연 시간(latency), 외부 의존성

그럼에도 LLM은 빠른 실험과 제품화를 가능하게 하고 높은 성능까지 제공해 이러한 한계를 상당 부분 보완합니다. 실제로 사내에서는 지난 1~2년 사이 AI 프로덕트가 10개 이상 만들어졌고, AI 프로덕트 개발 주체 또한 데이터 사이언티스트·머신러닝 엔지니어에서 PM, 프론트엔드, 백엔드 엔지니어까지 확장되었습니다. 실제 사례 중 하나는 우아한형제들 기술 블로그에 소개된 GPT를 활용한 카탈로그 아이템 생성에서 확인하실 수 있습니다.

이처럼 프로덕트와 고객이 빠르게 확산되면서 운영상 문제도 본격적으로 드러나기 시작했습니다. 이 내용은 아래 절에서 자세히 다루겠습니다. 결국 LLM은 단순히 모델을 호출하는 것을 넘어, 운영·정책·보안까지 아우르는 플랫폼 차원의 접근이 필요합니다.

그림 1. AI플랫폼 2.0 전체 구성도

우리는 이러한 문제를 해결하기 위해 GenAI 중심의 AI플랫폼 2.0을 준비했으며, 특히 LLMOps를 플랫폼 차원에서 지원하는 것을 핵심 목표로 삼았습니다. 이번 글에서는 문제 해결 과정에서 도입한 GenAI 컴포넌트(Studio·SDK·API Gateway·Labs)의 설계 방식과 향후 확장 비전을 소개합니다. 이를 통해 LLMOps 운영 과정에서 맞닥뜨릴 수 있는 문제를 미리 인식하고, 실제 해결 방안과 앞으로의 전략까지 확인할 수 있을 것입니다.

운영 중 마주한 8가지 문제

프로덕트와 고객이 빠르게 확산되면서 여러 운영 문제가 드러났습니다. 그중 핵심적인 8가지를 정리하면 다음과 같습니다.

1. 멀티 Provider 복잡성

LLM 벤더별로 API 호출 방식과 크레덴셜(Credential) 관리가 달라 초기 진입 장벽이 높았습니다. 서비스가 늘어날수록 코드와 관리 부담도 커졌습니다.

예를 들어 Azure OpenAI, Google Gemini, AWS Bedrock은 API 스펙이 모두 달라 같은 기능도 매번 다른 코드로 작성해야 했습니다. 여기에 벤더별 크레덴셜 발급과 관리까지 겹치면서 프로젝트 초반부터 불필요한 리소스가 소모되었습니다. 서비스 수가 늘어남에 따라 코드와 키 관리 복잡도는 계속 증가했습니다.

2. 프롬프트 관리 한계

프롬프트가 코드·시트·파일에 흩어져 관리되면서 버전 추적과 협업이 어려워졌습니다. 어떤 버전이 실제 서비스에 반영되는지도 불분명했습니다.

그림 2. 구글 시트에서 관리하고 있는 버전, 코멘트, 프롬프트


처음에는 Google 시트나 단순 코드 파일(prompt1.py, prompt2.py)로도 충분했지만, 운영 단계에서는 관리 한계가 분명해졌습니다. 프롬프트는 서비스 핵심 로직이기 때문에 변경 이력 관리와 버전 추적이 필수입니다. 그러나 체계가 없어서, 어느 프롬프트가 실제 배포 버전인지조차 파악하기 힘든 상황이 발생했고 이는 재현성·협업 모두를 저해했습니다.

3. 안정성 문제

외부 API 특성상 응답 지연과 장애가 잦았고, 벤더 정책 차단으로 응답이 차단되기도 했습니다.

그림 3. 외부 API 리전(region) 이슈

그림 4. 제공자 정책 차단 (Blocked by Provider Policy)

2025년 4월, Azure OpenAI East US 리전 장애로 GPT-4 계열 모델이 장시간 응답 불가 상태로 서비스에 영향이 있었습니다. 또한 특정 단어가 안전성 필터에 걸리면 Google Gemini는 PROHIBITED_CONTENT 오류를 반환해 응답이 차단되었습니다. 우리는 결국 동일 모델을 다른 리전에 재배포하고 트래픽을 우회하는 방식으로 대응해야 했습니다. 이처럼 LLM API는 기존 ML 서빙과 달리 장기 지연과 불확실성을 전제로 운영 전략을 세워야 한다는 사실이 분명해졌습니다.

4. 비용·리소스 관리 어려움

벤더 콘솔에 의존한 수동 관리 방식은 프로젝트별 비용 가시성을 확보하기 어려웠고, 재시도로 인한 불필요한 호출까지 누적되며 예산 관리가 불투명했습니다.

초기에는 각 LLM 벤더의 어드민 콘솔에서 사용량을 확인하고 별도 시트에 정리했지만, 프로젝트가 늘어나자 한계가 분명해졌습니다. 특히 AWS Bedrock처럼 하나의 모델을 여러 프로젝트가 공유하는 경우 Application Inference Profile | AWS 문서를 수동으로 관리해야 했습니다. 이 때문에 프로젝트 단위 비용 추적이 불가능했고, 클라이언트 타임아웃 후 자동 재시도로 인해 요금이 폭증하는 사례도 발생했습니다.

5. 실험 관리 부재

체계적 실험 관리가 부재해 결과 공유와 재현성이 부족했습니다. 같은 실험을 여러 팀이 반복하는 비효율이 발생했습니다.

그림 5. 시트에서 관리하는 실험 결과

당시 우리는 프롬프트와 실험 결과를 Google 시트 같은 임시 도구로 관리했고, 결과 이력은 쉽게 유실되었습니다. Golden Dataset을 기준으로 하고 Evaluation Dataset을 확장 관리해야 하지만, 이런 구조가 없어서 실험 데이터가 흩어졌습니다. 결국 다른 팀이 동일한 실험을 반복하거나, 유사한 과제를 하면서도 각자 데이터를 새로 만들어 쓰는 비효율이 빈번했습니다.

6. 새로운 고객층과 셀프 서비스 필요

PM·기획자 같은 비개발 직군도 직접 LLM을 활용하고자 했지만, 프롬프트만으로 실험할 수 있는 환경이 부족했습니다.

기존 플랫폼은 데이터 사이언티스트·머신러닝 엔지니어 중심이었지만, LLM 확산 이후에는 프론트엔드·백엔드 엔지니어뿐 아니라 PM과 기획자까지 고객층이 확대되었습니다. 이들은 코드를 작성하기보다 UI 기반에서 손쉽게 프롬프트를 수정·실험하고 결과를 확인하길 원했습니다. 결국 플랫폼은 개발자 전용이 아니라 셀프 서비스 형태로 확장되어야 한다는 요구가 분명해졌습니다.

7. 크레덴셜 발급 허들

API 키 발급 절차가 길고 복잡해 PoC 단계에서의 빠른 실험을 가로막았습니다.

보안 검토와 비용 승인을 거쳐야만 키가 발급되다 보니, 아이디어가 있어도 실험을 시작조차 하지 못하는 경우가 많았습니다. 특히 PoC 단계에서는 속도가 중요한데, ‘아이디어는 있지만 첫 호출조차 못 해본다’는 피드백이 여러 팀에서 나올 정도였습니다. 결과적으로 실험 속도가 느려지고, LLM 활용 확산의 발목을 잡는 구조적 병목으로 작용했습니다.

8. 보안·개인정보 보호

LLM 호출 시 개인정보가 그대로 외부 API로 전송될 위험이 있었고, 이는 법적·윤리적 리스크로 이어질 수 있었습니다.

이름, 연락처, 계좌번호, 주민등록번호 등 민감 정보가 필터링 없이 외부 벤더로 넘어갈 경우 개인정보 유출 문제로 이어질 수 있었습니다. 이를 사전에 차단하지 않으면 기업 차원의 리스크가 될 수 있었습니다.

8가지 문제와 해결 전략 요약

운영 경험과 더불어 서비스 개발자 인터뷰에서도 유사한 문제들이 확인되었습니다. 이를 종합해 8가지 핵심 문제를 도출했고, 각각에 대한 해결 전략과 대응 컴포넌트를 정리하면 아래와 같습니다.

문제	해결 전략	대응 컴포넌트
멀티 Provider 복잡성	호출 방식·크레덴셜 차이를 표준화한 통합 인터페이스	API Gateway, SDK
프롬프트 관리 한계	중앙 집중 관리로 버전 추적 및 변경 이력 확보	Studio
안정성 문제	Retry/Fallback, Trace 로깅, PII(Personally Identifiable Information, 개인 식별 정보) 필터링으로 안정적 운영	SDK, Studio
비용·리소스 관리 어려움	토큰·비용 기록, 대시보드 시각화, 알림 체계 구축	Studio, Superset
실험 관리 부재	Golden/Evaluation Dataset 기반 평가 및 결과 저장	Labs, Studio
새로운 사용자층 등장	비개발자도 활용 가능한 셀프 서비스 환경 제공	Labs, Studio, SDK
크레덴셜 발급 어려움	PoC 단계 공용 API 키, 정식 단계 분리 발급	거버넌스
보안·개인정보 보호	PII 탐지·차단 및 공통 보안 절차 정책화	SDK, Studio

특히 서비스 개발자 인터뷰에서는 프롬프트 관리 기능(91%)와 Trace 수집과 가시성 확보(Observability, 45%)가 우선순위가 가장 높은 항목으로 확인되었습니다. 프롬프트 관련해서는 다음과 같은 요구가 제기되었습니다.

동일한 프롬프트에 대해 모델 간 비교가 가능해야 한다.
프롬프트가 길어질수록 버전별 변경 사항을 추적하기 어렵다.
변경 이력을 기록하고 메모할 수 있는 기능이 필요하다.

이러한 요구를 직접적으로 해결하는 첫 번째 컴포넌트가 바로 Studio였습니다. 이후 Studio를 중심으로 SDK, API Gateway, Labs까지 확장하며 GenAI 플랫폼의 기반을 마련했습니다.

LLMOps를 위한 GenAI 컴포넌트 확장
그림 6. LLMOps Architecture

위 그림은 LLMOps Architecture를 나타낸 그림입니다. 이 절에서는 Studio를 비롯해 SDK, API Gateway, Labs가 어떤 방식으로 문제 해결에 기여했는지 구체적으로 살펴보겠습니다.

GenAI Studio: LLM 운영의 허브
그림 7. GenAI Studio 중심 구조 – Studio를 중심으로 SDK, Labs, API Gateway와 연결

AI 프로덕트를 실제 환경에 적용하려면 단순히 모델을 호출하는 것만으로는 충분하지 않습니다. 성능을 평가하고, 프롬프트를 관리하며, 장애와 비용을 모니터링할 수 있는 운영 체계가 필요합니다.
LLM 서비스가 늘어나면서 특히 네 가지 요구가 두드러졌습니다.

프롬프트 관리: 제품의 핵심 로직인 프롬프트를 버전별로 추적하고 모델 간 비교가 가능해야 합니다.
Observability: 요청 지연·실패 원인, 비용·토큰 사용 현황을 데이터 기반으로 확인할 수 있어야 합니다.
크레덴셜 관리: 프로젝트와 키가 늘어날수록 분산 관리 대신 중앙에서 일관되게 제어할 수 있어야 합니다.
Evaluation: Golden/Evaluation Dataset을 기반으로 모델 성능을 평가하고 결과를 축적해 재현성과 비교 가능성을 확보해야 합니다.

이 네 가지 요구를 해결하기 위해 도입한 것이 바로 GenAI Studio입니다.

Studio는 SDK, Labs, 모니터링 도구와 연결되는 운영 허브로서, 서비스 개발자들이 LLM을 안정적으로 실험하고 운영할 수 있는 기반을 제공합니다.

Studio의 기반 솔루션을 선택하기 위해 여러 후보를 검토했고, 최종적으로 Langfuse를 도입했습니다. 다음 절에서는 Langfuse를 선택한 과정을 소개합니다

Studio로 Langfuse를 선택한 이유

솔루션 선택 과정에서 비교한 후보에는 MLflow, PromptFlow, LangSmith, Agenta, Opik, Pezzo, OpenPrompt가 있었습니다.

MLflow: 엔터프라이즈에서 널리 활용되는 안정적인 실험 관리 도구였지만, LLM 특화 기능이 부족했습니다. 프롬프트 관련 기능이 제한적이었고, 최신 버전 업그레이드와 별도 Gateway 배포가 필요했습니다.
PromptFlow: Azure와 깊이 통합되어 Microsoft 생태계를 쓰는 조직에는 적합했습니다. 그러나 독립적인 웹 UI가 없어 운영 단계에서 필요한 대시보드·Trace 뷰어·협업 기능이 부족했습니다.
LangSmith: LangChain 생태계에 최적화되어 강력한 평가·디버깅 기능을 제공했지만, LangChain 중심으로 설계돼 범용성이 제한적이었습니다.
Agenta, Opik: 빠른 실험과 평가 루프에 적합했지만, 엔터프라이즈 성숙도(보안·권한 관리·대규모 운영 지원)가 부족했습니다.
Pezzo: 프롬프트 관리와 API 배포 기능은 유용했으나 운영 모니터링·피드백 기능이 없어서 확장성이 아쉬웠습니다.
OpenPrompt: 학계 연구에는 적합했지만, 로깅·버전 관리·권한 체계가 부족해 프로덕션 운영에는 적합하지 않았습니다.

Langfuse는 처음부터 프롬프트 관리와 Trace 기반 Observability를 핵심 기능으로 설계된 도구로, 단순한 실험 관리에 그치지 않고 운영 환경에서 필요한 성능 모니터링과 품질 개선 루프까지 지원한다는 점이 가장 큰 장점이었습니다.

Langfuse의 강점은 다음과 같았습니다.

프롬프트 관리 & 버전 제어: 프롬프트를 Text + 변수(placeholders) + 구성(config) 단위로 작성하고, 라벨 또는 버전으로 구분 가능하여 운영/실험 환경 간 전환이 쉬움.
Observability & Trace 기반 모니터링: 요청의 입력·출력·재시도·지연·비용 등의 모든 항목을 Trace 단위로 기록하고, 여러 모델/입력 타입에서 병목 및 오류 발생 지점을 정확하게 추적 가능.
대시보드: 토큰 소비량 및 API 호출 비용 추적 기능, 대시보드로 실시간 가시화 가능.
실험/평가 Workflow 지원: A/B테스트, 사용자 피드백, 커스텀 평가, 데이터셋 관리까지 포함되어, 변경 영향도를 정량적으로 평가 가능.
플랫폼 연계성: 주요 LLM 프레임워크와 쉽게 통합되며, 온프레미스(self-hosted) 지원.
오픈소스 생태계 & 신뢰성: 활발한 오픈소스 생태계를 기반으로 성장 중이며, 엔터프라이즈 환경에서도 신뢰 확보

Langfuse를 Self-hosted로 배포했기 때문에 물론 Clickhouse, Redis 같은 추가 운영 컴포넌트가 필요하다는 부담은 있습니다. 그러나 From Zero to Scale: Langfuse’s Infrastructure Evolution | Langfuse 블로그 문서에서 볼 수 있듯, Langfuse는 대규모 트래픽과 데이터 수집을 고려한 확장 아키텍처를 갖추고 있어 장기적인 안정성과 확장성 측면에서는 오히려 강점이 있다고 판단했습니다.

결국 Langfuse를 Studio의 기반 솔루션으로 선택했습니다.
비슷한 고민을 하고 계신다면, 다음 자료가 도움이 될 수 있습니다.

Langfuse is the #1 most used Open Source LLMOps Product | Langfuse 블로그
LangSmith Alternative? Langfuse vs. LangSmith | Langfuse 블로그
Ten Reasons to Use Langfuse for LLM Observability, Evaluations and Prompt Management | Langfuse 블로그
Studio 기능

자세한 Studio 기능은 Langfuse 공식 문서에서 확인할 수 있습니다. 여기서는 우리가 실제로 가장 많이 활용하고 있는 기능 네 가지를 중심으로 소개하겠습니다. Studio에서 가장 많이 활용하는 네 가지 기능은 프롬프트 관리, Observability, 크레덴셜 관리, Evaluation입니다.

1. 프롬프트 관리
그림 8. 프롬프트 버전 관리 화면 – 프롬프트 버전 관리 및 운영 배포 버전 지정 기능

LLM 서비스에서 프롬프트는 단순한 입력이 아니라 프로덕트의 핵심 로직입니다. 조금만 수정해도 모델의 응답 품질이나 비용, 지연 시간에 직접적인 영향을 미치기 때문에 체계적인 관리가 필수입니다. Studio는 프롬프트를 버전별로 저장하고 변경 이력을 추적할 수 있으며, 모델 간 성능을 비교하거나 문제가 생겼을 때 이전 버전으로 쉽게 롤백할 수 있습니다.

이런 기능은 단순히 편리함을 넘어 서비스 품질을 안정적으로 유지하기 위한 기본 장치입니다. 운영 환경에서 실제 사용되는 프롬프트를 추적하고 변경 이력을 투명하게 관리하는 것은 LLMOps의 출발점입니다.

2. Observability

외부 API를 호출하는 LLM은 언제든지 지연되거나 불안정해질 수 있습니다. 운영자가 가장 많이 묻는 질문은 “왜 응답이 느려졌는가?”, “어디서 오류가 발생했는가?”, “비용은 어디에서 많이 쓰이고 있는가?”입니다. Studio의 Observability 기능을 사용하면 요청 단위 Trace를 수집하고, 지연 시간, 비용, 오류 발생 지점, 토큰 사용량까지 정량적으로 모니터링할 수 있습니다.

그림 9. Observability 화면 – LLM 호출을 Trace 단위로 기록

그 결과 특정 단계에서 병목이 발생했는지, 어떤 프롬프트가 과도한 비용을 유발하는지, 혹은 특정 모델 호출에서 실패율이 높은지 등을 데이터 기반으로 분석할 수 있습니다. Langfuse 블로그의 Observability in Multi-step LLM Systems | Langfuse 블로그 글에서도 다루고 있듯이, 이런 추적 기능은 복잡한 LLM 파이프라인을 안정적으로 운영하기 위한 핵심 요소입니다.

Grafana 기반의 단독 모니터링 체계에서 벗어나, 시스템 전반을 데이터 기반으로 관찰하고 분석할 수 있는 Observability 파이프라인 설계를 했습니다.

그림 10. Observability – 파이프라인 설계

3계층 구조로 구성했습니다.
첫 번째 Application 레이어에서는 Studio를 통해 LLM 응답을 수집합니다. 두 번째 Collection 레이어에서는 Traces 데이터를 ClickHouse에, 서비스 및 시스템 메트릭을 Prometheus에 저장합니다. 마지막으로, 수집된 데이터를 기반으로 프로덕트와 시스템을 이해하고 분석할 수 있는 Observability 환경을 구축했습니다.

그림 11. Observability – 모니터링과 경보

기존 Grafana 기반 서빙 모니터링에서는 Latency 원인 분석이 어려웠습니다. Average Response Time의 변동폭이 크고, Max Response Time에서는 Client Timeout 이슈가 발생했습니다. 안정적인 평균 응답 시간을 기대했지만, 원인 파악이 쉽지 않았습니다.

Langfuse 도입 이후에는 모델별 응답 속도를 Percentile로 분석할 수 있었고, Traces를 통해 병목 지점을 명확히 확인할 수 있었습니다. 또한 ClickHouse와 Superset을 활용해 프로젝트별 비용 모니터링 및 알림 시스템을 구축함으로써, 전체 프로젝트의 비용 관리가 한층 효율적으로 개선되었습니다.

3. 크레덴셜 관리
그림 12. 크레덴셜 관리 – LLM Provider의 API Key를 중앙에서 관리하고, 프로젝트 단위로 제어

LLM 서비스가 늘어나면서 프로젝트별, 모델별로 API Key를 관리하는 일이 점점 더 복잡해졌습니다. 과거에는 AWS Secret Manager나 환경 변수(ENV)에 일일이 키를 등록해야 했고, 팀별로 키가 흩어져 있다 보니 누가 어떤 키를 쓰고 있는지 파악하기도 어려웠습니다.

크레덴셜을 한 번 Studio에 등록해두면, SDK는 Studio의 단일 API Key만으로 프로젝트에 등록된 모든 모델을 호출할 수 있습니다. 운영자는 중앙에서 발급과 사용 현황을 제어하고, 개발자는 별도의 환경 변수 설정 없이 빠르게 실험을 시작할 수 있습니다.

이 방식은 보안과 운영 효율성 측면에서 큰 장점이 있습니다. 키가 분산 관리되지 않기 때문에 유출 위험을 줄일 수 있고, 프로젝트·팀 단위별 사용 현황을 추적할 수 있어 비용 관리에도 유리합니다.

4. Evaluation (Golden Dataset & Evaluation Dataset)
그림 13. Evaluation, 출처: https://langfuse.com/docs/evaluation/overview


이 그림은 Langfuse의 LLM Evaluation 프로세스를 설명한 다이어그램으로, 오프라인(Offline) 단계와 온라인(Online) 단계가 유기적으로 연결되어 모델의 성능을 지속적으로 평가하고 개선하는 흐름을 보여줍니다.

그림 14. Evaluation – Dataset

LLM 실험과 운영에서 가장 중요한 자산은 데이터셋입니다. Studio에서는 사람이 직접 검수한 Golden Dataset을 만들어 기준선(Baseline) 검증에 활용할 수 있고, 여기에 실제 서비스 데이터를 확장해 Evaluation Dataset을 구축할 수 있습니다.

Golden Dataset은 작지만 신뢰도가 높은 데이터셋으로 모델 비교의 기준이 되고, Evaluation Dataset은 더 넓은 커버리지를 반영해 실제 서비스 품질을 평가합니다.

그림 15. Evaluation – Experiments

Dataset을 기준으로 다양한 실험을 수행할 수 있으며, 각 실험의 응답 속도, 비용, 정확도를 비교해 최적의 모델 구성과 조건을 도출할 수 있습니다.

그림 16. Evaluation – LLM-as-a-Judge

Evaluation 방법은 Manual Annotation이나 User Feedback을 통해 직접 수행할 수 있으며, LLM-as-a-Judge 방식을 활용해 모델이 스스로 출력을 평가하도록 설정할 수도 있습니다.

GenAI SDK: 반복은 줄이고, 요청은 간단하게. 결과는 안정적으로.
그림 17. GenAI SDK 구조 – GenAI SDK를 활용해 API Gateway와 AI Product 개발

GenAI SDK는 LLM 기반 서비스를 개발할 때 반복적으로 구현해야 하는 공통 기능들을 패키지화해 제공합니다.

모델 선택, 라우팅, Trace 로깅, 크레덴셜 관리 같은 기능은 모든 서비스에서 필요하지만 매번 새로 구현해야 했습니다. SDK는 이를 표준화해 제공함으로써 개발자가 프롬프트 설계와 애플리케이션 로직 같은 본질적인 부분에만 집중할 수 있도록 돕습니다.

단일화된 인터페이스: LiteLLM을 기반으로, 여러 LLM을 모델 이름만 바꿔 호출할 수 있는 공통 인터페이스를 제공합니다.
라우팅·로드밸런싱·Fallback 전략: LiteLLM의 기능을 그대로 활용해 단일 모델뿐 아니라 여러 리전·여러 벤더 간 트래픽 라우팅을 지원합니다. 장애가 발생하면 자동으로 다른 경로로 전환할 수 있습니다.
크레덴셜 관리 단순화: 사용자가 각 LLM의 API 키를 직접 관리할 필요가 없습니다. Studio에 크레덴셜을 등록해두면 SDK는 Studio의 단일 API 키만으로 모든 모델을 호출할 수 있습니다. 과거처럼 AWS Secret Manager나 환경 변수(ENV)에 일일이 설정할 필요가 없습니다.
프롬프트 연동과 Context Engineering: Studio에 저장된 프롬프트를 불러와 동적으로 컨텍스트를 주입할 수 있어, 보다 유연한 Context Engineering이 가능합니다.
GenAI API Gateway: SDK 기능을 담은 OpenAI-Compatible 인터페이스
그림 18. GenAI API Gateway – OpenAI-Compatible API를 제공해 다양한 애플리케이션 및 도구 연동

GenAI API Gateway는 ML SDK와 GenAI SDK의 기능을 그대로 내장하고 있으며, 이를 OpenAI-Compatible API 형태로 제공합니다. 따라서 Python SDK를 직접 사용하지 않아도 동일한 기능을 다양한 환경에서 활용할 수 있습니다.

SDK 기능 포함: Gateway는 SDK가 제공하는 모델 라우팅, 로드밸런싱, Fallback 전략, Trace 로깅, 크레덴셜 관리 기능을 모두 지원합니다. 즉, Python 코드에서 SDK를 직접 호출하든 Gateway를 통해 API를 호출하든 동일한 경험을 제공합니다.
OpenAI-Compatible API & 생태계 호환성: Gateway는 OpenAI와 동일한 API 스펙을 제공합니다. 그 결과 OpenWebUI, Langfuse Playground, LangChain, LlamaIndex 등 OpenAI-Compatible 도구들과 추가 개발 없이 바로 연동할 수 있습니다.
Python을 넘는 확장성: Python SDK를 직접 사용하지 않아도 REST API를 통해 Non-Python 애플리케이션이나 Web/Mobile 앱에서 그대로 활용할 수 있습니다.
GenAI Labs: 프롬프트 실험과 평가를 위한 워크플로우
그림 19. GenAI Labs – 도메인 전문가를 위한 실험 환경

다양한 LLM 서비스가 빠르게 등장하면서, 프롬프트를 어떻게 설계하고 최적화할 것인가는 중요한 과제가 되었습니다. 이제는 단순히 모델을 호출하는 수준을 넘어 아래 세 가지가 필수 요소가 되었습니다.

프롬프트 버전 관리
데이터셋 기반 검증
실험 결과 추적

이 요구를 해결하기 위해 우리는 GenAI Labs를 구축했습니다.

GenAI Labs를 직접 구현한 이유

기존에도 다양한 프롬프트 최적화 도구가 있었지만, 우리가 찾은 건 단순한 프롬프트 최적화가 아니었습니다. 우리가 필요했던 것은 다음과 같은 기능이었습니다.

신기능 실험: LLM 제공사의 새로운 기능을 빠르게 검토하고 즉시 실험 가능
Studio와 긴밀한 연동: 프롬프트·데이터셋·결과 관리가 하나의 흐름으로 연결
Custom Evaluation: 코드 레벨에서 평가 지표를 자유롭게 정의 가능
Context Engineering: Prompt Variables를 활용해 동적으로 컨텍스트 삽입

Studio에서도 UI나 코드로 실험을 진행할 수 있지만, UI만으로는 Context Engineering을 적용하기 어렵다는 한계가 있었습니다. 최근에는 단순 프롬프트 설계를 넘어, 성능을 극대화하기 위한 Context Engineering 연구로 이어지고 있습니다(참고: A Survey of Context Engineering for Large Language Models, Mei et al., 2025). 성능 극대화를 고려했을 때, 코드 레벨의 유연성을 반드시 확보해야 했습니다. 또한 당시 Langfuse Playground는 아직 멀티모달 입력을 지원하지 않는 제약이 있어 결국 직접 Labs를 개발하기로 했습니다.

GenAI Labs 기능 개요
그림 20. GenAI Labs 실험 화면 – Labs에서 프롬프트·모델·파라미터를 설정하고 단일 테스트 또는 배치 실험을 수행하는 기능

GenAI Labs는 단순한 도구가 아니라, 프롬프트 관리 → 실험 실행 → 성능 평가 → 결과 분석까지 LLM 실험의 전 과정을 하나의 워크플로우로 제공합니다.

Studio 연동: 프롬프트 관리, 데이터셋 활용, 실험 결과 저장 및 버전 관리
멀티 LLM 지원: Azure OpenAI, Google Gemini, AWS Bedrock 등 다양한 모델 지원
Custom Evaluation: 필요 시 코드 레벨에서 평가 함수 구현 가능
Context Engineering: Prompt Variables를 활용해 동적으로 컨텍스트 삽입
GenAI Labs 목적별 활용

이제 GenAI Labs를 어떤 목적으로 활용할 수 있는지 살펴보겠습니다. Labs는 단일 테스트부터 배치 실험, 데이터셋 업로드까지 다양한 상황에서 활용할 수 있도록 설계되었습니다.

단일 테스트
목적: 프롬프트 개발 초기 단계, 특정 케이스 빠른 검증
기능: Studio 프롬프트 로드, 다양한 모델/파라미터 설정, 이미지 입력 지원, 스트리밍 응답
배치 실험
목적: Golden Dataset 기반의 성능 평가 및 모델 비교
기능: Studio 데이터셋 연동, 다양한 평가 함수/커스텀 로직 지원
데이터셋 업로드
목적: 실험용 데이터셋 준비
기능: 입력/출력/메타데이터 매핑 후 프로젝트별 Studio 업로드
GenAI Labs 활용 시나리오

GenAI Labs는 개발·검증·분석 단계에서 어떻게 활용되는지 시나리오별로 정리할 수 있습니다. 아래 그림은 실험 간 결과를 비교하고 세부 지표를 분석하는 과정을 시각화한 예시입니다.

그림 21. GenAI Labs 실험간 비교 – 응답시간, 비용, 스코어
그림 22. GenAI Labs 실험 상세 비교 – 결과, 응답시간, 비용, 점수, 토큰 수
개발 단계: 단일 테스트로 프롬프트를 빠르게 검증
검증 단계: 데이터셋 업로드 후 배치 실험 실행
분석 단계: Studio 대시보드에서 결과를 종합 분석

입력은 프롬프트·모델 설정·데이터셋, 출력은 응답 속도·비용·스코어입니다. 이를 통해 모델별 응답 품질을 비교하고, 차이가 큰 사례는 심층 분석할 수 있습니다.

지금까지 살펴본 GenAI Studio, SDK, API Gateway, Labs는 모두 LLM 기반 서비스를 운영하면서 실제로 마주한 문제들을 해결하기 위해 만들어진 컴포넌트들입니다.

LLM은 빠르게 시작할 수 있지만, 운영이 길어질수록 응답 지연·장애·비용·프롬프트 관리 이슈가 누적됩니다.

다음에서는 이러한 문제들을 어떻게 풀어갔는지, 그리고 각 컴포넌트가 어떤 역할을 했는지 사례 중심으로 소개하겠습니다.

8가지 문제 해결 사례
1. 멀티 Provider 복잡성 → GenAI API Gateway + SDK

벤더마다 호출 방식이 달라 코드와 크레덴셜 관리가 복잡했던 문제는 SDK와 API Gateway로 해결했습니다.

SDK는 여러 벤더의 호출 방식을 단일 인터페이스로 통합해, 개발자가 모델 이름만 바꿔 호출할 수 있도록 했습니다. 또한 Trace 로깅, 라우팅, Fallback 같은 공통 기능도 내장해 반복 코드를 줄였습니다.

API Gateway는 OpenAI-Compatible 인터페이스를 제공해 Python 외 다른 언어나 환경에서도 쉽게 모델을 호출할 수 있게 했습니다.

2. 프롬프트 관리 한계 → GenAI Studio

프롬프트 버전 관리와 변경 이력이 불가능해 운영에 어려움이 컸던 문제는 Studio로 해결했습니다.

프롬프트를 중앙에서 관리하면서 버전별 성능, 변경 이력, Trace 추적이 가능해졌습니다. 운영 중에도 Studio에서 불러온 프롬프트를 안정적으로 배포할 수 있게 되어, Git, 시트, 파일에 흩어져 있던 관리 혼란이 해소되었습니다.

3. 안정성 문제 → SDK + Studio

LLM API의 응답 지연·실패, 정책 차단, 리전 장애 문제는 SDK와 Studio Trace로 대응했습니다.

SDK에는 Retry/Fallback 전략이 내장돼 특정 리전이 장애를 겪어도 자동으로 다른 리전이나 모델로 트래픽을 전환할 수 있습니다. 모든 요청은 Trace 단위로 기록되어 어느 구간에서 문제가 발생했는지 데이터 기반으로 분석할 수 있습니다. 또한 요청 전에는 자체 개발한 PII 탐지 모듈을 거쳐 개인정보(이름, 연락처, 계좌번호 등)가 포함된 입력을 차단해 안전한 운영을 보장했습니다.

4. 비용·리소스 관리 어려움 → Studio + Superset

프로젝트별 비용 가시성이 낮아 예산 관리가 불투명했던 문제는 Studio 데이터와 Superset 대시보드로 해결했습니다.

Studio는 모든 요청의 토큰 사용량과 비용 데이터를 기록하고, 이를 Superset에서 시각화해 팀·프로젝트 단위 리포트를 자동 생성했습니다. 또한 알림 기능을 통해 예산 초과나 비정상 패턴을 빠르게 감지해, 클라이언트 재시도 같은 불필요 호출까지 추적·제어할 수 있었습니다.

5. 실험 관리 부재 → GenAI Labs + Studio 연동

실험 결과가 시트에 흩어져 공유·재현성이 부족했던 문제는 Labs로 해결했습니다.

GenAI Labs는 Golden/Evaluation Dataset을 기반으로 프롬프트와 모델을 평가하고, 결과는 Studio에 자동 저장됩니다. 이를 통해 동일한 실험 반복이 줄어들고, 조직 차원의 지식 자산으로 축적할 수 있었습니다.

6. 새로운 사용자층의 등장 → Labs + Studio + SDK

사용자가 개발자뿐 아니라 PM·기획자 등 비개발 직군까지 확대되면서 셀프 서비스 환경이 필요했습니다.

Labs와 Studio의 UI를 통해 비개발자도 프롬프트만으로 실험할 수 있었고, 개발자는 SDK 기반 코드 작성에 집중할 수 있었습니다. 덕분에 작은 실험 요청에도 개발자가 개입하지 않아도 되는 구조가 마련되었습니다.

하지만 새로운 사용자층이 늘어나면서 기존에 개발자 중심으로 설계된 정책과 워크플로우가 비개발자에게는 여전히 어렵게 느껴졌습니다. UI에는 시스템 내부 개념이 그대로 드러나 이해가 쉽지 않았고, 실험 절차도 엔지니어링 관점에 맞춰져 있어 진입 장벽이 있었습니다. 결국 UI 제공만으로는 충분하지 않았고, 플랫폼 자체가 한 단계 더 추상화되어야 한다는 걸 체감했습니다. 이 때문에 Langflow, n8n과 같은 시각적 워크플로우 툴 도입도 함께 고민하고 있으며, 동시에 직군별 이해 수준에 맞는 정책 관리 체계를 새로 설계하는 과제도 남아 있습니다.

7. 크레덴셜 발급 허들 → 정책화된 키 관리

아이디어는 있어도 키 발급 절차 때문에 실험을 시작하지 못했던 문제는 정책화된 키 관리 프로세스로 해결했습니다.

그림 23. 크레덴셜 발급 프로세스 – 기존 프로세스와 개선된 프로세스 비교


PoC를 시작하기 전 보안 검토를 거치면, PoC 단계에서는 공용 API 키 하나로 여러 LLM 벤더 모델을 자유롭게 실험할 수 있습니다. 이후 실제 과제로 전환될 때는 필요한 모델에 대해서만 정식 API 키를 발급받아 운영 환경에서 관리합니다. 이 방식은 PoC 단계에서는 실험 자유도를 높이고, 정식 과제 단계에서는 보안성과 관리 효율성을 확보했습니다.

8. 보안·개인정보 보호 → SDK + Studio 정책화

외부 LLM API 호출 전에 PII 탐지 모듈을 거쳐, 개인정보(이름, 연락처, 계좌번호, 주민등록번호 등)가 포함된 경우 전송을 즉시 차단하고 관련 로그를 별도로 기록했습니다.

또한 Studio 레벨에서 이를 정책화해 모든 프로젝트가 동일한 보안 절차를 따르도록 했습니다. 개발자는 별도 로직을 작성하지 않아도 SDK와 Gateway를 통해 자동으로 PII 필터링을 적용할 수 있으며, 운영자는 Trace로 차단 기록과 정책 위반 현황을 투명하게 모니터링할 수 있었습니다.

이처럼 8가지 문제를 풀기 위해 도입한 컴포넌트들은 각각 개별 기능을 제공하는 데 그치지 않고, 서로 유기적으로 연결되며 하나의 운영 사이클을 완성했습니다.

LLMOps 관점에서 본 GenAI 컴포넌트

LLMOps는 모델 호출을 넘어서 개발–연구–운영을 연결하는 전체 운영 사이클을 다룹니다. GenAI 컴포넌트(Studio, Labs, SDK, API Gateway)는 이 사이클의 각 단계를 담당하면서도 서로 긴밀히 연결되어, 통합된 LLMOps 워크플로우를 형성합니다.

개발 (Studio + SDK + API Gateway)
개발자는 프롬프트를 Studio에 저장하고, SDK를 통해 불러와 LLM을 호출합니다.
ML Projects 컴포넌트를 활용해 Prompt를 API 형태로 빠르게 개발할 수 있습니다.
프롬프트와 설정은 여러 버전으로 관리되며, Trace를 통해 성능 변화를 추적합니다.
연구 (Studio + SDK + Labs)
연구자는 프롬프트·모델 설정을 수정하고 Studio와 Labs에서 다양한 실험을 수행합니다.
자동 평가(LLM-as-a-Judge), 사용자 피드백, 수동 라벨링을 통해 품질을 검증합니다.
모든 실험 결과는 Studio에 기록되어 재현 가능하며, 비용·토큰·사용량도 전 과정에서 추적됩니다.
운영 (Studio + SDK)
연구를 통해 확보한 최적의 프롬프트는 Studio에 저장되어, 운영 환경에서 라벨 기반 A/B 테스트 및 배포가 가능합니다.
운영 중에는 Trace를 통해 Observability를 확보하여 성능, 안정성, 비용을 모니터링합니다.
이 과정에서 축적된 데이터는 Golden/Evaluation Dataset으로 정제되어 다시 연구 단계로 피드백됩니다.
결과

LLMOps를 도입한 이후, 정성적 측면에서는 Observability, 보안, 안정성 확보를 통해 운영 체계의 신뢰성을 강화했습니다. 또한 개발과 배포 과정이 표준화 및 자동화되면서 프로덕트 개발 생산성이 향상되고, 운영 효율성 또한 크게 개선되었습니다. 정량적 측면에서도 2025년 기준 사용자 수는 전년 대비 50% 증가했고, 조직 전반의 LLM 활용률이 상승하면서 프로젝트 수는 69% 성장했습니다. 이를 통해 LLMOps 도입이 조직 전체의 생산성 레버리지(Leverage)로 작용했음을 확인할 수 있었습니다.

그림 24. 연도별 DS/MLE와 기타 직군의 활용 비율 비교


첫 번째 차트는 연도별 직군별 LLM 활용 비율을 보여줍니다. 2022~2024년에는 주로 데이터사이언티스트(DS)와 머신러닝 엔지니어(MLE) 중심의 활용이 많았으나,
2025년에는 기타 직군의 비중이 38.3%로 확대되었습니다. 이는 LLMOps 도입으로 인해 MLE/DS 외 직군에서도 모델을 활용할 수 있는 환경이 조성되었음을 의미합니다.

그림 25. 사용자 성장 지수 – 2025년 기준 전년 대비 50% 증가


두 번째 차트는 사용자 성장 지수(User Growth Index)를 나타냅니다. 2022년을 기준(100)으로 했을 때, 2023년에는 625%, 2024년에는 38%, 그리고 2025년에는 50%의 추가 성장을 기록했습니다. 이는 LLMOps 도입을 통해 사용성이 개선되고, 실제 사용자 참여가 확대된 결과로 해석됩니다.

그림 26. 연도별 신규 LLM 프로젝트 증가율 – 2025년 기준 전년 대비 69% 성장


세 번째 차트는 연도별 신규 LLM 프로젝트 증가율을 나타냅니다. 2023년 대비 2024년에는 333%, 2025년에는 633%의 높은 증가율을 보였습니다. 2025년에는 많은 프로젝트가 실제 배포(Deployed) 단계에 도달했지만, 여전히 개발 중(In Development)인 프로젝트의 비중도 많습니다. 이는 LLMOps 기반의 개발 파이프라인이 지속적으로 확장되고 있으며, 향후 더 많은 프로젝트가 프로덕션으로 전환될 잠재력을 보여줍니다.

요약하자면, LLMOps는 단순히 운영 자동화를 넘어 전사적인 생산성과 확장성의 기반을 마련한 핵심 인프라로 자리 잡았습니다.

마치며

AI플랫폼팀의 목표는 프로덕트를 만들면서 필요한 공통 기능을 플랫폼화하고, 이를 다시 레버리지하여 더 많은 프로덕트를 만들어 비즈니스 임팩트를 창출하는 것입니다.

앞으로는 Context Engineering, Agentic Design Patterns과 같은 새로운 기법들이 점점 더 중요해질 것입니다.

즉, “프로덕트 → 플랫폼 → 다시 프로덕트”로 이어지는 선순환 구조를 통해, 플랫폼을 지속적으로 확장하고 레버리지함으로써 더 많은 AI 프로덕트를 빠르게 확산하고 안정적으로 창출할 수 있는 체계를 구축해 나가고자 합니다.

우리가 직면했던 8가지 문제는 단순한 기술적 불편이 아니라, LLM을 서비스로 안정적으로 운영하기 위해 반드시 해결해야 할 과제였습니다. 이를 풀기 위해 도입한 GenAI Studio, Labs, SDK, API Gateway는 지금은 유기적으로 연결된 LLMOps 워크플로우로 자리 잡았습니다.

이 경험은 우리만의 사례가 아닙니다. 많은 기업이 PoC 이후 운영 확장에서 어려움을 겪는 이유 | McKinsey 블로그 사례와 같이 LLM은 누구나 빠르게 시도할 수 있지만, 지속 가능한 운영 체계 없이는 실제 서비스로 이어지기 어렵습니다.

이제 LLMOps는 선택이 아니라, LLM을 비즈니스 임팩트로 연결하기 위한 필수 조건입니다. AI플랫폼팀은 앞으로도 더 많은 팀이 이 길을 빠르고 안전하게 걸을 수 있도록 플랫폼을 발전시켜 나가겠습니다.

이제는 모두가 AI 프로덕트를 만들 수 있는 시대입니다.
여러분의 도전을 기대합니다. 🎈

 
이준수
               

---

## 이미지 목록 (30개)

| # | 설명 | URL |
|---|------|-----|
| 1 | 이준수 | [링크](https://techblog.woowahan.com/wp-content/uploads/2023/05/221007_우형사원증_양극모_이준수님_22050292.jpg) |
| 2 | clipboard | [링크](https://techblog.woowahan.com/wp-content/themes/techblog/imgs/link.svg) |
| 3 | facebook | [링크](https://techblog.woowahan.com/wp-content/themes/techblog/imgs/facebook.svg) |
| 4 | twitter | [링크](https://techblog.woowahan.com/wp-content/themes/techblog/imgs/twitter.svg) |
| 5 | AI플랫폼 2.0 전체 구성도 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-11.40.47%E2%80%AFAM.png) |
| 6 | 구글 시트에서 관리하고 있는 버전, 코멘트,프롬프트
 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/11/Screenshot-2025-11-06-at-1.06.30%E2%80%AFPM.png) |
| 7 | 외부 API 리전(region) 이슈 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-1.08.12%E2%80%AFPM.png) |
| 8 | 제공자 정책 차단 (Blocked by Provider Policy) | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-1.08.21%E2%80%AFPM.png) |
| 10 | 시트에서 관리하는 실험 결과 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-1.09.36%E2%80%AFPM.png) |
| 11 | GenAI Studio | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/11/Screenshot-2025-11-06-at-11.43.15%E2%80%AFAM.png) |
| 12 | GenAI Studio | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/11/Screenshot-2025-11-06-at-11.45.01%E2%80%AFAM.png) |
| 13 | GenAI Studio 기능 - 프롬프트 관리 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/AI-Platform-2.0-%EA%B7%B8%EB%A6%BC3.png) |
| 14 | GenAI Studio 기능 - Observability | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/AI-Platform-2.0-%EA%B7%B8%EB%A6%BC4.png) |
| 15 | GenAI Studio 기능 - Observability | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-1.15.20%E2%80%AFPM.png) |
| 16 | GenAI Studio 기능 - Observability | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-1.17.15%E2%80%AFPM.png) |
| 17 | GenAI Studio 기능 - 크레덴셜 관리 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/AI-Platform-2.0-%EA%B7%B8%EB%A6%BC5.png) |
| 18 | GenAI Studio 기능 - 크레덴셜 관리 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-1.19.07%E2%80%AFPM.png) |
| 19 | GenAI Studio 기능 - 크레덴셜 관리 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-1.19.47%E2%80%AFPM.png) |
| 20 | GenAI Studio 기능 - 크레덴셜 관리 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-1.19.55%E2%80%AFPM.png) |
| 21 | GenAI Studio 기능 - 크레덴셜 관리 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-1.19.34%E2%80%AFPM.png) |
| 22 | GenAI SDK | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/11/Screenshot-2025-11-06-at-12.46.39%E2%80%AFPM.png) |
| 23 | GenAI API Gateway | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/11/Screenshot-2025-11-06-at-12.53.12%E2%80%AFPM.png) |
| 24 | GenAI Labs | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/11/Screenshot-2025-11-06-at-12.56.06%E2%80%AFPM.png) |
| 25 | GenAI Labs 실험 화면 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/AI-Platform-2.0-%EA%B7%B8%EB%A6%BC9.png) |
| 26 | GenAI Labs 활용 시나리오 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/AI-Platform-2.0-%EA%B7%B8%EB%A6%BC10.png) |
| 27 | GenAI Labs 활용 시나리오 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/AI-Platform-2.0-%EA%B7%B8%EB%A6%BC11.png) |
| 28 | 크레덴셜 발급 프로세스 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/11/Screenshot-2025-11-06-at-1.04.14%E2%80%AFPM.png) |
| 29 | 결과 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-5.15.23%E2%80%AFPM.png) |
| 30 | 결과 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-5.15.30%E2%80%AFPM.png) |
| 31 | 결과 | [링크](https://techblog.woowahan.com/wp-content/uploads/2025/09/Screenshot-2025-11-06-at-5.15.39%E2%80%AFPM.png) |

---

## 참조 링크 (16개)

- [AI](/?pcat=ai)
- [배민 앱에도 AI 서비스가? AI 서비스와 MLOps 도입기](https://techblog.woowahan.com/11582/#toc-3)
- [제목은 안정적인 AI 서빙 시스템으로 하겠습니다. 근데 이제 자동화를 곁들인…](https://techblog.woowahan.com/19548/)
- [GPT를 활용한 카탈로그 아이템 생성](https://techblog.woowahan.com/21294/)
- [2025년 4월, Azure OpenAI East US 리전 장애로 GPT-4 계열 모델이 장시간 응답 불가 상태](https://learn.microsoft.com/en-us/answers/questions/2245448/azure-open-ai-service-unavailable-east-us-region?)
- [Application Inference Profile | AWS 문서](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles.html)
- [From Zero to Scale: Langfuse’s Infrastructure Evolution | Langfuse 블로그](https://langfuse.com/blog/2024-12-langfuse-v3-infrastructure-evolution)
- [Langfuse is the #1 most used Open Source LLMOps Product | Langfuse 블로그](https://langfuse.com/blog/2024-11-most-used-oss-llmops)
- [LangSmith Alternative? Langfuse vs. LangSmith | Langfuse 블로그](https://langfuse.com/faq/all/langsmith-alternative)
- [Ten Reasons to Use Langfuse for LLM Observability, Evaluations and Prompt Management | Langfuse 블로그](https://langfuse.com/faq/all/ten-reasons-to-use-langfuse)
- [Langfuse 공식 문서](https://langfuse.com/docs/prompt-management/overview)
- [Observability in Multi-step LLM Systems | Langfuse 블로그](https://langfuse.com/blog/2024-10-observability-in-multi-step-llm-systems)
- [A Survey of Context Engineering for Large Language Models, Mei et al., 2025](https://arxiv.org/abs/2507.13334)
- [Langfuse Playground는 아직 멀티모달 입력을 지원하지 않는 제약](https://github.com/orgs/langfuse/discussions/4268)
- [Agentic Design Patterns](https://www.amazon.com/Agentic-Design-Patterns-Hands-Intelligent/dp/3032014018)
- [많은 기업이 PoC 이후 운영 확장에서 어려움을 겪는 이유 | McKinsey 블로그](https://www.mckinsey.com/capabilities/mckinsey-digital/our-insights/overcoming-two-issues-that-are-sinking-gen-ai-programs)
