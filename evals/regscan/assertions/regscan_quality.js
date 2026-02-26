/**
 * RegScan V4 Article Quality Assertions
 *
 * promptfoo 커스텀 assertion -- compare_articles.py & test_v4_prompt_ab.py 메트릭 이식
 *
 * 반환: { pass, score, reason, componentResults } (단일 GradingResult)
 */

// -- 금지 표현 (compare_articles.py + prompts.py 금지 표현표) --
const BANNED_PHRASES = [
  "혁명적", "획기적", "사실상 제도권 밖", "게임체인저", "판도를 바꿀",
  "꿈의 신약", "기적", "만병통치", "완치", "100%",
  "놀라운", "압도적", "유망한", "기대되는",
  "지속적인 관심이 필요",
  "제도적 공백",
];

// -- 반복 문구 (compare_articles.py) --
const REPETITIVE_PHRASES = [
  "판매권자 부재", "시장성 판단 보류", "보험 적용 가능성 열려",
  "급여 가능성이 열려", "전액 환자 부담", "제도권 처방 경로",
];

// -- 변수명 누출 (test_v4_prompt_ab.py) --
const LEAKED_VARS = [
  "fda_status_text", "ema_status_text", "mfds_status_text",
  "copay_scenario_text", "d_day_text", "cost_scenario_table",
  "approval_summary_table", "valid_competitors",
  "context.d_day_text", "context.mfds_timeline_estimate",
  "copay_exemption", "domestic_status",
];

// -- 한계점 키워드 --
const LIMITATION_KEYWORDS = ["다만", "한계", "CI", "p-value", "p=", "유의성", "95%"];

// -- 가격 스펙트럼 참조 키워드 --
const PRICE_SPECTRUM_KEYWORDS = ["중앙값", "p50", "p90", "상위 10%", "스펙트럼", "백분위"];

// -- 섹션 글자수 범위 (경험적 기준) --
const SECTION_LENGTH = {
  headline:              { min: 10, max: 50 },
  subtitle:              { min: 15, max: 70 },
  global_insight_text:   { min: 200, max: 1500 },
  domestic_insight_text: { min: 150, max: 1200 },
  medclaim_action_text:  { min: 150, max: 1200 },
};

/**
 * promptfoo assertion entry point
 * @param {string} output - LLM 원시 출력 텍스트
 * @param {object} context - { prompt, vars, test }
 * @returns {{ pass: boolean, score: number, reason: string, componentResults: Array }}
 */
module.exports = (output, context) => {
  const components = [];

  // 0) JSON 파싱
  let parsed;
  try {
    let clean = output.trim();
    if (clean.startsWith("```")) {
      const lines = clean.split("\n");
      const filtered = lines.filter(l => !l.trim().startsWith("```"));
      clean = filtered.join("\n");
    }
    parsed = JSON.parse(clean);
  } catch (e) {
    return {
      pass: false,
      score: 0,
      reason: "JSON parse failed: " + e.message,
    };
  }

  // 전체 텍스트 결합 (메트릭용)
  const allText = [
    parsed.headline || "",
    parsed.subtitle || "",
    ...(parsed.key_points || []),
    parsed.global_insight_text || "",
    parsed.domestic_insight_text || "",
    parsed.medclaim_action_text || "",
  ].join(" ");

  // 1) 금지 표현 체크
  const bannedFound = BANNED_PHRASES.filter(w => allText.includes(w));
  components.push({
    pass: bannedFound.length === 0,
    score: bannedFound.length === 0 ? 1 : 0,
    reason: bannedFound.length
      ? "banned-phrases FAIL: " + bannedFound.join(", ")
      : "banned-phrases OK",
  });

  // 2) 변수명 누출 체크
  const leakedFound = LEAKED_VARS.filter(v => output.includes(v));
  components.push({
    pass: leakedFound.length === 0,
    score: leakedFound.length === 0 ? 1 : 0,
    reason: leakedFound.length
      ? "var-leak FAIL: " + leakedFound.join(", ")
      : "var-leak OK",
  });

  // 3) 숫자 훅 (headline 또는 global 첫 문장에 숫자)
  const hookTarget = (parsed.headline || "") + " " +
    (parsed.global_insight_text || "").split(/[.!?\n]/)[0];
  const hasNumberHook = /\d/.test(hookTarget);
  components.push({
    pass: hasNumberHook,
    score: hasNumberHook ? 1 : 0,
    reason: hasNumberHook ? "number-hook OK" : "number-hook FAIL",
  });

  // 4) MOA 연쇄
  const arrowCount = (allText.match(/\u2192/g) || []).length;
  const hasMoaChain = arrowCount >= 2;
  components.push({
    pass: hasMoaChain,
    score: hasMoaChain ? 1 : Math.min(arrowCount / 2, 0.5),
    reason: hasMoaChain
      ? "moa-chain OK (" + arrowCount + "x)"
      : "moa-chain FAIL (" + arrowCount + "x, need 2+)",
  });

  // 5) 한계점 서술
  const hasLimitation = LIMITATION_KEYWORDS.some(kw => allText.includes(kw));
  components.push({
    pass: hasLimitation,
    score: hasLimitation ? 1 : 0,
    reason: hasLimitation ? "limitation OK" : "limitation FAIL",
  });

  // 6) 반복 문구 카운트
  let repCount = 0;
  for (const phrase of REPETITIVE_PHRASES) {
    const matches = allText.match(new RegExp(phrase, "g"));
    if (matches) repCount += matches.length;
  }
  components.push({
    pass: repCount <= 1,
    score: repCount <= 1 ? 1 : Math.max(0, 1 - (repCount - 1) * 0.3),
    reason: repCount <= 1
      ? "repetition OK (" + repCount + "x)"
      : "repetition FAIL (" + repCount + "x)",
  });

  // 7) 섹션별 글자수 범위
  for (const [field, range] of Object.entries(SECTION_LENGTH)) {
    const text = parsed[field] || "";
    const len = text.length;
    const inRange = len >= range.min && len <= range.max;
    components.push({
      pass: inRange,
      score: inRange ? 1 : (len < range.min ? len / range.min : range.max / len),
      reason: inRange
        ? field + " length OK (" + len + ")"
        : field + " length FAIL (" + len + ", need " + range.min + "-" + range.max + ")",
    });
  }

  // 8) key_points 개수
  const kpCount = (parsed.key_points || []).length;
  components.push({
    pass: kpCount === 4,
    score: kpCount === 4 ? 1 : Math.max(0, 1 - Math.abs(4 - kpCount) * 0.25),
    reason: kpCount === 4
      ? "key_points count OK (4)"
      : "key_points count FAIL (" + kpCount + ", need 4)",
  });

  // 9) HTML 태그 금지
  const hasHtml = /<[a-z][a-z0-9]*[\s>]/i.test(allText);
  components.push({
    pass: !hasHtml,
    score: hasHtml ? 0 : 1,
    reason: hasHtml ? "html-tags FAIL" : "html-tags OK",
  });

  // 10) 불릿 포함 여부
  const insightFields = ["global_insight_text", "domestic_insight_text", "medclaim_action_text"];
  for (const field of insightFields) {
    const text = parsed[field] || "";
    const hasBullet = /^\s*[-*\u2022]\s/m.test(text) || /\n\s*[-*\u2022]\s/.test(text);
    components.push({
      pass: hasBullet,
      score: hasBullet ? 1 : 0,
      reason: hasBullet
        ? field + " bullet OK"
        : field + " bullet FAIL",
    });
  }

  // 11) 가격 스펙트럼 참조 여부 (domestic/medclaim 텍스트)
  const priceTarget = [
    parsed.domestic_insight_text || "",
    parsed.medclaim_action_text || "",
  ].join(" ");
  const spectrumFound = PRICE_SPECTRUM_KEYWORDS.filter(kw => priceTarget.includes(kw));
  components.push({
    pass: spectrumFound.length > 0,
    score: Math.min(spectrumFound.length / 2, 1),
    reason: spectrumFound.length
      ? "price-spectrum-ref OK (" + spectrumFound.join(", ") + ")"
      : "price-spectrum-ref FAIL (no spectrum keywords in domestic/medclaim)",
  });

  // 집계
  const totalChecks = components.length;
  const passed = components.filter(c => c.pass).length;
  const failed = components.filter(c => !c.pass);
  const avgScore = components.reduce((sum, c) => sum + (c.score || 0), 0) / totalChecks;

  const failReasons = failed.map(c => c.reason).join(" | ");

  return {
    pass: failed.length === 0,
    score: avgScore,
    reason: failed.length === 0
      ? "All " + totalChecks + " checks passed"
      : passed + "/" + totalChecks + " passed. Failures: " + failReasons,
    componentResults: components,
  };
};
