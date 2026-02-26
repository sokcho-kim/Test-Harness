/**
 * V4.0 Prompt Function
 *
 * Python 형식 프롬프트 파일을 promptfoo 변수와 연결하는 어댑터.
 * - {drug_data} → vars.drug_data 치환
 * - {{ / }} → { / } 변환 (Python .format() 이스케이프 해제)
 * - Nunjucks 충돌 방지
 */
const fs = require("fs");
const path = require("path");

/**
 * Python .format() 시뮬레이션:
 * 1. {drug_data} → 실제 값 치환
 * 2. {{ → { , }} → } (이스케이프 해제)
 */
function pythonFormat(template, vars) {
  // 단일 중괄호 변수 치환
  let result = template.replace("{drug_data}", vars.drug_data || "");
  // Python format 이스케이프 해제: {{ → { , }} → }
  result = result.replace(/\{\{/g, "{").replace(/\}\}/g, "}");
  return result;
}

module.exports = function ({ vars }) {
  const systemPrompt = fs.readFileSync(
    path.join(__dirname, "v4.0_system.txt"),
    "utf-8"
  );
  const userTemplate = fs.readFileSync(
    path.join(__dirname, "v4.0_user.txt"),
    "utf-8"
  );

  const userPrompt = pythonFormat(userTemplate, vars);

  return [
    { role: "system", content: systemPrompt },
    { role: "user", content: userPrompt },
  ];
};
